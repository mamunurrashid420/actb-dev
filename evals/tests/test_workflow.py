"""Tests for the workflow evaluation module.

Tests for Phase 4 of the evaluation framework: Workflow Evaluation.
Tests trace types, callback handler, OTel integration, and workflow evaluators.
"""

from evals.framework.workflow.callback import WorkflowTraceCallback
from evals.framework.workflow.types import (
    AgentSpan,
    AgentTrace,
    ToolCall,
    WorkflowTrace,
)

# ─────────────────────────────────────────────────────────────────────────────
# ToolCall Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestToolCall:
    """Tests for ToolCall dataclass."""

    def test_creation(self):
        """Should create ToolCall with required fields."""
        tc = ToolCall(tool_name="search", args={"query": "gdp"})
        assert tc.tool_name == "search"
        assert tc.args == {"query": "gdp"}
        assert tc.result is None
        assert tc.error is None

    def test_creation_with_result(self):
        """Should create ToolCall with result."""
        tc = ToolCall(tool_name="search", args={"query": "gdp"}, result="data")
        assert tc.result == "data"

    def test_creation_with_error(self):
        """Should create ToolCall with error."""
        tc = ToolCall(tool_name="search", args={}, error="failed")
        assert tc.error == "failed"

    def test_creation_with_duration(self):
        """Should create ToolCall with duration."""
        tc = ToolCall(tool_name="search", args={}, duration_ms=150.5)
        assert tc.duration_ms == 150.5


# ─────────────────────────────────────────────────────────────────────────────
# AgentTrace Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAgentTrace:
    """Tests for AgentTrace dataclass."""

    def test_creation(self):
        """Should create AgentTrace with required fields."""
        at = AgentTrace(agent_name="IntentClassifier", input={"message": "hello"})
        assert at.agent_name == "IntentClassifier"
        assert at.input == {"message": "hello"}
        assert at.output is None
        assert at.tool_calls == []
        assert at.error is None
        assert at.duration_ms == 0

    def test_creation_with_output(self):
        """Should create AgentTrace with output."""
        at = AgentTrace(
            agent_name="IntentClassifier",
            input={"message": "hello"},
            output={"intent": "greeting"},
        )
        assert at.output == {"intent": "greeting"}

    def test_creation_with_tool_calls(self):
        """Should create AgentTrace with tool calls."""
        tc = ToolCall(tool_name="search", args={})
        at = AgentTrace(agent_name="DataAgent", input={}, tool_calls=[tc])
        assert len(at.tool_calls) == 1
        assert at.tool_calls[0].tool_name == "search"

    def test_creation_with_error(self):
        """Should create AgentTrace with error."""
        at = AgentTrace(agent_name="FailAgent", input={}, error="boom")
        assert at.error == "boom"


