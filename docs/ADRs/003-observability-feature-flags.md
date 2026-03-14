# ADR-003: Observability & Feature Flag Strategy

| | |
|---|---|
| **Date** | March 2026 |
| **Status** | ✅ ACCEPTED |
| **Deciders** | Nikos (CTO), DevOps Engineer |
| **Applies to** | Next.js frontend · FastAPI backend · LangGraph agents |
| **Supersedes** | None |

---

## 1. Context

ActBI delivers AI-generated insights via a Server-Sent Events (SSE) stream carrying reasoning tokens, chart specifications, and recommendations from FastAPI to Next.js. We need to answer three operational questions across this architecture:

- Which users see which features? *(feature flags)*
- Are our agents performing well? *(LLM observability)*
- What are users actually doing? *(product analytics)*

These questions span three layers — React components, FastAPI request handlers, and LangGraph agent nodes — so the solution must work cleanly across all three without code pollution or vendor lock-in.

> **Key constraint:** Flag evaluation must complete before the SSE stream starts. Event capture must never block or delay the stream. LLM tracing must be async and non-intrusive to agent code.

---

## 2. Decision

We adopt a three-tool stack with clear separation of concerns:

| Tool | Layer | Responsibility |
|---|---|---|
| **PostHog EU Cloud** | Frontend + Backend | Product analytics (funnel events) · Feature flags with local evaluation |
| **Vercel Flags SDK** | Next.js only | Provider-agnostic flag abstraction · Server-side resolution before render/stream |
| **Langfuse** | Backend · Agents | LLM trace · Prompt versioning · Eval scores · Cost/latency per span |

**What we are NOT doing:**
- No **Portkey** — Langfuse covers LLM observability without a proxy
- No **OpenFeature** — adds abstraction with no practical benefit at our current scale
- No **per-token PostHog events** — only semantic product milestones go to PostHog; operational events stay in the logging stack

---

## 3. Architecture Overview

Each tool stays in its lane. No SDK crosses layer boundaries.

| Next.js Frontend | FastAPI Backend | LangGraph Agents |
|---|---|---|
| **Vercel Flags SDK** — resolves flags in RSCs before render/stream. Zero client-side flag network calls. | **FlagService** — typed methods over PostHog local eval. Resolves once per request into `AgentConfig`. | **No SDK imports** — agents receive plain typed state. No PostHog, no Langfuse, no flag checks. |
| **PostHogProvider** — wraps app. Session replay, autocapture, typed event helpers. | **EventBus** — typed PostHog capture methods. Only funnel milestones, not operational logs. | **LangChain callbacks** — Langfuse + PostHog injected via `config={"callbacks": [...]}`. Agents are unaware. |
| | **StreamProcessor** — owns SSE loop + all event emission decisions. Route is pure wiring. | |

---

## 4. Backend Implementation

### 4.1 Settings (Pydantic)

All SDK credentials owned by Pydantic Settings. The container reads from these — nothing else touches env vars directly.

```python
# core/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class PostHogSettings(BaseSettings):
    api_key: str
    flags_secure_key: str
    host: str = "https://eu.i.posthog.com"

class LangfuseSettings(BaseSettings):
    public_key: str
    secret_key: str
    host: str

class Settings(BaseSettings):
    posthog: PostHogSettings = PostHogSettings()
    langfuse: LangfuseSettings = LangfuseSettings()

    model_config = SettingsConfigDict(env_nested_delimiter="__")
```

```bash
# .env
POSTHOG__API_KEY=phc_...
POSTHOG__FLAGS_SECURE_KEY=phsec_...
LANGFUSE__PUBLIC_KEY=pk-lf-...
LANGFUSE__SECRET_KEY=sk-lf-...
LANGFUSE__HOST=https://cloud.langfuse.com
```

### 4.2 DI Container

PostHog and Langfuse are singletons. Higher-level services are built from them. Nothing outside the container instantiates an SDK client.

