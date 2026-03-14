"""Built-in evaluation metrics for the framework.

These metrics wrap pydantic-evals evaluators and provide measurement
capabilities using sklearn for proper statistical computations.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from pydantic_evals.evaluators import Evaluator, EvaluatorContext
from pydantic_evals.evaluators.evaluator import EvaluationReason
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score


@dataclass
class MetricResult:
    """Result from a metric evaluation."""

    name: str
    score: float  # 0.0 to 1.0
    details: dict[str, Any] | None = None


def _get_value(obj: Any, field: str) -> Any:
    """Extract a field value from an object, supporting various types."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump().get(field)
    if isinstance(obj, dict):
        return obj.get(field)
    return getattr(obj, field, None)


def _normalize_for_comparison(value: Any) -> Any:
    """Normalize a value for comparison, converting Pydantic models to dicts."""
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {k: _normalize_for_comparison(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_for_comparison(v) for v in value]
    return value


class ExactMatchEvaluator(Evaluator[Any, Any]):
    """Evaluates if output exactly matches expected output.

    Handles:
    - Pydantic models (converts to dict via model_dump())
    - Dicts (recursive normalization)
    - Primitives (direct comparison)
    - None values (None expected = pass, None output = fail)
    """

    def evaluate(self, ctx: EvaluatorContext[Any, Any]) -> float:
        if ctx.expected_output is None:
            return 1.0  # No expected output, consider it passing

        if ctx.output is None:
            return 0.0

        expected = _normalize_for_comparison(ctx.expected_output)
        actual = _normalize_for_comparison(ctx.output)

        return 1.0 if expected == actual else 0.0


class FieldMatchEvaluator(Evaluator[Any, Any]):
    """Evaluates exact match on specific fields.

    Returns fraction of fields matching (0.0 to 1.0) and reports
    individual field results as named scores.
    """

    def __init__(self, fields: list[str]):
        self.fields = fields

    def evaluate(self, ctx: EvaluatorContext[Any, Any]) -> dict[str, float]:
        """Returns dict with overall score and per-field match scores."""
        if not self.fields:
            return {"field_match": 1.0}

        if ctx.expected_output is None:
            return {"field_match": 1.0}

        if ctx.output is None:
            result = {"field_match": 0.0}
            for field in self.fields:
                result[f"{field}_match"] = 0.0
            return result

        matches = 0
        result: dict[str, float] = {}

        for field in self.fields:
            expected_val = _normalize_for_comparison(
                _get_value(ctx.expected_output, field)
            )
            actual_val = _normalize_for_comparison(_get_value(ctx.output, field))
            is_match = expected_val == actual_val
            result[f"{field}_match"] = 1.0 if is_match else 0.0
            if is_match:
                matches += 1

        result["field_match"] = matches / len(self.fields)
        return result


class FieldClassificationEvaluator(Evaluator[Any, Any]):
    """Records expected/predicted labels for classification metrics.

    Per-case: Records expected_{field} and predicted_{field} as labels,
    along with per-field accuracy (match rate).
    Aggregate: compute_aggregate_metrics() computes F1, precision, recall, accuracy.

    This evaluator is the foundation for classification metrics - it records
    the raw labels that sklearn metrics need for aggregate computation.
    """

    def __init__(self, fields: list[str]):
        self.fields = fields

    def evaluate(self, ctx: EvaluatorContext[Any, Any]) -> dict[str, float | str]:
        """Returns per-field accuracy and stores labels for F1 aggregation."""
        if not self.fields:
            return {"field_accuracy": 1.0}

        if ctx.expected_output is None:
            return {"field_accuracy": 1.0}

        if ctx.output is None:
            result: dict[str, float | str] = {"field_accuracy": 0.0}
            for field in self.fields:
                result[f"{field}_accuracy"] = 0.0
            return result

        matches = 0
        result: dict[str, float | str] = {}

        for field in self.fields:
            expected_val = _get_value(ctx.expected_output, field)
            actual_val = _get_value(ctx.output, field)

            # Normalize for comparison
            expected_norm = _normalize_for_comparison(expected_val)
            actual_norm = _normalize_for_comparison(actual_val)

            is_match = expected_norm == actual_norm
            result[f"{field}_accuracy"] = 1.0 if is_match else 0.0

            # Store labels for F1 aggregation (as strings for categorical)
            result[f"expected_{field}"] = (
                str(expected_val) if expected_val is not None else "__none__"
            )
            result[f"predicted_{field}"] = (
                str(actual_val) if actual_val is not None else "__none__"
            )

            if is_match:
                matches += 1

        result["field_accuracy"] = matches / len(self.fields)
        return result


# Backward compatibility alias
FieldF1Evaluator = FieldClassificationEvaluator


class FieldAccuracyEvaluator(Evaluator[Any, Any]):
    """Evaluates per-field accuracy using sklearn's accuracy_score concept.

    Similar to FieldMatchEvaluator but named for clarity when computing
    accuracy metrics. Reports individual field accuracies (0 or 1 per case).
    """

    def __init__(self, fields: list[str]):
        self.fields = fields

    def evaluate(self, ctx: EvaluatorContext[Any, Any]) -> dict[str, float]:
        """Returns per-field accuracy scores (0.0 or 1.0 per field)."""
        if not self.fields:
            return {"accuracy": 1.0}

        if ctx.expected_output is None:
            return {"accuracy": 1.0}

        if ctx.output is None:
            result = {"accuracy": 0.0}
            for field in self.fields:
                result[f"{field}_accuracy"] = 0.0
            return result

        correct = 0
        result: dict[str, float] = {}

        for field in self.fields:
            expected_val = _normalize_for_comparison(
                _get_value(ctx.expected_output, field)
            )
            actual_val = _normalize_for_comparison(_get_value(ctx.output, field))
            is_correct = expected_val == actual_val
            result[f"{field}_accuracy"] = 1.0 if is_correct else 0.0
            if is_correct:
                correct += 1

        result["accuracy"] = correct / len(self.fields)
        return result


class LatencyEvaluator(Evaluator[Any, Any]):
    """Records latency (execution time) from the evaluation context.

    Returns the duration in seconds as recorded by pydantic-evals.
    """

    def __init__(self, threshold_seconds: float | None = None):
        """Initialize with optional threshold for pass/fail.

        Args:
            threshold_seconds: If provided, also returns a boolean indicating
                whether latency is under threshold.
        """
        self.threshold_seconds = threshold_seconds

    def evaluate(
        self, ctx: EvaluatorContext[Any, Any]
    ) -> float | dict[str, float | EvaluationReason]:
        """Returns latency in seconds, optionally with threshold check."""
        duration = ctx.duration

        if self.threshold_seconds is not None:
            is_under = duration <= self.threshold_seconds
            return {
                "latency_seconds": duration,
                "latency_ok": EvaluationReason(
                    value=1.0 if is_under else 0.0,
                    reason=f"{'Under' if is_under else 'Over'} threshold of {self.threshold_seconds}s",
                ),
            }

        return duration


class TokenCountEvaluator(Evaluator[Any, Any]):
    """Records token count from the evaluation context metrics.

    Expects token counts to be available in ctx.metrics (e.g., from LLM calls).
    """

    def __init__(self, max_tokens: int | None = None):
        """Initialize with optional max token threshold.

        Args:
            max_tokens: If provided, also returns whether count is under limit.
        """
        self.max_tokens = max_tokens

    def evaluate(
        self, ctx: EvaluatorContext[Any, Any]
    ) -> dict[str, float | EvaluationReason]:
        """Returns token counts from metrics if available."""
        result: dict[str, float | EvaluationReason] = {}

        # Check for common token count metric names
        input_tokens = ctx.metrics.get(
            "input_tokens", ctx.metrics.get("prompt_tokens", 0)
        )
        output_tokens = ctx.metrics.get(
            "output_tokens", ctx.metrics.get("completion_tokens", 0)
        )
        total_tokens = ctx.metrics.get("total_tokens", input_tokens + output_tokens)

        result["input_tokens"] = float(input_tokens)
        result["output_tokens"] = float(output_tokens)
        result["total_tokens"] = float(total_tokens)

        if self.max_tokens is not None and total_tokens > 0:
            is_under = total_tokens <= self.max_tokens
            result["tokens_ok"] = EvaluationReason(
                value=1.0 if is_under else 0.0,
                reason=f"{total_tokens} tokens {'under' if is_under else 'over'} limit of {self.max_tokens}",
            )

        return result


# Factory functions for cleaner API
def exact_match() -> ExactMatchEvaluator:
    """Create an exact match evaluator."""
    return ExactMatchEvaluator()


def field_match(fields: list[str]) -> FieldMatchEvaluator:
    """Create a field match evaluator for specific fields."""
    return FieldMatchEvaluator(fields=fields)


def classification(fields: list[str]) -> FieldClassificationEvaluator:
    """Create a classification evaluator for specific fields.

    Per-case: Records expected/predicted labels.
    Aggregate: Computes F1, precision, recall, accuracy via sklearn.

    Args:
        fields: List of field names to evaluate as classification labels.

    Returns:
        FieldClassificationEvaluator configured for the specified fields.
    """
    return FieldClassificationEvaluator(fields=fields)


def field_f1(fields: list[str]) -> FieldClassificationEvaluator:
    """Alias for classification(). Kept for backward compatibility."""
    return classification(fields)


def field_accuracy(fields: list[str]) -> FieldAccuracyEvaluator:
    """Create a field accuracy evaluator for specific fields."""
    return FieldAccuracyEvaluator(fields=fields)


def latency(threshold_seconds: float | None = None) -> LatencyEvaluator:
    """Create a latency evaluator.

    Args:
        threshold_seconds: Optional threshold for pass/fail check.
    """
    return LatencyEvaluator(threshold_seconds=threshold_seconds)


def token_count(max_tokens: int | None = None) -> TokenCountEvaluator:
    """Create a token count evaluator.

    Args:
        max_tokens: Optional max token limit for pass/fail check.
    """
    return TokenCountEvaluator(max_tokens=max_tokens)


def compute_aggregate_metrics(report) -> dict[str, float]:
    """Compute aggregate metrics from an EvaluationReport.

    Returns a summary dict with:
    - success_rate: Fraction of cases without failures
    - Per-field accuracy averages (from *_match and *_accuracy scores)
    - Per-field F1 scores (computed from expected_*/predicted_* labels)
    - Average latency (if latency_seconds in scores)

    Uses sklearn for proper F1 computation across all cases.
    """
    total = len(report.cases)
    if total == 0:
        return {"success_rate": 0.0}

    # Count successes (cases without failures)
    failed_names = {f.name for f in report.failures}
    successes = sum(1 for c in report.cases if c.name not in failed_names)

    summary: dict[str, float] = {"success_rate": successes / total}

    # Collect per-field scores for averaging
    field_scores: dict[str, list[float]] = defaultdict(list)

    # Collect expected/predicted pairs for F1 computation
    field_labels: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: {"expected": [], "predicted": []}
    )

    # Latency collection
    latencies: list[float] = []

    for case_result in report.cases:
        # Process scores (numeric values)
        if case_result.scores:
            for score_name, eval_result in case_result.scores.items():
                # Get the actual value from EvaluationResult
                value = (
                    eval_result.value if hasattr(eval_result, "value") else eval_result
                )
                if isinstance(value, (int, float)):
                    if score_name.endswith("_match") or score_name.endswith(
                        "_accuracy"
                    ):
                        field_scores[score_name].append(float(value))
                    elif score_name == "latency_seconds":
                        latencies.append(float(value))
                    elif score_name in ("field_match", "field_accuracy", "accuracy"):
                        field_scores[score_name].append(float(value))

        # Process labels (string values for F1 computation)
        if case_result.labels:
            for label_name, eval_result in case_result.labels.items():
                label_value = (
                    eval_result.value if hasattr(eval_result, "value") else eval_result
                )
                if isinstance(label_value, str):
                    if label_name.startswith("expected_"):
                        field = label_name[9:]  # Remove "expected_" prefix
                        field_labels[field]["expected"].append(label_value)
                    elif label_name.startswith("predicted_"):
                        field = label_name[10:]  # Remove "predicted_" prefix
                        field_labels[field]["predicted"].append(label_value)

    # Compute average scores
    for score_name, scores in field_scores.items():
        if scores:
            summary[score_name] = sum(scores) / len(scores)

    # Compute classification metrics per field using sklearn
    for field, labels in field_labels.items():
        expected = labels["expected"]
        predicted = labels["predicted"]
        if expected and predicted and len(expected) == len(predicted):
            # Get unique labels for multi-class handling
            unique_labels = list(set(expected) | set(predicted))

            # Always compute accuracy
            acc = accuracy_score(expected, predicted)
            summary[f"{field}_accuracy"] = float(acc)

            if len(unique_labels) > 1:
                # Multi-class: use weighted average to account for class imbalance
                try:
                    f1 = f1_score(
                        expected,
                        predicted,
                        labels=unique_labels,
                        average="weighted",
                        zero_division=0.0,
                    )
                    precision = precision_score(
                        expected,
                        predicted,
                        labels=unique_labels,
                        average="weighted",
                        zero_division=0.0,
                    )
                    recall = recall_score(
                        expected,
                        predicted,
                        labels=unique_labels,
                        average="weighted",
                        zero_division=0.0,
                    )
                    summary[f"{field}_f1"] = float(f1)
                    summary[f"{field}_precision"] = float(precision)
                    summary[f"{field}_recall"] = float(recall)
                except ValueError:
                    # Fallback: metrics already have accuracy above
                    pass
            # Single class case: accuracy is sufficient (F1/precision/recall undefined)

    # Add average latency if available
    if latencies:
        summary["avg_latency_seconds"] = sum(latencies) / len(latencies)
        summary["max_latency_seconds"] = max(latencies)
        summary["min_latency_seconds"] = min(latencies)

    return summary