class TestAgentSpanAlias:
    """Tests for AgentSpan alias."""

    def test_alias_is_agent_trace(self):
        """AgentSpan should be an alias for AgentTrace."""
        assert AgentSpan is AgentTrace

    def test_can_use_alias(self):
        """Should be able to use AgentSpan like AgentTrace."""
        span = AgentSpan(agent_name="TestAgent", input={"key": "value"})
        assert span.agent_name == "TestAgent"
        assert span.input == {"key": "value"}


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowTrace Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestWorkflowTrace:
    """Tests for WorkflowTrace dataclass."""

    def test_get_agent_found(self):
        """Should find agent by name."""
        trace = WorkflowTrace(
            agents=[
                AgentTrace(agent_name="A", input={}),
                AgentTrace(agent_name="B", input={}),
            ]
        )
        agent = trace.get_agent("A")
        assert agent is not None
        assert agent.agent_name == "A"

    def test_get_agent_not_found(self):
        """Should return None when agent not found."""
        trace = WorkflowTrace()
        assert trace.get_agent("X") is None

    def test_has_errors_no_errors(self):
        """Should return False when no errors."""
        trace = WorkflowTrace(agents=[AgentTrace(agent_name="A", input={})])
        assert trace.has_errors() is False

    def test_has_errors_agent_error(self):
        """Should return True when agent has error."""
        trace = WorkflowTrace(
            agents=[AgentTrace(agent_name="A", input={}, error="boom")]
        )
        assert trace.has_errors() is True

    def test_has_errors_tool_error(self):
        """Should return True when tool has error."""
        trace = WorkflowTrace(
            tool_calls=[ToolCall(tool_name="search", args={}, error="failed")]
        )
        assert trace.has_errors() is True

    def test_has_errors_empty_trace(self):
        """Should return False for empty trace."""
        trace = WorkflowTrace()
        assert trace.has_errors() is False

    def test_agents_invoked(self):
        """Should return list of agent names."""
        trace = WorkflowTrace(
            agents=[
                AgentTrace(agent_name="A", input={}),
                AgentTrace(agent_name="B", input={}),
            ]
        )
        assert trace.agents_invoked() == ["A", "B"]

    def test_agents_invoked_empty(self):
        """Should return empty list when no agents."""
        trace = WorkflowTrace()
        assert trace.agents_invoked() == []

    def test_get_tool_calls(self):
        """Should return list of tool calls for a specific tool."""
        trace = WorkflowTrace(
            tool_calls=[
                ToolCall(tool_name="search", args={"q": "1"}),
                ToolCall(tool_name="get", args={}),
                ToolCall(tool_name="search", args={"q": "2"}),
            ]
        )
        searches = trace.get_tool_calls("search")
        assert len(searches) == 2
        assert searches[0].args == {"q": "1"}
        assert searches[1].args == {"q": "2"}

    def test_get_tool_calls_not_found(self):
        """Should return empty list when tool not found."""
        trace = WorkflowTrace(tool_calls=[ToolCall(tool_name="search", args={})])
        assert trace.get_tool_calls("unknown") == []

    def test_get_tool_calls_empty(self):
        """Should return empty list when no tool calls."""
        trace = WorkflowTrace()
        assert trace.get_tool_calls("search") == []


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowTraceCallback Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestWorkflowTraceCallback:
    """Tests for WorkflowTraceCallback."""

    def test_initial_state(self):
        """Should start with empty trace."""
        cb = WorkflowTraceCallback()
        assert len(cb.trace.agents) == 0
        assert len(cb.trace.tool_calls) == 0

    def test_captures_agent_start_end(self):
        """Should capture agent execution."""
        cb = WorkflowTraceCallback()
        cb.on_chain_start({"name": "TestAgent"}, {"input": "test"})
        cb.on_chain_end({"output": "result"})

        assert len(cb.trace.agents) == 1
        assert cb.trace.agents[0].agent_name == "TestAgent"
        assert cb.trace.agents[0].input == {"input": "test"}
        assert cb.trace.agents[0].output == {"output": "result"}

    def test_captures_agent_duration(self):
        """Should capture agent duration."""
        cb = WorkflowTraceCallback()
        cb.on_chain_start({"name": "TestAgent"}, {})
        cb.on_chain_end({})

        assert cb.trace.agents[0].duration_ms > 0

    def test_captures_agent_error(self):
        """Should capture agent error."""
        cb = WorkflowTraceCallback()
        cb.on_chain_start({"name": "TestAgent"}, {})
        cb.on_chain_error(Exception("failed"))

        assert len(cb.trace.agents) == 1
        assert cb.trace.agents[0].error == "failed"

    def test_captures_tool_calls(self):
        """Should capture tool calls."""
        cb = WorkflowTraceCallback()
        cb.on_tool_start({"name": "search"}, '{"query": "gdp"}')
        cb.on_tool_end("results")

        assert len(cb.trace.tool_calls) == 1
        assert cb.trace.tool_calls[0].tool_name == "search"
        assert cb.trace.tool_calls[0].args == {"query": "gdp"}
        assert cb.trace.tool_calls[0].result == "results"

    def test_captures_tool_error(self):
        """Should capture tool error."""
        cb = WorkflowTraceCallback()
        cb.on_tool_start({"name": "search"}, "{}")
        cb.on_tool_error(Exception("tool failed"))

        assert len(cb.trace.tool_calls) == 1
        assert cb.trace.tool_calls[0].error == "tool failed"

    def test_associates_tools_with_agent(self):
        """Should associate tool calls with current agent."""
        cb = WorkflowTraceCallback()
        cb.on_chain_start({"name": "DataAgent"}, {})
        cb.on_tool_start({"name": "search"}, '{"query": "test"}')
        cb.on_tool_end("results")
        cb.on_chain_end({})

        assert len(cb.trace.agents[0].tool_calls) == 1
        assert cb.trace.agents[0].tool_calls[0].tool_name == "search"

    def test_handles_raw_input_string(self):
        """Should handle non-JSON input string."""
        cb = WorkflowTraceCallback()
        cb.on_tool_start({"name": "search"}, "raw input")
        cb.on_tool_end("results")

        assert cb.trace.tool_calls[0].args == {"raw": "raw input"}

    def test_uses_id_if_no_name(self):
        """Should use id as agent name if name not provided."""
        cb = WorkflowTraceCallback()
        cb.on_chain_start({"id": ["module", "MyAgent"]}, {})
        cb.on_chain_end({})

        assert cb.trace.agents[0].agent_name == "MyAgent"

    def test_uses_unknown_if_no_id_or_name(self):
        """Should use 'unknown' if neither name nor id provided."""
        cb = WorkflowTraceCallback()
        cb.on_chain_start({}, {})
        cb.on_chain_end({})

        assert cb.trace.agents[0].agent_name == "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Workflow Evaluator Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestNoErrorsEvaluator:
    """Tests for no-errors evaluator."""

    def test_passes_when_clean(self):
        """Should pass when no errors in trace."""
        from evals.framework.assertions.evaluators import EVALUATORS
        from evals.framework.assertions.types import Assertion, EvalContext

        trace = WorkflowTrace()
        ctx = EvalContext(duration_seconds=1.0, trace=trace)
        asn = Assertion(type="no-errors")

        result = EVALUATORS["no-errors"](None, asn, ctx)
        assert result is True

    def test_passes_without_trace(self):
        """Should pass when no trace (no workflow to evaluate)."""
        from evals.framework.assertions.evaluators import EVALUATORS
        from evals.framework.assertions.types import Assertion, EvalContext

        ctx = EvalContext(duration_seconds=1.0)
        asn = Assertion(type="no-errors")

        result = EVALUATORS["no-errors"](None, asn, ctx)
        assert result is True

    def test_fails_on_agent_error(self):
        """Should fail when agent has error."""
        from evals.framework.assertions.evaluators import EVALUATORS
        from evals.framework.assertions.types import Assertion, EvalContext

        trace = WorkflowTrace(
            agents=[AgentTrace(agent_name="A", input={}, error="boom")]
        )
        ctx = EvalContext(duration_seconds=1.0, trace=trace)
        asn = Assertion(type="no-errors")

        result = EVALUATORS["no-errors"](None, asn, ctx)
        assert result is False

    def test_fails_on_tool_error(self):
        """Should fail when tool has error."""
        from evals.framework.assertions.evaluators import EVALUATORS
        from evals.framework.assertions.types import Assertion, EvalContext

        trace = WorkflowTrace(
            tool_calls=[ToolCall(tool_name="search", args={}, error="failed")]
        )
        ctx = EvalContext(duration_seconds=1.0, trace=trace)
        asn = Assertion(type="no-errors")

        result = EVALUATORS["no-errors"](None, asn, ctx)
        assert result is False