```python
# containers.py
from dependency_injector import containers, providers

class ObservabilityContainer(containers.DeclarativeContainer):
    config = providers.Configuration()

    posthog = providers.Singleton(
        Posthog,
        project_api_key=config.posthog.api_key,
        host=config.posthog.host,
        feature_flags_secure_api_key=config.posthog.flags_secure_key,
        feature_flags_polling_interval=30,
    )

    langfuse = providers.Singleton(
        Langfuse,
        public_key=config.langfuse.public_key,
        secret_key=config.langfuse.secret_key,
        host=config.langfuse.host,
    )

    flags            = providers.Singleton(FlagService,       posthog=posthog)
    event_bus        = providers.Singleton(EventBus,           posthog=posthog)
    callback_factory = providers.Singleton(CallbackFactory,    langfuse=langfuse, posthog=posthog)
    stream_processor = providers.Singleton(StreamProcessor,    event_bus=event_bus,
                                                               callback_factory=callback_factory)
```

### 4.3 FlagService — typed flag methods

FlagService wraps PostHog local evaluation. Every flag is a typed method returning a Python value. No flag key strings appear outside this file. Retiring a flag = deleting the method; pyright surfaces every reference instantly.

```python
# core/flags.py
from typing import Literal
from posthog import Posthog

class FlagService:
    def __init__(self, posthog: Posthog) -> None:
        self._ph = posthog

    def _get(self, key: str, user_id: str, tenant_id: str | None = None):
        return self._ph.get_feature_flag(
            key, user_id,
            person_properties={"tenant_id": tenant_id} if tenant_id else {},
        )

    def insight_variant(
        self, user_id: str, tenant_id: str
    ) -> Literal["control", "variant_b", "variant_c"]:
        v = self._get("insight_summarizer_variant", user_id, tenant_id)
        return v if v in ("control", "variant_b", "variant_c") else "control"  # type: ignore

    def external_signals_enabled(self, user_id: str, tenant_id: str) -> bool:
        return bool(self._get("enable_external_signals", user_id, tenant_id))

    def sql_fallback_strategy(
        self, user_id: str
    ) -> Literal["retry_smaller", "simplify", "disabled"]:
        v = self._get("sql_fallback_strategy", user_id)
        return v if v in ("retry_smaller", "simplify", "disabled") else "retry_smaller"  # type: ignore
```

> **Local evaluation:** PostHog SDK fetches flag definitions every 30 seconds and evaluates in-memory. Each flag check costs ~0ms. Changes in the PostHog dashboard are live within 30 seconds — no server restart required.

### 4.4 EventBus — typed product events

EventBus is the only place `posthog.capture()` is called. The full product event schema is visible by reading this one file. Only funnel milestones go here — operational events (errors, latency, request logs) belong in the logging stack.

```python
# core/events.py
from posthog import Posthog

class EventBus:
    def __init__(self, posthog: Posthog) -> None:
        self._ph = posthog

    def conversation_started(
        self, *, user_id: str, conversation_id: str, mode: str, variant: str
    ) -> None:
        self._ph.capture("conversation_started", distinct_id=user_id, properties={
            "conversation_id": conversation_id,
            "mode": mode,
            "$feature/insight_summarizer_variant": variant,
        })

    def chart_created(
        self, *, user_id: str, conversation_id: str, chart_type: str, variant: str
    ) -> None:
        self._ph.capture("visualization_chart_created", distinct_id=user_id, properties={
            "conversation_id": conversation_id,
            "chart_type": chart_type,
            "$feature/insight_summarizer_variant": variant,
        })

    def conversation_completed(
        self, *, user_id: str, conversation_id: str, latency_ms: int, variant: str
    ) -> None:
        self._ph.capture("conversation_response_received", distinct_id=user_id, properties={
            "conversation_id": conversation_id,
            "latency_ms": latency_ms,
            "$feature/insight_summarizer_variant": variant,
        })

    def flush(self) -> None:
        self._ph.flush()  # required before Cloud Run container exits
```

