"""Assertion types for the evaluation framework.

Defines the Assertion model and AssertionResult dataclass used throughout
the assertion-based evaluation system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from evals.framework.workflow.types import WorkflowTrace


class Assertion(BaseModel):
    """Configuration for a single assertion in a test case.

    Assertions define expectations about agent outputs. The type field
    determines which evaluator is used, and other fields provide the
    parameters for that evaluator.

    Examples:
        Presence check:
            Assertion(type="not-null", field="task")

        Exact match:
            Assertion(type="equals", field="status", value="active")

        Range check:
            Assertion(type="in-range", field="score", min=0, max=100)

        Performance budget:
            Assertion(type="latency-budget", max_seconds=2.5)
    """

    type: str
    """Assertion type: not-null, equals, contains, in-range, etc."""

    field: str | None = None
    """JSONPath to the field to check. E.g., "task", "assets[*].path", "user.profile.city"."""

    value: Any = None
    """Expected value for equality checks, substring for contains, or allowed set for one-of."""

    min: int | float | None = None
    """Minimum value for range checks (inclusive)."""

    max: int | float | None = None
    """Maximum value for range checks (inclusive)."""

    max_seconds: float | None = None
    """Maximum execution time for latency-budget assertion."""

    max_tokens: int | None = None
    """Maximum token count for token-budget assertion."""

    tool: str | None = None
    """Tool name for tool-call-valid assertion."""

    model_config = {"extra": "forbid"}


@dataclass
class AssertionResult:
    """Result of evaluating a single assertion.

    Captures whether the assertion passed, the actual value found,
    and an optional message explaining the result.
    """

    assertion: Assertion
    """The assertion that was evaluated."""

    passed: bool
    """Whether the assertion passed."""

    actual_value: Any = None
    """The actual value found in the output."""

    message: str | None = None
    """Optional message explaining the result, especially for failures."""

    def __str__(self) -> str:
        """Format result for display."""
        status = "PASS" if self.passed else "FAIL"
        field_str = f" [{self.assertion.field}]" if self.assertion.field else ""
        msg = f" - {self.message}" if self.message else ""
        return f"{status}: {self.assertion.type}{field_str}{msg}"


@dataclass
class EvalContext:
    """Context passed to evaluators with execution metadata.

    Contains performance metrics from the agent execution that are
    needed for performance assertions (latency-budget, token-budget).
    """

    duration_seconds: float = 0.0
    """Execution time in seconds."""

    total_tokens: int = 0
    """Total tokens used (input + output)."""

    input_tokens: int = 0
    """Input/prompt tokens used."""

    output_tokens: int = 0
    """Output/completion tokens used."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata from the execution."""

    trace: WorkflowTrace | None = None
    """Workflow trace for workflow-level assertions."""