class TestAgentInvokedEvaluator:
    """Tests for agent-invoked evaluator."""

    def test_passes_when_agent_invoked(self):
        """Should pass when specified agent was invoked."""
        from evals.framework.assertions.evaluators import EVALUATORS
        from evals.framework.assertions.types import Assertion, EvalContext

        trace = WorkflowTrace(
            agents=[AgentTrace(agent_name="IntentClassifier", input={})]
        )
        ctx = EvalContext(duration_seconds=1.0, trace=trace)
        asn = Assertion(type="agent-invoked", value="IntentClassifier")

        result = EVALUATORS["agent-invoked"](None, asn, ctx)
        assert result is True

    def test_fails_when_agent_not_invoked(self):
        """Should fail when specified agent was not invoked."""
        from evals.framework.assertions.evaluators import EVALUATORS
        from evals.framework.assertions.types import Assertion, EvalContext

        trace = WorkflowTrace(agents=[AgentTrace(agent_name="OtherAgent", input={})])
        ctx = EvalContext(duration_seconds=1.0, trace=trace)
        asn = Assertion(type="agent-invoked", value="IntentClassifier")

        result = EVALUATORS["agent-invoked"](None, asn, ctx)
        assert result is False

    def test_fails_without_trace(self):
        """Should fail when no trace."""
        from evals.framework.assertions.evaluators import EVALUATORS
        from evals.framework.assertions.types import Assertion, EvalContext

        ctx = EvalContext(duration_seconds=1.0)
        asn = Assertion(type="agent-invoked", value="IntentClassifier")

        result = EVALUATORS["agent-invoked"](None, asn, ctx)
        assert result is False