### 4.5 CallbackFactory — LLM observability

Composes LangChain callbacks for one agent run. Both Langfuse and PostHog receive the run via their handlers. Agents never import either SDK.

```python
# core/observability.py
from langfuse.callback import CallbackHandler as LangfuseCallback
from posthog.ai.langchain import CallbackHandler as PostHogCallback

class CallbackFactory:
    def __init__(self, langfuse: Langfuse, posthog: Posthog) -> None:
        self._langfuse = langfuse
        self._posthog = posthog

    def for_run(
        self, *, user_id: str, conversation_id: str, variant: str, tenant_id: str
    ) -> list:
        """
        Returns [LangfuseCallback, PostHogCallback].
        Pass as config={"callbacks": factory.for_run(...)}.

        Langfuse: full per-span trace, prompt version, eval scores.
        PostHog:  $ai_generation per LLM call (tokens, cost, latency).
        Both are async — never block the SSE stream.
        """
        return [
            LangfuseCallback(
                trace_name="actbi_agent_run",
                session_id=conversation_id,
                user_id=user_id,
                metadata={"variant": variant, "tenant_id": tenant_id},
            ),
            PostHogCallback(
                client=self._posthog,
                trace_id=conversation_id,
                properties={"variant": variant, "tenant_id": tenant_id},
            ),
        ]
```

### 4.6 FastAPI: Dependencies and Route

The container is bridged to FastAPI via thin `Depends` callables. `AgentConfig` is resolved once per request. The route is pure wiring — it builds a `RunContext` and hands off to `StreamProcessor`.

```python
# core/dependencies.py

# Bridge container → FastAPI Depends
def get_flag_service(request: Request) -> FlagService:
    return request.app.container.flags()

def get_stream_processor(request: Request) -> StreamProcessor:
    return request.app.container.stream_processor()

# All flags resolved once here, before the stream starts
async def get_agent_config(
    ctx: RequestContext = Depends(get_request_context),
    flags: FlagService  = Depends(get_flag_service),
) -> AgentConfig:
    return AgentConfig(
        insight_variant=flags.insight_variant(ctx.user_id, ctx.tenant_id),
        external_signals_enabled=flags.external_signals_enabled(ctx.user_id, ctx.tenant_id),
        sql_fallback_strategy=flags.sql_fallback_strategy(ctx.user_id),
    )
```

```python
# agents/sse_handler.py — route is pure wiring, zero SDK imports

@router.post("/api/stream")
async def stream_conversation(
    body: ConversationRequest,
    ctx:       RequestContext    = Depends(get_request_context),
    config:    AgentConfig       = Depends(get_agent_config),
    processor: StreamProcessor   = Depends(get_stream_processor),
):
    run = RunContext(
        user_id=ctx.user_id,
        conversation_id=body.conversation_id,
        message_id=str(uuid4()),
        insight_variant=config.insight_variant,
        external_signals_enabled=config.external_signals_enabled,
        sql_fallback_strategy=config.sql_fallback_strategy,
        ...
    )
    return StreamingResponse(
        processor.run(run),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

### 4.7 Agent Code — the result

Agent nodes receive plain typed state. No flag checks, no SDK calls. The callbacks passed via `config` handle all tracing automatically.

```python
# agents/nodes/insight_summarizer.py
from typing import TypedDict, Literal

class AgentState(TypedDict):
    query: str
    conversation_id: str
    insight_variant: Literal["control", "variant_b", "variant_c"]
    use_external_signals: bool
    sql_fallback_strategy: str

PROMPTS = {
    "control":   PROMPT_DEFAULT,
    "variant_b": PROMPT_CONCISE,
    "variant_c": PROMPT_STRUCTURED,
}

def insight_summarizer_node(state: AgentState) -> AgentState:
    prompt = PROMPTS[state["insight_variant"]]   # dict lookup, not a flag call
    # LLM call traced automatically by Langfuse + PostHog via callbacks in config
    ...
