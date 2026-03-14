"""Workflow-specific assertion evaluators.

Provides evaluators for workflow constraints:
- no-errors: Check that no agent or tool raised an exception
- agent-invoked: Check that a specific agent was called
- tool-call-valid: Check that tool calls for a specific tool succeeded
"""

from typing import Any

from evals.framework.assertions.evaluators import evaluator
from evals.framework.assertions.types import Assertion, EvalContext


@evaluator("no-errors")
def no_errors(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Pass if no agent or tool raised an exception."""
    if not hasattr(ctx, "trace") or ctx.trace is None:
        return True  # No trace means no workflow, pass by default
    return not ctx.trace.has_errors()


@evaluator("agent-invoked")
def agent_invoked(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Pass if specified agent was called at least once."""
    if not hasattr(ctx, "trace") or ctx.trace is None:
        return False
    return asn.value in ctx.trace.agents_invoked()


@evaluator("tool-call-valid")
def tool_call_valid(actual: Any, asn: Assertion, ctx: EvalContext) -> bool:
    """Pass if tool calls for specified tool meet nested assertions.

    Usage in YAML:
    - type: tool-call-valid
      tool: sql_execution
      assert:
        - { type: is-valid-sql, field: query }
    """
    if not hasattr(ctx, "trace") or ctx.trace is None:
        return False

    tool_calls = [tc for tc in ctx.trace.tool_calls if tc.tool_name == asn.tool]
    if not tool_calls:
        return False

    # For now, just check that tool was called successfully (no errors)
    # Full nested assertion support can be added later
    return all(tc.error is None for tc in tool_calls)
