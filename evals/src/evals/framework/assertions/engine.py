"""Assertion evaluation engine.

The AssertionEngine is responsible for:
1. Extracting field values from output using JSONPath
2. Running the appropriate evaluator for each assertion
3. Returning structured AssertionResult objects
"""

from typing import Any

from jsonpath_ng import parse as jsonpath_parse
from jsonpath_ng.exceptions import JsonPathParserError

from evals.framework.assertions.evaluators import EVALUATORS
from evals.framework.assertions.types import Assertion, AssertionResult, EvalContext


class AssertionEngine:
    """Engine for evaluating assertions against agent outputs.

    Uses jsonpath-ng for flexible field extraction and a registry of
    evaluator functions for different assertion types.

    Example:
        engine = AssertionEngine()
        output = {"task": "consult", "assets": [{"path": "a"}, {"path": "b"}]}
        assertions = [
            Assertion(type="equals", field="task", value="consult"),
            Assertion(type="any-contains", field="assets[*].path", value="a"),
        ]
        ctx = EvalContext(duration_seconds=1.5)
        results = engine.evaluate_all(output, assertions, ctx)
    """

    def __init__(self):
        """Initialize the assertion engine."""
        # Cache compiled JSONPath expressions
        self._jsonpath_cache: dict[str, Any] = {}

    def evaluate(
        self,
        output: Any,
        assertion: Assertion,
        context: EvalContext,
    ) -> AssertionResult:
        """Evaluate a single assertion against the output.

        Args:
            output: The agent output (dict, Pydantic model, or None)
            assertion: The assertion to evaluate
            context: Evaluation context with performance metrics

        Returns:
            AssertionResult with passed status and details

        Raises:
            ValueError: If assertion type is unknown
        """
        # Get the evaluator for this assertion type
        evaluator = EVALUATORS.get(assertion.type)
        if evaluator is None:
            raise ValueError(f"Unknown assertion type: {assertion.type}")

        # Extract the field value (or use special handling for performance assertions)
        if assertion.type in ("latency-budget", "token-budget"):
            # Performance assertions don't need field extraction
            actual_value = self._get_performance_value(assertion, context)
        elif assertion.field:
            actual_value = self.extract_field(output, assertion.field)
        else:
            # No field specified, use entire output
            actual_value = self._normalize_output(output)

        # Run the evaluator
        passed = evaluator(actual_value, assertion, context)

        # Create result with appropriate message
        message = self._create_message(assertion, actual_value, passed)

        return AssertionResult(
            assertion=assertion,
            passed=passed,
            actual_value=actual_value,
            message=message,
        )

    def evaluate_all(
        self,
        output: Any,
        assertions: list[Assertion],
        context: EvalContext,
    ) -> list[AssertionResult]:
        """Evaluate multiple assertions against the output.

        Args:
            output: The agent output
            assertions: List of assertions to evaluate
            context: Evaluation context with performance metrics

        Returns:
            List of AssertionResult objects
        """
        return [self.evaluate(output, asn, context) for asn in assertions]

    def extract_field(self, output: Any, field: str) -> Any:
        """Extract a field value from output using JSONPath.

        Args:
            output: The output to extract from (dict or Pydantic model)
            field: JSONPath expression (e.g., "name", "user.profile.city", "items[*].id")

        Returns:
            The extracted value, list of values for wildcards, or None if not found
        """
        if output is None:
            return None

        # Normalize output to dict
        data = self._normalize_output(output)
        if data is None:
            return None

        # Get or compile the JSONPath expression
        expr = self._get_jsonpath(field)
        if expr is None:
            return None

        # Find all matches
        matches = expr.find(data)
        if not matches:
            return None

        # Return single value or list depending on path
        if len(matches) == 1 and "[*]" not in field:
            return matches[0].value
        return [m.value for m in matches]

    def _normalize_output(self, output: Any) -> dict | None:
        """Convert output to dict for JSONPath processing."""
        if output is None:
            return None
        if hasattr(output, "model_dump"):
            return output.model_dump()
        if isinstance(output, dict):
            return output
        return None

    def _get_jsonpath(self, field: str) -> Any | None:
        """Get compiled JSONPath expression, using cache."""
        if field in self._jsonpath_cache:
            return self._jsonpath_cache[field]

        try:
            # Convert simple dot notation to JSONPath if needed
            jsonpath_str = self._to_jsonpath(field)
            expr = jsonpath_parse(jsonpath_str)
            self._jsonpath_cache[field] = expr
            return expr
        except JsonPathParserError:
            return None

    def _to_jsonpath(self, field: str) -> str:
        """Convert field path to JSONPath expression.

        Handles simple dot notation (user.name) and array access (items[0], items[*]).
        """
        # Already a valid JSONPath with $ prefix
        if field.startswith("$"):
            return field

        # Split on dots but preserve array notation
        parts = []
        current = ""
        i = 0
        while i < len(field):
            char = field[i]
            if char == ".":
                if current:
                    parts.append(current)
                    current = ""
            elif char == "[":
                if current:
                    parts.append(current)
                    current = ""
                # Find matching ]
                bracket_end = field.find("]", i)
                if bracket_end == -1:
                    current = field[i:]
                    break
                parts.append(field[i : bracket_end + 1])
                i = bracket_end
            else:
                current += char
            i += 1

        if current:
            parts.append(current)

        # Build JSONPath
        if not parts:
            return "$"

        result = "$"
        for part in parts:
            if part.startswith("["):
                result += part
            else:
                result += f".{part}"

        return result

    def _get_performance_value(self, assertion: Assertion, context: EvalContext) -> Any:
        """Get the actual value for performance assertions."""
        if assertion.type == "latency-budget":
            return context.duration_seconds
        if assertion.type == "token-budget":
            return context.total_tokens
        return None

    def _create_message(
        self, assertion: Assertion, actual_value: Any, passed: bool
    ) -> str | None:
        """Create a descriptive message for the assertion result."""
        if passed:
            return None

        # Create failure message based on assertion type
        if assertion.type == "not-null":
            return f"Expected non-null value, got {actual_value}"
        if assertion.type == "is-null":
            return f"Expected null, got {actual_value}"
        if assertion.type == "equals":
            return f"Expected {assertion.value!r}, got {actual_value!r}"
        if assertion.type == "not-equals":
            return f"Expected value to differ from {assertion.value!r}"
        if assertion.type == "one-of":
            return f"Expected one of {assertion.value}, got {actual_value!r}"
        if assertion.type == "contains":
            return f"Expected string to contain {assertion.value!r}"
        if assertion.type == "not-contains":
            return f"Expected string to not contain {assertion.value!r}"
        if assertion.type == "regex":
            return f"Value {actual_value!r} did not match pattern {assertion.value!r}"
        if assertion.type == "any-contains":
            return f"No element contains {assertion.value!r}"
        if assertion.type == "all-contain":
            return f"Not all elements contain {assertion.value!r}"
        if assertion.type == "count-range":
            count = len(actual_value) if isinstance(actual_value, list) else 0
            return (
                f"Array count {count} not in range [{assertion.min}, {assertion.max}]"
            )
        if assertion.type == "includes":
            return f"Array does not include {assertion.value!r}"
        if assertion.type == "in-range":
            return (
                f"Value {actual_value} not in range [{assertion.min}, {assertion.max}]"
            )
        if assertion.type == "latency-budget":
            return f"Latency {actual_value:.2f}s exceeds budget of {assertion.max_seconds}s"
        if assertion.type == "token-budget":
            return (
                f"Token count {actual_value} exceeds budget of {assertion.max_tokens}"
            )

        return None