```

---

## 5. Frontend Implementation

### 5.1 PostHog Provider

```tsx
// app/providers.tsx
'use client'
import posthog from 'posthog-js'
import { PostHogProvider } from 'posthog-js/react'

if (typeof window !== 'undefined') {
  posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
    api_host: 'https://eu.i.posthog.com',
    ui_host: 'https://eu.posthog.com',
    capture_pageview: 'history_change',
    session_recording: { recordCrossOriginIframes: false },
  })
}

export function Providers({ children }: { children: React.ReactNode }) {
  return <PostHogProvider client={posthog}>{children}</PostHogProvider>
}
```

### 5.2 Vercel Flags SDK — server-side resolution

Flags declared as typed async functions. Resolved in Server Components before render — no client-side flag network calls.

```ts
// lib/flags.ts
import { flag } from '@vercel/flags/next'
import { PostHogAdapter } from '@vercel/flags/adapters/posthog'

const adapter = PostHogAdapter({
  personalApiKey: process.env.POSTHOG_PERSONAL_API_KEY!,
  projectId:      process.env.POSTHOG_PROJECT_ID!,
})

export const insightVariantFlag = flag<'control' | 'variant_b' | 'variant_c'>({
  key:          'insight_summarizer_variant',
  adapter,
  defaultValue: 'control',
})

// Usage in a Server Component:
// const variant = await insightVariantFlag()
// Pass to client as a prop — client never calls PostHog for flags
```

### 5.3 Typed Event Helpers

```ts
// lib/analytics.ts
import posthog from 'posthog-js'

type ActBIEvents = {
  conversation_started:        { conversation_id: string; mode: string }
  visualization_chart_created: { conversation_id: string; chart_type: string }
  dashboard_published:         { dashboard_id: string; chart_count: number }
}

export function trackEvent<K extends keyof ActBIEvents>(
  event: K, props: ActBIEvents[K]
) {
  posthog.capture(event, props)
}
```

### 5.4 SSE Hook — where client events fire

Events fire at semantic boundaries only — never per reasoning token. The experiment variant flows through the SSE envelope from the backend, so client events are automatically attributed to the correct flag variant.

```ts
// hooks/useActBIStream.ts
import { trackEvent } from '@/lib/analytics'