class TestToolCallValidEvaluator:
    """Tests for tool-call-valid evaluator."""

    def test_passes_when_tool_called_successfully(self):
        """Should pass when tool was called without errors."""
        from evals.framework.assertions.evaluators import EVALUATORS
        from evals.framework.assertions.types import Assertion, EvalContext

        trace = WorkflowTrace(
            tool_calls=[
                ToolCall(
                    tool_name="sql_execution", args={"query": "SELECT 1"}, result="1"
                )
            ]
        )
        ctx = EvalContext(duration_seconds=1.0, trace=trace)
        asn = Assertion(type="tool-call-valid", tool="sql_execution")

        result = EVALUATORS["tool-call-valid"](None, asn, ctx)
        assert result is True

    def test_fails_when_tool_not_called(self):
        """Should fail when tool was not called."""
        from evals.framework.assertions.evaluators import EVALUATORS
        from evals.framework.assertions.types import Assertion, EvalContext

        trace = WorkflowTrace(
            tool_calls=[ToolCall(tool_name="other_tool", args={}, result="ok")]
        )
        ctx = EvalContext(duration_seconds=1.0, trace=trace)
        asn = Assertion(type="tool-call-valid", tool="sql_execution")

        result = EVALUATORS["tool-call-valid"](None, asn, ctx)
        assert result is False

    def test_fails_when_tool_had_error(self):
        """Should fail when tool had error."""
        from evals.framework.assertions.evaluators import EVALUATORS
        from evals.framework.assertions.types import Assertion, EvalContext

        trace = WorkflowTrace(
            tool_calls=[
                ToolCall(tool_name="sql_execution", args={}, error="syntax error")
            ]
        )
        ctx = EvalContext(duration_seconds=1.0, trace=trace)
        asn = Assertion(type="tool-call-valid", tool="sql_execution")

        result = EVALUATORS["tool-call-valid"](None, asn, ctx)
        assert result is False

    def test_fails_without_trace(self):
        """Should fail when no trace."""
        from evals.framework.assertions.evaluators import EVALUATORS
        from evals.framework.assertions.types import Assertion, EvalContext

        ctx = EvalContext(duration_seconds=1.0)
        asn = Assertion(type="tool-call-valid", tool="sql_execution")

        result = EVALUATORS["tool-call-valid"](None, asn, ctx)
        assert result is False

    def test_passes_with_multiple_successful_calls(self):
        """Should pass when all calls to tool succeeded."""
        from evals.framework.assertions.evaluators import EVALUATORS
        from evals.framework.assertions.types import Assertion, EvalContext

        trace = WorkflowTrace(
            tool_calls=[
                ToolCall(tool_name="sql_execution", args={}, result="ok"),
                ToolCall(tool_name="sql_execution", args={}, result="ok"),
            ]
        )
        ctx = EvalContext(duration_seconds=1.0, trace=trace)
        asn = Assertion(type="tool-call-valid", tool="sql_execution")

        result = EVALUATORS["tool-call-valid"](None, asn, ctx)
        assert result is True


