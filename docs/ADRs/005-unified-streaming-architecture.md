# ADR-005: Unified Streaming Architecture

**Author:** Nikos Michalakis
**Date:** March 2026
**Status:** DRAFT — for review
**Depends on:** ADR-003 (Observability & Feature Flags), XLake Store Architecture, CustomerChartStore Design, Agent Architecture, UX Architecture

---

## 1. Design Intent

A single user message produces a cascade of agent activity: entity resolution, data queries, chart generation, insights, recommendations. Today this cascade is invisible — the user sees a chat response, but the *reasoning* that produced it is lost.

This architecture makes every step of that cascade a **durable, linkable event** that simultaneously:

- streams to the UI in real time (SSE)
- persists to an append-only event log (Postgres)
- feeds PostHog product funnels (observability)
- enriches Langfuse agent traces (LLM debugging)

The design principle is **one write path, many read surfaces**. Events are born once inside `StreamProcessor`, then projected into each system. No event is constructed twice. No SDK is called from agent code.

### 1.1 Relationship to Decision Journeys and Decision Vault

The event log produced by this architecture is the **raw material** for two downstream systems defined in separate design documents:

- **Decision Journeys** — bounded traces of a user moving through the consult/reflect cycle (conversation → charts/stacks → insights → dashboard/report). Materialized from the event log by a background job that follows artifact ID links across events.
- **Decision Vault** — a RAG-indexed knowledge base of completed decision journeys, enabling precedent search ("find past analyses where executives explored margin variance"). Built by chunking, embedding, and indexing journey records in Qdrant.

This architecture does not define either system. It defines the event primitive and the write path that feeds them. The event model carries enough artifact IDs (`chart_id`, `stack_id`, `dashboard_id` in payloads) for the journey materializer to assemble complete traces without requiring additional fields on the event itself.

---

## 2. The Event as Primitive

Every meaningful thing that happens during a conversation turn is an `ActBIEvent`. This is the atomic unit of the entire architecture — streaming, persistence, tracing, and analytics all operate on the same object.

### 2.1 Protobuf Definition

`ActBIEvent` is a first-class protobuf-defined contract in the spec plane, alongside Chart, ChartStack, Dashboard, and Insight.

```protobuf
// actbi/v1/event.proto
syntax = "proto3";
package actbi.v1;

import "google/protobuf/timestamp.proto";
import "google/protobuf/struct.proto";

// The atomic unit of the ActBI streaming architecture.
// Born in StreamProcessor, persisted to conversation_events,
// projected to PostHog (milestones) and Langfuse (traces).
//
// The payload field carries the actual content (chart spec, insight,
// recommendation, etc.) as canonical JSON of the relevant domain
// protobuf (Chart, Insight, Recommendation). Consumers switch on
// event_type to interpret the payload.
message ActBIEvent {
    string event_id          = 1;   // "evt_{uuid12}"
    string event_type        = 2;   // "reasoning", "chart_spec", "insight", etc.
    string conversation_id   = 3;
    string message_id        = 4;
    uint32 seq               = 5;   // ordering within a message turn
    google.protobuf.Timestamp ts = 6;
    string tenant_id         = 7;

    // The actual content — type-specific, consumers switch on event_type.
    // For chart_spec: canonical JSON of Chart proto.
    // For insight: canonical JSON of Insight proto.
    // For reasoning: {"text": "..."}
    google.protobuf.Struct payload = 8;

    // Causal chain between events within a message turn.
    // e.g., an insight event caused_by the chart_spec event it analyzed.
    repeated string caused_by = 9;

    // Which LangGraph node produced this event.
    string agent_node        = 10;

    // Experiment variant from AgentConfig (for PostHog attribution).
    string variant           = 11;

    uint32 schema_version    = 12;  // default 1, for forward-compatible evolution
}
```

**Design decisions:**

- **No `entity_refs` or `edge_refs`.** The XLake CustomerContextStore (business knowledge graph) and the decision vault (decision knowledge base) are separate systems with separate read/write paths. Events carry artifact IDs in their payloads (chart_id, stack_id, dashboard_id) which downstream systems use to build their own indexes. The event model stays lean.
- **`payload` is `google.protobuf.Struct`.** This preserves flexibility — a `chart_spec` event's payload is a Chart protobuf canonical JSON, an `insight` event's payload is an Insight protobuf canonical JSON, a `reasoning` event's payload is `{"text": "..."}`. The event proto defines the envelope; existing domain protos define the content.
- **`caused_by` stays on the event.** Causal ordering between events is a streaming concern — it's how the UI builds reasoning lineage displays and how the decision journey materializer reconstructs the decision chain.

### 2.2 Pydantic Runtime Model

Following the established pattern (protobuf for storage/transport, Pydantic only at LangChain/FastAPI boundaries):

```python
# actbi/streaming/events.py
from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Literal
import uuid

EventType = Literal[
    "reasoning", "status",
    "chart_spec", "chart_stack_update",
    "insight", "recommendation",
    "data_binding", "highlight",
    "error", "done",
]

_MILESTONE_TYPES = frozenset({
    "chart_spec", "chart_stack_update", "insight",
    "recommendation", "done", "error",
})

class ActBIEvent(BaseModel):
    """Pydantic representation of actbi.v1.ActBIEvent proto.

    Used at the LangChain/FastAPI boundary. Serializes to
    canonical JSON matching the protobuf definition.
    """
    event_id:        str       = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    event_type:      EventType
    conversation_id: str
    message_id:      str
    seq:             int
    ts:              datetime  = Field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id:       str
    payload:         dict

    caused_by:       list[str]  = []   # prior event_ids in causal chain

    agent_node:      str | None = None # LangGraph node name
    variant:         str | None = None # experiment variant from AgentConfig
    schema_version:  int        = 1

    def to_sse(self) -> str:
        """One allocation, one serialization. This is the hot path."""
        return f"event: {self.event_type}\ndata: {self.model_dump_json()}\n\n"

    @property
    def is_milestone(self) -> bool:
        """Only milestones go to PostHog. Reasoning tokens and status do not."""
        return self.event_type in _MILESTONE_TYPES
```

The `to_sse()` method is the only serialization. The same JSON string goes to the wire, to Postgres, and (for milestones) to PostHog. No re-serialization.

---

## 3. StreamProcessor — The Single Write Path

`StreamProcessor` is the heart. It owns the SSE generator loop and makes all emission decisions. It is the *only* place where events are created, persisted, and forwarded. The SSE route, agent code, and observability SDKs never create events directly.

This is intentionally a "God object" for the stream (acknowledged in ADR-003) because scattering emission logic across handlers, middleware, and callbacks would make the system impossible to reason about.