export function useActBIStream(conversationId: string) {
  const [state, setState] = useState<StreamState>({})

  useEffect(() => {
    const es = new EventSource(`/api/stream/${conversationId}`)

    es.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      switch (msg.type) {
        case 'chart_spec':
          setState(s => ({ ...s, charts: [...(s.charts ?? []), msg.payload] }))
          trackEvent('visualization_chart_created', {
            conversation_id: conversationId,
            chart_type: msg.payload.type,
          })
          break
        case 'reasoning':
          // never captured — just rendered
          setState(s => ({ ...s, reasoning: (s.reasoning ?? '') + msg.payload }))
          break
      }
    }
    return () => es.close()
  }, [conversationId])

  return state
}
```

---

## 6. Langfuse ↔ PostHog Integration

The two tools are complementary, linked by `conversation_id` as a universal join key.

| | Langfuse | PostHog |
|---|---|---|
| **Use case** | Debug why a response was slow or wrong | Measure funnel conversion across variants |
| **Granularity** | Per-span (every LLM call, tool call, node) | Per-conversation milestone |
| **Audience** | Engineers | Product / Growth |
| **Trigger** | LangChain callback (automatic) | `EventBus.capture()` at semantic boundaries |
| **Join key** | `session_id = conversation_id` | property: `conversation_id` |

A nightly Dagster pipeline joins both datasets on `conversation_id` to compute model-level metrics (cost, latency, quality scores) alongside product-level outcomes (funnel stage reached, dashboard published). This enables experiment analysis combining LLM quality with user behaviour.

---

## 7. Compliance

| Tool | Hosting | GDPR path |
|---|---|---|
| PostHog | EU Cloud (AWS eu-central-1) | Acts as Data Processor. DPA available. Same pricing as US. |
| Langfuse | Cloud Core → self-host at scale | Self-hosted = no data leaves your infra. Cloud uses SCCs. |
| Vercel Flags SDK | OSS — no data sent anywhere | Flag evaluation runs locally. No third-party calls. |

---

## 8. MVP Implementation Steps

| # | Task | Owner | Done when |
|---|---|---|---|
| 1 | PostHog EU account — enable DPA, note API key + flags secure key | Nikos | Keys in `.env`, DPA signed |
| 2 | Langfuse Cloud Core account (free tier) | Nikos | Keys in `.env` |
| 3 | Pydantic Settings nested config (`PostHogSettings`, `LangfuseSettings`) | Backend | Settings load from env, validated at startup |
| 4 | Container: `posthog` + `langfuse` singletons | Backend | Container wires clients, no global instantiation elsewhere |
| 5 | `FlagService` with first flag (`insight_summarizer_variant`) | Backend | Flag resolves locally, variant logged on startup |
| 6 | `EventBus` with `conversation_started` + `conversation_completed` | Backend | Events visible in PostHog Live Events |
| 7 | `CallbackFactory` composing Langfuse + PostHog callbacks | Backend | Test run creates trace in Langfuse + `$ai_generation` in PostHog |
| 8 | `StreamProcessor` owning SSE loop + event emission | Backend | Route is pure wiring, no SDK imports in handler |
| 9 | FastAPI `Depends` bridge (`get_flag_service`, `get_stream_processor`) | Backend | `get_agent_config` resolves `AgentConfig` in <5ms |
| 10 | Next.js: `PostHogProvider` + `posthog.init` (EU host) | Frontend | Session replay visible in PostHog |
| 11 | Vercel Flags SDK: `insightVariantFlag` backed by PostHog adapter | Frontend | Flag resolves server-side, passed as prop to client |
| 12 | `lib/analytics.ts` typed event helpers | Frontend | `trackEvent("dashboard_published", ...)` autocompletes |
| 13 | `useActBIStream` hook emitting `chart_created` events | Frontend | Funnel: `started → chart_created` visible in PostHog |
| 14 | Verify join: `conversation_id` in PostHog events + Langfuse traces | Backend | Dagster pipeline can join on `conversation_id` |

---

## 9. Cost Model

| Stage | PostHog EU | Langfuse | Total/mo |
|---|---|---|---|
| MVP / Internal | Free (<1M events) | Cloud Core $29 | ~$29 |
| Pilot (5–10 tenants) | ~$155 | Cloud Core $29–50 | ~$185 |
| Early production (50 tenants) | ~$500 | Cloud Core ~$100 | ~$600 |
| Growth (self-host Langfuse) | ~$700 | GCP infra ~$250 | ~$950 |

Migrate Langfuse to self-hosted (Cloud Run + Cloud SQL) when costs approach $500/mo — infrastructure (~$250/mo) becomes cheaper than the cloud tier. PostHog remains on EU Cloud throughout; self-hosting its 16-service stack is not cost-effective at this scale.

---

## 10. Consequences

**Positive:**
- Agent code is completely free of observability SDK imports — testable with no mocking
- Full event schema visible in two files: `core/flags.py` and `core/events.py`
- Retiring a flag or event is a single method deletion — pyright surfaces all references
- Experiment variant flows end-to-end: PostHog flag → `AgentConfig` → SSE envelope → client events
- Langfuse + PostHog share `conversation_id`, enabling cross-system analysis in Dagster

**Accepted trade-offs:**
- `StreamProcessor` is a God object for the SSE stream — justified because it is the only layer that can make semantic emission decisions
- Vercel Flags SDK adds a build dependency on `@vercel/flags` — acceptable given it is OSS and provider-agnostic
- PostHog local eval has a 30-second flag definition lag — acceptable for feature rollouts; critical kill-switches should use separate deployment mechanisms

---

*ActBI · ADR-003 · March 2026*