# ─────────────────────────────────────────────────────────────────────────────
# Evaluator Registry Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestWorkflowEvaluatorRegistry:
    """Tests for workflow evaluator registration."""

    def test_workflow_evaluators_registered(self):
        """Should have workflow evaluators registered."""
        from evals.framework.assertions.evaluators import EVALUATORS

        expected = ["no-errors", "agent-invoked", "tool-call-valid"]
        for type_ in expected:
            assert type_ in EVALUATORS, f"Missing evaluator: {type_}"

    def test_total_evaluator_count(self):
        """Should have 25 total evaluators (22 original + 3 workflow)."""
        from evals.framework.assertions.evaluators import EVALUATORS

        assert len(EVALUATORS) == 25


# ─────────────────────────────────────────────────────────────────────────────
# OpenTelemetry Integration Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestOtelSetup:
    """Tests for OpenTelemetry setup functions."""

    def test_setup_otel_tracing(self):
        """Should set up OTel with in-memory exporter."""
        from evals.framework.workflow.otel import (
            get_exporter,
            setup_otel_tracing,
        )

        exporter = setup_otel_tracing()
        assert exporter is not None
        assert get_exporter() is exporter

    def test_clear_spans(self):
        """Should clear captured spans."""
        from evals.framework.workflow.otel import (
            clear_spans,
            get_finished_spans,
            setup_otel_tracing,
        )

        setup_otel_tracing()
        clear_spans()
        assert get_finished_spans() == []

    def test_get_finished_spans_empty(self):
        """Should return empty list when no spans captured."""
        from evals.framework.workflow.otel import (
            clear_spans,
            get_finished_spans,
            setup_otel_tracing,
        )

        setup_otel_tracing()
        clear_spans()
        spans = get_finished_spans()
        assert spans == []


class TestCaptureTrace:
    """Tests for capture_trace context manager."""

    def test_capture_trace_context_manager(self):
        """Should capture spans within context."""
        from evals.framework.workflow.otel import (
            capture_trace,
            get_exporter,
        )

        with capture_trace():
            pass  # No actual spans created in this test

        assert get_exporter() is not None


class TestSpansToWorkflowTrace:
    """Tests for spans_to_workflow_trace conversion."""

    def test_empty_spans(self):
        """Should return empty WorkflowTrace for empty spans."""
        from evals.framework.workflow.otel import spans_to_workflow_trace

        trace = spans_to_workflow_trace([])
        assert len(trace.agents) == 0
        assert len(trace.tool_calls) == 0
        assert not trace.has_errors()


class TestOtelExports:
    """Tests for OTel function exports."""

    def test_exports_from_workflow_module(self):
        """Should export OTel functions from workflow module."""
        from evals.framework.workflow import (
            capture_trace,
            clear_spans,
            get_exporter,
            get_finished_spans,
            setup_otel_tracing,
            spans_to_workflow_trace,
        )

        assert callable(setup_otel_tracing)
        assert callable(get_exporter)
        assert callable(clear_spans)
        assert callable(get_finished_spans)
        assert callable(capture_trace)
        assert callable(spans_to_workflow_trace)

    def test_exports_from_framework_module(self):
        """Should export OTel functions from main framework module."""
        from evals.framework import (
            capture_trace,
            clear_spans,
            get_exporter,
            get_finished_spans,
            setup_otel_tracing,
            spans_to_workflow_trace,
        )

        assert callable(setup_otel_tracing)
        assert callable(get_exporter)
        assert callable(clear_spans)
        assert callable(get_finished_spans)
        assert callable(capture_trace)
        assert callable(spans_to_workflow_trace)

    def test_agent_span_export(self):
        """Should export AgentSpan alias."""
        from evals.framework import AgentSpan, AgentTrace

        assert AgentSpan is AgentTrace