```python
# actbi/streaming/processor.py
from __future__ import annotations
from typing import AsyncIterator
from actbi.streaming.events import ActBIEvent
from actbi.streaming.translator import translate_lg_event
from actbi.core.events import EventBus
from actbi.core.observability import CallbackFactory

class StreamProcessor:
    def __init__(
        self,
        event_bus: EventBus,
        callback_factory: CallbackFactory,
        db,  # async Supabase/Postgres client
    ) -> None:
        self._event_bus = event_bus
        self._cb = callback_factory
        self._db = db

    async def run(self, ctx: RunContext) -> AsyncIterator[str]:
        """
        The single write path. Every event born here flows to:
          1. SSE wire  (yield)
          2. Postgres   (persist)
          3. PostHog    (milestones only, via EventBus)
          4. Langfuse   (automatic via LangChain callbacks)
        """
        seq = 0
        reasoning_buf = _ReasoningBuffer()
        callbacks = self._cb.for_run(
            user_id=ctx.user_id,
            conversation_id=ctx.conversation_id,
            variant=ctx.insight_variant,
            tenant_id=ctx.tenant_id,
        )

        async for lg_event in ctx.agent_graph.astream_events(
            input={"message": ctx.message, **ctx.agent_state()},
            config={"callbacks": callbacks, "configurable": ctx.configurable()},
            version="v2",
        ):
            for evt in translate_lg_event(lg_event, ctx, seq):
                seq = evt.seq

                # Reasoning tokens: stream immediately, batch for persistence
                if evt.event_type == "reasoning":
                    reasoning_buf.append(evt.payload["text"], evt.seq)
                    yield evt.to_sse()
                    continue

                # Non-reasoning event: flush reasoning buffer first
                flushed = reasoning_buf.flush(ctx)
                if flushed:
                    await self._persist(flushed)

                # Persist the event
                await self._persist(evt)

                # PostHog milestone (async, never blocks SSE)
                if evt.is_milestone:
                    self._event_bus.from_event(evt, user_id=ctx.user_id)

                # SSE wire
                yield evt.to_sse()

        # Flush any remaining reasoning tokens
        flushed = reasoning_buf.flush(ctx)
        if flushed:
            await self._persist(flushed)

        # Terminal event
        seq += 1
        done = ActBIEvent(
            event_type="done",
            conversation_id=ctx.conversation_id,
            message_id=ctx.message_id,
            seq=seq, tenant_id=ctx.tenant_id,
            payload={"status": "complete"},
            variant=ctx.insight_variant,
        )
        await self._persist(done)
        self._event_bus.from_event(done, user_id=ctx.user_id)
        yield done.to_sse()

        # Flush PostHog buffer (Cloud Run may terminate after response)
        self._event_bus.flush()

    async def _persist(self, evt: ActBIEvent) -> None:
        """Single INSERT to conversation_events. RLS enforced via tenant_id."""
        await self._db.table("conversation_events").insert(
            evt.model_dump(mode="json")
        ).execute()
```

### 3.1 Reasoning Token Batching

Reasoning tokens arrive at ~50ms intervals. Persisting each one individually would overwhelm Postgres. Instead, `StreamProcessor` accumulates reasoning tokens and flushes them as a single concatenated event on the next non-reasoning event or on a 500ms timer:

```python
# Inside StreamProcessor — reasoning accumulator
class _ReasoningBuffer:
    """Accumulates reasoning tokens, flushes as one DB row."""
    __slots__ = ("_parts", "_first_seq", "_last_seq")

    def __init__(self):
        self._parts: list[str] = []
        self._first_seq = 0
        self._last_seq = 0

    def append(self, text: str, seq: int) -> None:
        if not self._parts:
            self._first_seq = seq
        self._parts.append(text)
        self._last_seq = seq

    def flush(self, ctx: "RunContext") -> ActBIEvent | None:
        if not self._parts:
            return None
        evt = ActBIEvent(
            event_type="reasoning",
            conversation_id=ctx.conversation_id,
            message_id=ctx.message_id,
            seq=self._first_seq,
            tenant_id=ctx.tenant_id,
            payload={"text": "".join(self._parts), "token_count": len(self._parts)},
            variant=ctx.insight_variant,
        )
        self._parts.clear()
        return evt
```

The UI receives every individual token via SSE (for the typing effect). The database stores the batched text (for replay and lineage). This is the only place where the SSE wire and the persistence layer diverge.

---

## 4. Translation Layer — The Only LangGraph-Coupled Code

The translator is a **format converter**, not a logic layer. Its job is purely mechanical: LangGraph emits internal events in its own schema, and the translator wraps the output into an `ActBIEvent` envelope. It does not modify, filter, or enrich the agent's actual output. The payload passes through untouched.

This is the ONLY file that imports or understands LangGraph's internal event schema. Swap frameworks → change only this file.

```python
# actbi/streaming/translator.py
from actbi.streaming.events import ActBIEvent

# Tool name → ActBI event type
_TOOL_MAP = {
    "create_chart":            "chart_spec",
    "update_chart":            "chart_spec",
    "create_chart_stack":      "chart_stack_update",
    "generate_insight":        "insight",
    "generate_recommendation": "recommendation",
    "create_data_binding":     "data_binding",
    "add_highlight":           "highlight",
}

# Graph node → UI status label
_STATUS_MAP = {
    "intent_classifier":  "thinking",
    "schema_resolver":    "resolving_entities",
    "query_generator":    "querying_data",
    "viz_designer":       "generating_chart",
    "insight_generator":  "generating_insight",
}

def translate_lg_event(
    lg: dict, ctx: "RunContext", seq: int
) -> list[ActBIEvent]:
    """Pure function. LangGraph dict in → ActBIEvent list out."""
    kind = lg.get("event", "")
    out: list[ActBIEvent] = []

    if kind == "on_chat_model_stream":
        chunk = lg["data"].get("chunk")
        if chunk and hasattr(chunk, "content") and chunk.content:
            out.append(_evt(ctx, seq + 1, "reasoning", {"text": chunk.content}))

    elif kind == "on_tool_end":
        etype = _TOOL_MAP.get(lg.get("name", ""))
        if etype:
            output = lg["data"].get("output", {})
            # Extract causal links (tools may declare what prior events they depend on)
            caused_by = output.pop("_caused_by", [])
            out.append(_evt(
                ctx, seq + 1, etype, output,
                agent_node=lg.get("name"),
                caused_by=caused_by,
            ))

    elif kind == "on_chain_start":
        status = _STATUS_MAP.get(lg.get("name", ""))
        if status:
            out.append(_evt(ctx, seq + 1, "status", {"status": status}))

    return out


def _evt(ctx, seq, etype, payload, **kwargs) -> ActBIEvent:
    return ActBIEvent(
        event_type=etype,
        conversation_id=ctx.conversation_id,
        message_id=ctx.message_id,
        seq=seq,
        tenant_id=ctx.tenant_id,
        payload=payload,
        variant=ctx.insight_variant,
        **kwargs,
    )
```

---

## 5. EventBus — PostHog Milestone Bridge

From ADR-003, `EventBus` is the single place `posthog.capture()` is called. We add one method that accepts an `ActBIEvent` directly — the bridge between the streaming domain and the analytics domain:

```python
# actbi/core/events.py  (extending ADR-003's EventBus)
class EventBus:
    def __init__(self, posthog: Posthog) -> None:
        self._ph = posthog

    def from_event(self, evt: ActBIEvent, *, user_id: str) -> None:
        """Bridge: ActBIEvent → PostHog product event.

        Maps event_type to domain-prefixed PostHog event names.
        Only called for milestones (evt.is_milestone == True).
        """
        posthog_name = _EVENT_NAME_MAP.get(evt.event_type)
        if not posthog_name:
            return

        props = {
            "conversation_id": evt.conversation_id,
            "message_id": evt.message_id,
        }
        if evt.variant:
            props["$feature/insight_summarizer_variant"] = evt.variant

        # Event-type-specific properties
        match evt.event_type:
            case "chart_spec":
                props["chart_type"] = evt.payload.get("chart_type", "")
                props["chart_id"] = evt.payload.get("id", "")
            case "insight":
                props["insight_type"] = evt.payload.get("type", "")
                props["confidence"] = evt.payload.get("confidence", 0)
            case "recommendation":
                props["recommendation_type"] = evt.payload.get("type", "")
            case "done":
                pass  # conversation_id is sufficient
            case "error":
                props["error_type"] = evt.payload.get("error_type", "unknown")

        self._ph.capture(posthog_name, distinct_id=user_id, properties=props)

    # --- Explicit typed methods for non-streaming events (UI actions) ---

    def decision_insight_clicked(
        self, *, user_id: str, insight_id: str, conversation_id: str, action: str
    ) -> None:
        self._ph.capture("decision_insight_clicked", distinct_id=user_id, properties={
            "insight_id": insight_id,
            "conversation_id": conversation_id,
            "action": action,
        })

    def visualization_dashboard_published(
        self, *, user_id: str, dashboard_id: str, version: int, chart_count: int
    ) -> None:
        self._ph.capture("visualization_dashboard_published", distinct_id=user_id, properties={
            "dashboard_id": dashboard_id,
            "version": version,
            "chart_count": chart_count,
        })

    def visualization_dashboard_cloned(
        self, *, user_id: str, source_dashboard_id: str
    ) -> None:
        self._ph.capture("visualization_dashboard_cloned", distinct_id=user_id, properties={
            "source_dashboard_id": source_dashboard_id,
        })

    def flush(self) -> None:
        self._ph.flush()


_EVENT_NAME_MAP: dict[str, str] = {
    "chart_spec":         "visualization_chart_created",
    "chart_stack_update": "visualization_stack_created",
    "insight":            "decision_insight_generated",
    "recommendation":     "decision_recommendation_generated",
    "done":               "conversation_response_completed",
    "error":              "quality_agent_error",
}
```

Two emission paths:
- **Streaming milestones** → `from_event()` called by `StreamProcessor` as events flow
- **UI interactions** → typed methods called from FastAPI endpoints (dashboard publish, clone, insight click, etc.)

Both share `conversation_id` as the universal join key with Langfuse traces.

---

## 6. Database Schema

One table for the event log. One table for materialized reasoning lineage. RLS on both.

```sql
-- Event log: the single source of truth for what happened during streaming
CREATE TABLE conversation_events (
    event_id          TEXT PRIMARY KEY,
    event_type        TEXT NOT NULL,
    conversation_id   TEXT NOT NULL REFERENCES conversations(id),
    message_id        TEXT NOT NULL REFERENCES messages(id),
    seq               INT  NOT NULL,
    ts                TIMESTAMPTZ NOT NULL DEFAULT now(),
    tenant_id         TEXT NOT NULL,
    payload           JSONB NOT NULL,

    -- causal chain between events
    caused_by         TEXT[] DEFAULT '{}',

    -- execution metadata
    agent_node        TEXT,
    variant           TEXT,
    schema_version    INT DEFAULT 1,

    UNIQUE(conversation_id, message_id, seq)
);

CREATE INDEX idx_events_conv      ON conversation_events(conversation_id, seq);
CREATE INDEX idx_events_type      ON conversation_events(event_type);
CREATE INDEX idx_events_tenant    ON conversation_events(tenant_id);
CREATE INDEX idx_events_payload   ON conversation_events USING gin(payload);

ALTER TABLE conversation_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON conversation_events
    USING (tenant_id = current_setting('app.current_tenant')::text);

-- Materialized reasoning lineage (populated async by background worker)
CREATE TABLE reasoning_lineage (
    id                TEXT PRIMARY KEY,
    conversation_id   TEXT NOT NULL,
    message_id        TEXT NOT NULL,
    tenant_id         TEXT NOT NULL,
    steps             JSONB NOT NULL,    -- [{step, description, event_refs}]
    created_at        TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE reasoning_lineage ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON reasoning_lineage
    USING (tenant_id = current_setting('app.current_tenant')::text);
```

**Note on downstream consumers:** The `conversation_events` table is read by:
1. The replay endpoint (§10) for debugging and step-through UI
2. The reasoning lineage materializer (§11) for human-readable traces
3. The eval dataset generator (ADR-002 extension) for production regression suites
4. The decision journey materializer (separate design) for bounded decision traces
5. The decision vault pipeline (separate design) for RAG-indexed precedent search

None of these consumers write back to `conversation_events`. It is a pure append-only log.

---

## 7. The Route — Pure Wiring

Following ADR-003's principle: the route imports no SDKs, creates no events, makes no emission decisions.

```python
# actbi/api/routes/stream.py
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from actbi.core.dependencies import (
    get_stream_processor, get_agent_config, get_request_context,
)
from uuid import uuid4

router = APIRouter()

@router.post("/api/v1/stream/{conversation_id}")
async def stream_conversation(
    conversation_id: str,
    body: ConversationRequest,
    ctx:       RequestContext  = Depends(get_request_context),
    config:    AgentConfig     = Depends(get_agent_config),
    processor: StreamProcessor = Depends(get_stream_processor),
):
    run = RunContext(
        user_id=ctx.user_id,
        tenant_id=ctx.tenant_id,
        conversation_id=conversation_id,
        message_id=str(uuid4()),
        message=body.message,
        insight_variant=config.insight_variant,
        external_signals_enabled=config.external_signals_enabled,
        sql_fallback_strategy=config.sql_fallback_strategy,
        agent_graph=ctx.agent_graph,
    )
    return StreamingResponse(
        processor.run(run),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

---

## 8. Frontend Architecture

The frontend consumes the SSE stream through three layers: a **proxy route** (Next.js API route forwarding to FastAPI), a **stream service** (connection management, parsing, error handling), and a **React hook** (state management, handler dispatch). This separation ensures the connection logic is testable independently of React, and multiple UI components can consume the same stream.

### 8.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  React Components                                           │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Conversation │  │ ChartCanvas  │  │ InsightPanel     │  │
│  │ Panel        │  │              │  │                  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────────┘  │
│         │                 │                  │              │
│         └────────┬────────┴──────────────────┘              │
│                  │                                          │
│         ┌────────▼────────┐                                 │
│         │ useActBIStream  │  React hook: state + dispatch   │
│         └────────┬────────┘                                 │
│                  │                                          │
│         ┌────────▼────────┐                                 │
│         │ StreamService   │  Pure TS: connect, parse, retry │
│         └────────┬────────┘                                 │
│                  │                                          │
│         ┌────────▼────────┐                                 │
│         │ /api/stream/    │  Next.js proxy route            │
│         │ [conversationId]│                                 │
│         └────────┬────────┘                                 │
└──────────────────┼──────────────────────────────────────────┘
                   │ SSE
         ┌─────────▼─────────┐
         │ FastAPI backend   │
         │ StreamProcessor   │
         └───────────────────┘
```

