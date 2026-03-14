"""Workflow evaluation module.

Provides tools for capturing and evaluating LangGraph workflow execution:
- WorkflowTrace: Full trace of workflow execution
- WorkflowTraceCallback: LangGraph callback for capturing traces
- ToolCall: Record of a single tool invocation
- AgentTrace/AgentSpan: Trace of a single agent execution

OpenTelemetry support:
- setup_otel_tracing: Initialize OTel with in-memory exporter
- capture_trace: Context manager for capturing spans
- spans_to_workflow_trace: Convert OTel spans to WorkflowTrace

Example (callback-based):
    from evals.framework.workflow import WorkflowTraceCallback, WorkflowTrace

    # Create callback to capture trace
    callback = WorkflowTraceCallback()

    # Run workflow with callback
    workflow.invoke({"input": "test"}, config={"callbacks": [callback]})

    # Access trace for evaluation
    trace = callback.trace
    assert not trace.has_errors()
    assert "IntentClassifier" in trace.agents_invoked()

Example (OTel-based):
    from evals.framework.workflow import (
        setup_otel_tracing,
        capture_trace,
        get_finished_spans,
        spans_to_workflow_trace,
    )

    # Set up OTel tracing
    setup_otel_tracing()

    # Run workflow with trace capture
    with capture_trace():
        workflow.invoke({"input": "test"})

    # Convert to WorkflowTrace
    trace = spans_to_workflow_trace(get_finished_spans())
    assert not trace.has_errors()
"""

# Import evaluators to register them
from evals.framework.workflow import evaluators as _evaluators  # noqa: F401
from evals.framework.workflow.callback import WorkflowTraceCallback
from evals.framework.workflow.otel import (
    capture_trace,
    clear_spans,
    get_exporter,
    get_finished_spans,
    setup_otel_tracing,
    spans_to_workflow_trace,
)
from evals.framework.workflow.types import (
    AgentSpan,
    AgentTrace,
    ToolCall,
    WorkflowTrace,
)

__all__ = [
    # Core types
    "WorkflowTrace",
    "ToolCall",
    "AgentTrace",
    "AgentSpan",  # Alias for AgentTrace
    # Callback-based tracing
    "WorkflowTraceCallback",
    # OTel-based tracing
    "setup_otel_tracing",
    "get_exporter",
    "clear_spans",
    "get_finished_spans",
    "capture_trace",
    "spans_to_workflow_trace",
]
