"""OpenTelemetry integration for workflow tracing.

Provides OTel setup and span conversion for capturing agent execution
traces during evaluation.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from evals.framework.workflow.types import AgentTrace, ToolCall, WorkflowTrace

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import ReadableSpan

# Global exporter for capturing spans
_exporter: InMemorySpanExporter | None = None


def setup_otel_tracing() -> InMemorySpanExporter:
    """Set up OTel with in-memory exporter for evaluation."""
    global _exporter

    _exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(_exporter))
    trace.set_tracer_provider(provider)

    # Auto-instrument LangChain if available
    try:
        from opentelemetry.instrumentation.langchain import LangchainInstrumentor

        LangchainInstrumentor().instrument()
    except ImportError:
        pass  # LangChain instrumentation not available

    return _exporter


def get_exporter() -> InMemorySpanExporter | None:
    """Get the current exporter."""
    return _exporter


def clear_spans() -> None:
    """Clear captured spans."""
    if _exporter:
        _exporter.clear()


def get_finished_spans() -> list[ReadableSpan]:
    """Get all finished spans."""
    if _exporter:
        return list(_exporter.get_finished_spans())
    return []


@contextmanager
def capture_trace():
    """Context manager to capture spans during execution."""
    if _exporter is None:
        setup_otel_tracing()

    clear_spans()
    try:
        yield
    finally:
        pass  # Spans are captured automatically


def spans_to_workflow_trace(spans: list[ReadableSpan]) -> WorkflowTrace:
    """Convert OTel spans to WorkflowTrace."""
    workflow_trace = WorkflowTrace()

    for span in spans:
        attrs = dict(span.attributes) if span.attributes else {}
        name = span.name

        # Calculate duration
        duration_ms = 0.0
        if span.start_time and span.end_time:
            duration_ms = (span.end_time - span.start_time) / 1_000_000  # ns to ms

        # Check if it's a tool span
        if "tool" in name.lower() or attrs.get("openinference.span.kind") == "TOOL":
            tool_call = ToolCall(
                tool_name=attrs.get("tool.name", name),
                args=_extract_json_attr(attrs, "tool.input", "input"),
                result=_extract_json_attr(attrs, "tool.output", "output"),
                error=_get_error(span),
                duration_ms=duration_ms,
            )
            workflow_trace.tool_calls.append(tool_call)
        else:
            # It's an agent/chain span
            agent_trace = AgentTrace(
                agent_name=name,
                input=_extract_json_attr(attrs, "input", "llm.input") or {},
                output=_extract_json_attr(attrs, "output", "llm.output"),
                error=_get_error(span),
                duration_ms=duration_ms,
            )
            workflow_trace.agents.append(agent_trace)

    return workflow_trace


def _extract_json_attr(attrs: dict, *keys: str) -> dict | None:
    """Extract JSON attribute, trying multiple possible keys."""
    for key in keys:
        if key in attrs:
            val = attrs[key]
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except (json.JSONDecodeError, ValueError):
                    return {"raw": val}
            if isinstance(val, dict):
                return val
    return None


def _get_error(span: ReadableSpan) -> str | None:
    """Extract error from span status."""
    if span.status and span.status.status_code.name == "ERROR":
        return span.status.description or "Unknown error"
    return None