### 8.2 Next.js Proxy Route

The proxy route forwards the client's POST to the FastAPI backend and streams the SSE response back. This keeps the FastAPI origin private and lets Vercel handle auth, rate limiting, and edge caching headers.

```typescript
// app/api/stream/[conversationId]/route.ts
import { NextRequest } from 'next/server'
import { auth } from '@/lib/auth'

const BACKEND_URL = process.env.ACTBI_BACKEND_URL!

export async function POST(
    request: NextRequest,
    { params }: { params: { conversationId: string } }
) {
    const session = await auth()
    if (!session) {
        return new Response('Unauthorized', { status: 401 })
    }

    const body = await request.json()

    const backendResp = await fetch(
        `${BACKEND_URL}/api/v1/stream/${params.conversationId}`,
        {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${session.accessToken}`,
                'X-Tenant-Id': session.tenantId,
            },
            body: JSON.stringify(body),
        }
    )

    if (!backendResp.ok) {
        return new Response(backendResp.statusText, {
            status: backendResp.status,
        })
    }

    // Stream the SSE response through to the client
    return new Response(backendResp.body, {
        headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    })
}
```

### 8.3 Stream Service

The service layer handles connection lifecycle, SSE parsing, error recovery, and abort logic. It is a plain TypeScript class with no React dependencies — testable with any test runner.

```typescript
// lib/services/stream-service.ts
import { createParser, type EventSourceMessage } from 'eventsource-parser'

// ── Types ──────────────────────────────────────────────────

/** Wire format matching ActBIEvent proto canonical JSON */
export interface ActBIEvent {
    event_id: string
    event_type: EventType
    conversation_id: string
    message_id: string
    seq: number
    ts: string
    tenant_id: string
    payload: Record<string, unknown>
    caused_by: string[]
    agent_node: string | null
    variant: string | null
    schema_version: number
}

export type EventType =
    | 'reasoning'
    | 'status'
    | 'chart_spec'
    | 'chart_stack_update'
    | 'insight'
    | 'recommendation'
    | 'data_binding'
    | 'highlight'
    | 'error'
    | 'done'

export interface StreamCallbacks {
    onEvent: (event: ActBIEvent) => void
    onError: (error: StreamError) => void
    onComplete: () => void
}

export interface StreamError {
    type: 'network' | 'parse' | 'server'
    message: string
    retryable: boolean
    status?: number
}

// ── Service ────────────────────────────────────────────────

export class StreamService {
    private abortController: AbortController | null = null

    /**
     * Opens an SSE connection for a conversation turn.
     * Parses each SSE frame into a typed ActBIEvent and dispatches
     * to callbacks. Returns when the stream completes or errors.
     */
    async stream(
        conversationId: string,
        message: string,
        callbacks: StreamCallbacks,
    ): Promise<void> {
        this.abort() // cancel any in-flight stream
        this.abortController = new AbortController()

        let response: Response
        try {
            response = await fetch(`/api/stream/${conversationId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message }),
                signal: this.abortController.signal,
            })
        } catch (err) {
            if ((err as Error).name === 'AbortError') return
            callbacks.onError({
                type: 'network',
                message: 'Failed to connect to streaming endpoint',
                retryable: true,
            })
            return
        }

        if (!response.ok) {
            callbacks.onError({
                type: 'server',
                message: `Server returned ${response.status}`,
                retryable: response.status >= 500,
                status: response.status,
            })
            return
        }

        // Parse SSE frames
        const parser = createParser({
            onEvent: (sseEvent: EventSourceMessage) => {
                try {
                    const evt: ActBIEvent = JSON.parse(sseEvent.data)
                    callbacks.onEvent(evt)

                    if (evt.event_type === 'done') {
                        callbacks.onComplete()
                    }
                } catch {
                    callbacks.onError({
                        type: 'parse',
                        message: `Failed to parse SSE frame: ${sseEvent.data}`,
                        retryable: false,
                    })
                }
            },
        })

        const reader = response.body!.getReader()
        const decoder = new TextDecoder()

        try {
            while (true) {
                const { done, value } = await reader.read()
                if (done) break
                parser.feed(decoder.decode(value, { stream: true }))
            }
        } catch (err) {
            if ((err as Error).name === 'AbortError') return
            callbacks.onError({
                type: 'network',
                message: 'Stream connection lost',
                retryable: true,
            })
        }
    }

    /** Cancel the in-flight stream. Safe to call multiple times. */
    abort(): void {
        this.abortController?.abort()
        this.abortController = null
    }

    get isActive(): boolean {
        return this.abortController !== null
            && !this.abortController.signal.aborted
    }
}
```

### 8.4 React Hook — `useActBIStream`

The hook manages React state and dispatches events to UI component handlers. It uses the `StreamService` internally but exposes a React-idiomatic API.

```typescript
// lib/hooks/useActBIStream.ts
import { useState, useCallback, useRef, useMemo } from 'react'
import { StreamService, type ActBIEvent, type StreamError } from '@/lib/services/stream-service'
import { trackEvent } from '@/lib/analytics'

// ── Handler interfaces ─────────────────────────────────────

/**
 * Handlers for each event type. Components register the handlers
 * they care about — the hook dispatches to the right one.
 *
 * Each handler receives (payload, fullEvent) so components can
 * access both the domain object and the event metadata.
 */
export interface StreamHandlers {
    // Conversation panel
    onReasoning?:       (text: string) => void
    onStatus?:          (status: string) => void

    // Chart canvas
    onChartSpec?:       (spec: ChartSpec, evt: ActBIEvent) => void
    onChartStackUpdate?:(stack: ChartStackUpdate, evt: ActBIEvent) => void
    onDataBinding?:     (binding: DataBinding, evt: ActBIEvent) => void
    onHighlight?:       (highlight: Highlight, evt: ActBIEvent) => void

    // Insight panel
    onInsight?:         (insight: Insight, evt: ActBIEvent) => void
    onRecommendation?:  (rec: Recommendation, evt: ActBIEvent) => void

    // Error / completion
    onError?:           (error: StreamError) => void
    onDone?:            () => void
}

// ── Hook state ─────────────────────────────────────────────

export interface StreamState {
    isStreaming: boolean
    agentStatus: string
    error: StreamError | null
}

// ── Hook ───────────────────────────────────────────────────

export function useActBIStream(handlers: StreamHandlers) {
    const [state, setState] = useState<StreamState>({
        isStreaming: false,
        agentStatus: '',
        error: null,
    })

    // StreamService instance persists across renders.
    // Not in state — it's imperative, not declarative.
    const serviceRef = useRef<StreamService>(new StreamService())

    // Ref to handlers so the dispatch closure doesn't go stale.
    const handlersRef = useRef(handlers)
    handlersRef.current = handlers

    const sendMessage = useCallback(async (
        conversationId: string,
        message: string,
    ) => {
        setState({ isStreaming: true, agentStatus: '', error: null })

        await serviceRef.current.stream(conversationId, message, {
            onEvent: (evt: ActBIEvent) => {
                const h = handlersRef.current

                switch (evt.event_type) {
                    // ── Conversation panel ──
                    case 'reasoning':
                        h.onReasoning?.(evt.payload.text as string)
                        break

                    case 'status':
                        setState(s => ({
                            ...s,
                            agentStatus: evt.payload.status as string,
                        }))
                        h.onStatus?.(evt.payload.status as string)
                        break

                    // ── Chart canvas ──
                    case 'chart_spec':
                        h.onChartSpec?.(evt.payload as unknown as ChartSpec, evt)
                        trackEvent('visualization_chart_created', {
                            conversation_id: evt.conversation_id,
                            chart_type: evt.payload.chart_type,
                            chart_id: evt.payload.id,
                        })
                        break

                    case 'chart_stack_update':
                        h.onChartStackUpdate?.(
                            evt.payload as unknown as ChartStackUpdate, evt,
                        )
                        break

                    case 'data_binding':
                        h.onDataBinding?.(
                            evt.payload as unknown as DataBinding, evt,
                        )
                        break

                    case 'highlight':
                        h.onHighlight?.(
                            evt.payload as unknown as Highlight, evt,
                        )
                        break

                    // ── Insight panel ──
                    case 'insight':
                        h.onInsight?.(evt.payload as unknown as Insight, evt)
                        break

                    case 'recommendation':
                        h.onRecommendation?.(
                            evt.payload as unknown as Recommendation, evt,
                        )
                        break

                    // ── Error ──
                    case 'error':
                        setState(s => ({
                            ...s,
                            error: {
                                type: 'server',
                                message: evt.payload.message as string,
                                retryable: false,
                            },
                        }))
                        h.onError?.({
                            type: 'server',
                            message: evt.payload.message as string,
                            retryable: false,
                        })
                        break

                    // ── Done ──
                    case 'done':
                        setState({
                            isStreaming: false,
                            agentStatus: '',
                            error: null,
                        })
                        h.onDone?.()
                        break
                }
            },

            onError: (error: StreamError) => {
                setState(s => ({ ...s, isStreaming: false, error }))
                handlersRef.current.onError?.(error)
            },

            onComplete: () => {
                // done event already handled above
            },
        })
    }, [])

    const cancel = useCallback(() => {
        serviceRef.current.abort()
        setState({ isStreaming: false, agentStatus: '', error: null })
    }, [])

    return {
        sendMessage,
        cancel,
        ...state,
    }
}
```

### 8.5 Component Integration Example

Here's how the page-level component wires the hook to the different UI regions. Each handler updates only the state slice relevant to its region:

```typescript
// app/conversation/[id]/page.tsx
'use client'

import { useState, useCallback } from 'react'
import { useActBIStream } from '@/lib/hooks/useActBIStream'
import { ConversationPanel } from '@/components/conversation-panel'
import { ChartCanvas } from '@/components/chart-canvas'
import { InsightPanel } from '@/components/insight-panel'
import { AgentStatusBar } from '@/components/agent-status-bar'
import type { ChartSpec, Insight, Recommendation, ActBIEvent } from '@/lib/services/stream-service'

export default function ConversationPage({
    params,
}: {
    params: { id: string }
}) {
    // ── State slices per UI region ──
    const [reasoning, setReasoning] = useState('')
    const [charts, setCharts] = useState<ChartSpec[]>([])
    const [insights, setInsights] = useState<Insight[]>([])
    const [recommendations, setRecommendations] = useState<Recommendation[]>([])

    // ── Stream hook with handlers per region ──
    const { sendMessage, cancel, isStreaming, agentStatus, error } =
        useActBIStream({
            // Conversation panel: accumulate reasoning text
            onReasoning: useCallback((text: string) => {
                setReasoning(prev => prev + text)
            }, []),

            // Chart canvas: append new charts
            onChartSpec: useCallback((spec: ChartSpec, evt: ActBIEvent) => {
                setCharts(prev => [...prev, spec])
            }, []),

            // Insight panel: append insights and recommendations
            onInsight: useCallback((insight: Insight) => {
                setInsights(prev => [...prev, insight])
            }, []),

            onRecommendation: useCallback((rec: Recommendation) => {
                setRecommendations(prev => [...prev, rec])
            }, []),

            // Reset reasoning buffer when new turn starts
            onDone: useCallback(() => {
                setReasoning('')
            }, []),
        })

    const handleSend = useCallback((message: string) => {
        // Clear previous turn's transient state
        setReasoning('')
        sendMessage(params.id, message)
    }, [params.id, sendMessage])

    return (
        <div className="flex h-screen">
            {/* Left: conversation + reasoning */}
            <ConversationPanel
                reasoning={reasoning}
                onSend={handleSend}
                isStreaming={isStreaming}
                onCancel={cancel}
            />

            {/* Center: charts and stacks */}
            <ChartCanvas charts={charts} />

            {/* Right: insights and recommendations */}
            <InsightPanel
                insights={insights}
                recommendations={recommendations}
            />

            {/* Top bar: agent status */}
            <AgentStatusBar
                status={agentStatus}
                isStreaming={isStreaming}
                error={error}
            />
        </div>
    )
}
```

### 8.6 Client-Side PostHog

PostHog fires on both server and client for different reasons:

| Source | What it captures | Why needed |
|--------|-----------------|------------|
| **Backend** (`EventBus.from_event`) | Agent metadata: variant, agent_node, chart_type | Backend knows *why* the chart was created |
| **Client** (`trackEvent` in hook) | Session context: viewport, session_id, referrer | Client knows *where* the user was |

PostHog deduplicates on event name + distinct_id + timestamp window. Both sources share `conversation_id` as the join key.

```typescript
// lib/analytics.ts — typed PostHog helpers (from ADR-003)
import posthog from 'posthog-js'

type EventMap = {
    visualization_chart_created: {
        conversation_id: string
        chart_type: string
        chart_id: string
    }
    decision_insight_clicked: {
        conversation_id: string
        insight_id: string
        action: 'expand' | 'dismiss' | 'act'
    }
    visualization_dashboard_published: {
        dashboard_id: string
        version: number
        chart_count: number
    }
}

export function trackEvent<K extends keyof EventMap>(
    name: K,
    properties: EventMap[K],
): void {
    posthog.capture(name, properties)
}
```

### 8.7 Replay Support

The same `StreamService` can consume the replay endpoint (§10). Since replay emits identical SSE frames with the same event types, the hook dispatches to the same handlers:

```typescript
// lib/hooks/useReplay.ts
import { useCallback, useRef } from 'react'
import { StreamService } from '@/lib/services/stream-service'
import type { StreamHandlers } from './useActBIStream'

export function useReplay(handlers: StreamHandlers) {
    const serviceRef = useRef(new StreamService())

    const replay = useCallback(async (
        conversationId: string,
        messageId: string,
        speed: number = 1.0,
    ) => {
        // Replay uses GET, not POST — extend StreamService or
        // use fetch directly for the different endpoint shape.
        const response = await fetch(
            `/api/replay/${conversationId}/${messageId}?speed=${speed}`,
        )
        // Same SSE parsing logic applies — events dispatch
        // to the same handlers, rendering the same UI transitions.
        // ...
    }, [handlers])

    return { replay, cancel: () => serviceRef.current.abort() }
}
```

---

## 9. Observability Integration Points

Mapping to ADR-003's components:

| ADR-003 Component | Role in Streaming Architecture |
|---|---|
| `FlagService` | Resolves flags into `AgentConfig` **before** `StreamProcessor.run()` starts. Zero flag checks during streaming. |
| `CallbackFactory` | Creates Langfuse + PostHog LangChain callbacks passed to `astream_events()`. Agents are traced automatically. |
| `EventBus` | Receives milestone events from `StreamProcessor` via `from_event()`. Also receives UI interaction events from FastAPI endpoints. |
| `StreamProcessor` | Owns the loop. Calls translator, persists, emits to EventBus, yields SSE. The only code that touches events. |

The agent code remains completely clean:

```python
# agents/nodes/insight_summarizer.py — unchanged from ADR-003
def insight_summarizer_node(state: AgentState) -> AgentState:
    prompt = PROMPTS[state["insight_variant"]]
    # LLM call traced by Langfuse callback automatically
    # Tool outputs carry artifact IDs for downstream consumers
    ...
```

### 9.1 Universal Join Key

`conversation_id` links all systems:

| System | Field | What It Captures |
|---|---|---|
| **conversation_events** (Postgres) | `conversation_id` | Every event: specs, insights, reasoning, status |
| **Langfuse** | `session_id` | Per-span LLM traces: tokens, latency, cost, tool calls |
| **PostHog** | property: `conversation_id` | Product milestones: chart_created, dashboard_published |
| **reasoning_lineage** (Postgres) | `conversation_id` | Human-readable decision trace per message turn |
| **decision_journeys** (future) | `conversation_ids[]` | Bounded decision traces linking conversations to artifacts |
| **decision_vault** (future, Qdrant) | payload: `journey_id` | Embedded journey summaries for precedent search |

To debug a conversation:
1. **PostHog** → find in funnels, see which milestones fired
2. **Langfuse** → filter by `session_id`, see agent spans, costs
3. **conversation_events** → replay the exact SSE stream the user saw
4. **reasoning_lineage** → read the deterministic step-by-step trace

No system queries another. Each has `conversation_id` and answers its own questions independently. The Dagster nightly pipeline joins PostHog exports + Langfuse exports on `conversation_id` for cross-system analysis.

---

## 10. Replay Endpoint

Re-emits stored events as SSE. Powers debugging, the reasoning lineage UI's step-through mode, and the "show me what I saw on Tuesday" feature. Because it emits the same SSE frame format as live streaming, the frontend `StreamService` and `useActBIStream` hook work without modification.

```python
# actbi/api/routes/replay.py
@router.get("/api/v1/replay/{conversation_id}/{message_id}")
async def replay(
    conversation_id: str,
    message_id: str,
    speed: float = 1.0,
    tenant_ctx = Depends(get_request_context),
):
    async def stream():
        events = await db.table("conversation_events") \
            .select("*") \
            .eq("conversation_id", conversation_id) \
            .eq("message_id", message_id) \
            .order("seq") \
            .execute()

        prev_ts = None
        for row in events.data:
            if prev_ts and speed > 0:
                delta = (row["ts"] - prev_ts).total_seconds()
                await asyncio.sleep(delta / speed)
            prev_ts = row["ts"]
            yield f"event: {row['event_type']}\ndata: {json.dumps(row)}\n\n"

        yield 'event: done\ndata: {"status":"replay_complete"}\n\n'

    return StreamingResponse(stream(), media_type="text/event-stream")
```

---

## 11. Reasoning Lineage Materialization

A background job reads completed message turns and produces human-readable lineage. Triggered by the `done` event.

```python
# dagster job: materialize_reasoning_lineage
async def materialize_lineage(conversation_id: str, message_id: str):
    events = await db.table("conversation_events") \
        .select("*") \
        .eq("conversation_id", conversation_id) \
        .eq("message_id", message_id) \
        .neq("event_type", "reasoning") \
        .order("seq") \
        .execute()

    steps = []
    for evt in events.data:
        desc = _TEMPLATES.get(evt["event_type"], "").format(**evt)
        if desc:
            steps.append({
                "step": len(steps) + 1,
                "description": desc,
                "event_refs": [evt["event_id"]],
            })

    await db.table("reasoning_lineage").upsert({
        "id": f"lineage_{message_id}",
        "conversation_id": conversation_id,
        "message_id": message_id,
        "tenant_id": events.data[0]["tenant_id"],
        "steps": steps,
    }).execute()

_TEMPLATES = {
    "status":             "",  # skip
    "chart_spec":         "Generated {payload[chart_type]} chart: {payload[title]}",
    "insight":            "Identified {payload[type]} insight (confidence {payload[confidence]:.0%}): {payload[summary]}",
    "recommendation":     "Suggested {payload[type]} action: {payload[summary]}",
    "chart_stack_update": "Grouped charts into stack: {payload[title]}",
    "data_binding":       "Created data binding for {payload[id]}",
    "highlight":          "Highlighted {payload[type]} on chart data",
}
```

Deterministic templates for individual steps (auditable, reproducible). Optional LLM summarization for top-level narrative (presentation layer only, not stored as ground truth).

---

## 12. Eval Framework Integration

The event log integrates with ADR-002 (Evaluation Framework) in two ways:

### 12.1 Events as Eval Dataset Source

A Dagster job reads completed conversation turns from `conversation_events` and exports them as YAML datasets consumable by the eval framework. See the "Production Dataset Generation" section in ADR-002 for the full pipeline design including harvest, filter, and assertion derivation stages.

Key contract: `conversation_events.payload` stores the **complete** agent output (the canonical JSON of the domain protobuf). The eval framework's `reference_output` is populated directly from this field. The `variant` column enables segmenting production data by experiment arm.

### 12.2 Translator Transparency

The translator (§4) is a format converter that wraps agent output in an `ActBIEvent` envelope. It does not modify the payload. This means the eval framework scores the same output the user sees — there is no divergence between eval context and production context.

The only mutation the translator performs is extracting `_caused_by` from the tool output dict (which is internal causal metadata, not part of the domain output). Eval assertions should never reference `_caused_by` — it's a streaming concern, not an agent output.

---

## 13. Dependency Inventory

| Layer | Package | Status | Purpose |
|---|---|---|---|
| Backend | `fastapi` | Already in stack | SSE via `StreamingResponse` |
| Backend | `pydantic` | Already in stack | Event model validation |
| Backend | `langgraph` | Already in stack | `astream_events()` |
| Backend | `posthog` | ADR-003 | Product events + flag eval |
| Backend | `langfuse` | ADR-003 | LLM tracing via callbacks |
| Backend | `dependency-injector` | Already in stack | DI container |
| Frontend | `eventsource-parser` | **New** (sole addition) | SSE parsing |
| Frontend | `posthog-js` | ADR-003 | Client-side analytics |
| Frontend | `@vercel/flags` | ADR-003 | Server-side flag resolution |

Zero new backend packages beyond what ADR-003 already introduces. One new frontend package.

---

## 14. Implementation Phases

| Phase | Deliverable | Gate |
|---|---|---|
| **1** | `ActBIEvent` protobuf + Pydantic model + `translate_lg_event()` + unit tests | Translation tests pass for all LangGraph event types |
| **2** | `conversation_events` migration + `StreamProcessor` + persistence | httpx integration test: POST → SSE stream → events in DB |
| **3** | `EventBus.from_event()` bridge + PostHog milestone emission | Milestone events visible in PostHog Live Events |
| **4** | `CallbackFactory` integration (from ADR-003) | Langfuse trace created with `session_id = conversation_id` |
| **5** | Next.js proxy route + `StreamService` + `useActBIStream` hook | Browser receives SSE, handlers fire, PostHog client events emit |
| **6** | Component integration: ConversationPanel, ChartCanvas, InsightPanel | All event types render in correct UI regions |
| **7** | Replay endpoint + reasoning lineage materializer | Replay produces identical event sequence; lineage table populated |

Phases 1–6 are the MVP critical path. Phase 7 is the foundation for decision journeys and decision vault (separate designs).

---

## 15. What This Architecture Does NOT Do

- **No per-token persistence** — reasoning tokens stream to the UI but only batch-persist to Postgres
- **No event queue for MVP** — write-through to Postgres, not Pub/Sub. Add queue when fan-out demands it
- **No real-time decision vault** — decision journey materialization and vault indexing are async background jobs, not on the hot path
- **No entity_refs / edge_refs on events** — the XLake CustomerContextStore and the decision vault are separate systems with separate write paths. Events carry artifact IDs in payloads; downstream systems use those to build their own indexes
- **No WebSocket channel** — SSE for conversation streaming. WebSocket reserved for paired mobile-desktop mode (separate design)
- **No LangSmith** — Langfuse provides tracing without LangChain ecosystem lock-in
- **No Portkey** — Langfuse handles LLM observability without a proxy gateway
- **No OpenTelemetry in production** — Langfuse callbacks handle production tracing. OTel is used only in the eval framework (ADR-002) for in-memory test tracing

---

## 16. Open Design Decisions

The following are deferred to their respective design documents:

1. **Decision journey boundary detection** — how to detect journey start/completion signals, how to handle timeout-based implicit completion, and the `decision_journeys` table schema. (Decision Journey Design)
2. **Decision vault RAG pipeline** — chunking strategy for journey records, embedding model selection, Qdrant collection schema, retrieval strategies (semantic, metadata-filtered, hybrid). (Decision Vault Design)
3. **Production eval dataset generation** — the Dagster pipeline stages (harvest, filter, export), assertion derivation rules per event type, and CI integration. (ADR-002 extension)

---

## Appendix A: Decision Journey & Decision Vault — Design Sketch

This appendix captures the preliminary design for the two downstream systems that consume the event log. It is a reference sketch, not a final design. A dedicated design document will refine these concepts.

### A.1 Conceptual Model

The event log (`conversation_events`) is a raw time-series of everything that happened. Two layers of abstraction sit above it:

| Layer | What it is | Data structure | Storage |
|---|---|---|---|
| **1. Event Log** | Raw append-only events | `conversation_events` table | Postgres |
| **2. Decision Log** | Events queryable by conversation turn | Same table, queried by `(conversation_id, message_id, seq)` | Postgres |
| **3. Decision Journeys** | Bounded traces of a user's consult/reflect cycle | `decision_journeys` table, materialized from events | Postgres |
| **4. Decision Vault** | RAG-indexed knowledge base of completed journeys | Embedded journey records in a dedicated collection | Qdrant |

Layers 1–2 are defined in this ADR. Layers 3–4 are sketched below.

### A.2 Decision Journeys

A decision journey is a bounded trace of a user moving through ActBI's interaction cycle with a coherent intent. The UX Architecture defines the cycle: a user starts with a question (consult), produces charts and stacks through conversation, generates insights, acts on recommendations or publishes a dashboard, and optionally reflects on what they've built.

#### Boundary Detection

The boundary is artifact-based, not time-based. A journey may span minutes or days.

**Journey start signals:**
- New conversation initiated from scratch (no `from_dashboard_id`)
- "Clone dashboard" action beginning a new variant exploration (`visualization_dashboard_cloned` event)
- Explicit "build me a dashboard about X" request

**Journey continuation:**
- Every subsequent conversation turn, chart creation, chart refinement, stack creation, insight generation, and recommendation within the same conversation thread or linked to artifacts created within the journey
- Links followed via: `conversation_id` → `chart_ids` (from `chart_spec` event payloads) → `stack_id` (from `chart_stack_update` payloads) → `dashboard_id` (from dashboard events)

**Journey completion signals:**
- `visualization_dashboard_published` — user committed a durable artifact
- `decision_recommendation_acted` with type `report`, `share`, or `export` — user acted on output
- Session timeout / conversation closure without further interaction — implicit completion (configurable period)

#### Journey Data Structure

```yaml
decision_journey:
  journey_id:        "dj_abc123"
  tenant_id:         "tenant_xyz"
  user_id:           "user_456"
  started_at:        "2026-03-04T09:15:00Z"
  completed_at:      "2026-03-04T09:52:00Z"
  completion_signal:  "dashboard_published"

  # The artifact chain — IDs linking the full progression
  conversation_ids:  ["conv_1"]
  message_ids:       ["msg_1", "msg_2", "msg_3", "msg_4", "msg_5"]
  chart_ids:         ["chart_a", "chart_b", "chart_c"]
  stack_ids:         ["stack_1", "stack_2"]
  dashboard_id:      "dash_001"
  report_id:         null

  # The intent progression — what modes and tasks were used
  turns:
    - message_id: "msg_1"
      task: "consult"
      mode: "reporter"
      produced: ["chart_a"]
    - message_id: "msg_2"
      task: "reflect"
      mode: "interpreter"
      produced: ["chart_b"]
    - message_id: "msg_3"
      task: "reflect"
      mode: "explorer"
      produced: ["chart_c", "insight_1"]
    - message_id: "msg_4"
      task: "consult"
      mode: "interpreter"
      produced: ["stack_1", "stack_2"]
    - message_id: "msg_5"
      task: "reflect"
      mode: "explorer"
      produced: ["dash_001"]

  # Product outcome — what happened after
  outcome:
    dashboard_published: true
    insights_acted_on:   ["insight_1"]
    recommendations_acted_on: []
```

#### Materialization

A background Dagster job runs when it detects a completion signal. It walks backward through `conversation_events`, follows artifact ID links, and assembles the journey record. The `journey_id` is assigned at materialization time. The job does not write back to `conversation_events` — the event log is a pure append-only source.

### A.3 Decision Vault

The decision vault is a RAG knowledge base of completed decision journeys. It follows the same pipeline pattern as document extraction in the CustomerDocStore: ingest → chunk → extract metadata → embed → index → retrieve.

#### Stage 1: Ingestion

When a decision journey is materialized, it enters the vault pipeline. Triggered by the same completion signals that trigger journey materialization.

#### Stage 2: Chunking

Decision journeys have natural chunk boundaries — each conversation turn is a chunk. A turn contains the user's question, the agent's mode/task, the artifacts produced, and the insights generated. This is already structured, so chunking is trivial.

Two chunk types per journey:

**Turn-level chunks** — one per conversation turn. Contains the user's question, the agent's response mode, and what was produced. Fine-grained retrieval target.

**Journey-level chunk** — one per journey. A natural-language summary of the complete decision cycle. The primary retrieval target for precedent search. Example:

```
"Executive explored Q4 margin variance by region. Started with
revenue breakdown (consult/reporter), deepened into margin
contribution analysis (reflect/interpreter), discovered freight
cost correlation with Brazil sourcing via weather signals
(reflect/explorer). Published dashboard 'Q4 Regional Margins'
with 3 stacks covering revenue, costs, and external factors.
Key insight: 60% Brazil sourcing creates freight dependency."
```

Generated by the reasoning lineage materializer operating at journey level — deterministic templates for turn-level summaries, optional LLM pass for the journey-level narrative (since it's the primary retrieval target and benefits from natural language quality).

#### Stage 3: Metadata Extraction

Structured metadata for filtered retrieval, derived directly from the journey record:

- `tenant_id` — mandatory, enforces tenant isolation
- `user_role` — executive, analyst, etc.
- `data_domains` — from chart specs and data bindings (e.g., "finance", "logistics")
- `kpis_referenced` — from chart series names and insight content
- `modes_used` — ["reporter", "interpreter", "explorer"]
- `tasks_used` — ["consult", "reflect"]
- `completion_type` — "dashboard_published", "recommendation_acted", "timeout"
- `user_engaged` — derived from PostHog: did the user act on outputs (insight_clicked, chart_pinned)?
- `led_to_dashboard` — did the journey produce a published dashboard?
- `time_span` — journey duration

#### Stage 4: Embedding and Indexing

Journey-level and turn-level chunks are embedded and stored in Qdrant, in a collection dedicated to the decision vault (separate from CustomerContextStore collections).

```yaml
collection: decision_vault
  vector: journey summary embedding (or turn-level chunk embedding)
  payload:
    journey_id:       "dj_abc123"
    tenant_id:        "tenant_xyz"
    chunk_type:       "journey_summary" | "turn"
    message_id:       null | "msg_2"           # null for journey-level
    domains:          ["finance", "logistics"]
    kpis_referenced:  ["margin_pct", "revenue", "freight_cost"]
    modes_used:       ["reporter", "interpreter", "explorer"]
    tasks_used:       ["consult", "reflect"]
    completion_type:  "dashboard_published"
    outcome_quality:  "high"                    # derived from engagement signals
    started_at:       "2026-03-04T09:15:00Z"
    completed_at:     "2026-03-04T09:52:00Z"
    summary_text:     "Executive explored Q4 margin variance..."
```

#### Retrieval Strategies

Multiple retrieval methods, exactly as used for document RAG:

- **Semantic search** — "find journeys similar to this question" using vector similarity on journey summaries
- **Metadata-filtered search** — "find journeys about margin in the last 90 days" using Qdrant payload filters
- **Hybrid search** — semantic + metadata filters combined (e.g., "find journeys in the finance domain where an executive explored cost variance")

Tenanted by default — a tenant's decision vault only contains their own journeys.

### A.4 Product Features Enabled

**Agent context enrichment:** An agent handling a new conversation queries the vault: "has this user (or any user in this tenant) explored a similar question before?" If the vault returns a high-similarity journey, the agent can reference it: "You explored a similar question about margin variance last month. That analysis found freight cost sensitivity to Brazil sourcing. Want me to update that analysis with current data, or start fresh?"

**Morning Brew dashboard:** The auto-generated executive digest (from UX Architecture §5.6) pulls from the decision vault to find thematic connections across past journeys. Not just recent conversations — accumulated decision precedent enriching the narrative.

**Eval dataset generation:** The decision vault's structured journey records (with `outcome_quality` and `user_engaged` annotations) feed the production eval dataset pipeline (ADR-002 extension). Journeys where users engaged are higher-quality positive examples for regression testing.

**Compounding intelligence:** Every completed journey makes future conversations more informed. This is the Foundation Capital thesis realized — decision traces become searchable precedent that compounds over time.

### A.5 Separation from XLake CustomerContextStore

The decision vault and the XLake CustomerContextStore are completely separate systems:

| | CustomerContextStore | Decision Vault |
|---|---|---|
| **Contains** | Business knowledge: tables, fields, KPIs, joins, concepts, document metadata | Decision knowledge: what was asked, what was found, what was decided |
| **Write path** | Ingestion pipelines (Dagster), schema enrichment | Event log → journey materializer → vault pipeline |
| **Read path** | Agents at query time (entity resolution, SQL generation) | Agents at conversation start (precedent search), Morning Brew |
| **Qdrant collection** | `customer_context` | `decision_vault` |
| **Changes when** | Data sources change, users enrich schemas, documents ingested | Users complete decision journeys |

A future composition layer may read from both — e.g., "executives who explored freight costs (decision vault) also found that supplier diversification (CustomerContextStore business concept) was relevant" — but that sits above both systems, not inside either.

---

*ActBI · ADR-005 · Unified Streaming Architecture · March 2026*
