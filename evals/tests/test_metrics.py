"""Tests for evaluation metrics and evaluators."""

from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from evals.framework.metrics import (
    ExactMatchEvaluator,
    FieldClassificationEvaluator,
    FieldMatchEvaluator,
    classification,
    compute_aggregate_metrics,
    exact_match,
    field_f1,
    field_match,
)

# ─────────────────────────────────────────────────────────────────────────────
# Test Fixtures
# ─────────────────────────────────────────────────────────────────────────────


class MockOutput(BaseModel):
    """Mock output model for testing evaluators."""

    task: str
    mode: str
    job: str = "default"


def make_mock_context(output, expected_output):
    """Create a mock EvaluatorContext for testing evaluators."""
    ctx = MagicMock()
    ctx.output = output
    ctx.expected_output = expected_output
    ctx.labels = {}

    def record_label(name, value):
        ctx.labels[name] = value

    ctx.record_label = record_label
    return ctx


def make_mock_case(name: str, scores: dict | None = None, labels: dict | None = None):
    """Create a mock case for aggregate metrics testing."""
    case = MagicMock()
    case.name = name
    case.scores = scores
    case.labels = labels or {}
    return case


# ─────────────────────────────────────────────────────────────────────────────
# Factory Function Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestMetricFactories:
    """Tests for metric factory functions."""

    def test_exact_match_creates_evaluator(self):
        """exact_match() should create ExactMatchEvaluator."""
        evaluator = exact_match()
        assert isinstance(evaluator, ExactMatchEvaluator)

    def test_field_match_creates_evaluator(self):
        """field_match() should create FieldMatchEvaluator with fields."""
        evaluator = field_match(fields=["task", "mode"])
        assert isinstance(evaluator, FieldMatchEvaluator)
        assert evaluator.fields == ["task", "mode"]

    def test_field_f1_creates_classification_evaluator(self):
        """field_f1() should create FieldClassificationEvaluator (backward compat)."""
        evaluator = field_f1(fields=["task", "mode", "job"])
        assert isinstance(evaluator, FieldClassificationEvaluator)
        assert evaluator.fields == ["task", "mode", "job"]

    def test_classification_creates_evaluator(self):
        """classification() should create FieldClassificationEvaluator."""
        evaluator = classification(fields=["task", "mode", "job"])
        assert isinstance(evaluator, FieldClassificationEvaluator)
        assert evaluator.fields == ["task", "mode", "job"]


# ─────────────────────────────────────────────────────────────────────────────
# ExactMatchEvaluator Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestExactMatchEvaluator:
    """Tests for ExactMatchEvaluator.evaluate()."""

    def test_identical_dicts_return_1(self):
        """Identical outputs should return 1.0."""
        evaluator = ExactMatchEvaluator()
        output = {"task": "consult", "mode": "chat"}
        expected = {"task": "consult", "mode": "chat"}
        ctx = make_mock_context(output, expected)

        assert evaluator.evaluate(ctx) == 1.0

    def test_different_dicts_return_0(self):
        """Different outputs should return 0.0."""
        evaluator = ExactMatchEvaluator()
        output = {"task": "consult", "mode": "chat"}
        expected = {"task": "reflect", "mode": "chat"}
        ctx = make_mock_context(output, expected)

        assert evaluator.evaluate(ctx) == 0.0

    def test_pydantic_models_compared_by_value(self):
        """Pydantic models should be compared by model_dump()."""
        evaluator = ExactMatchEvaluator()
        output = MockOutput(task="consult", mode="chat")
        expected = MockOutput(task="consult", mode="chat")
        ctx = make_mock_context(output, expected)

        assert evaluator.evaluate(ctx) == 1.0

    def test_different_pydantic_models_return_0(self):
        """Different Pydantic models should return 0.0."""
        evaluator = ExactMatchEvaluator()
        output = MockOutput(task="consult", mode="chat")
        expected = MockOutput(task="reflect", mode="chat")
        ctx = make_mock_context(output, expected)

        assert evaluator.evaluate(ctx) == 0.0

    @pytest.mark.parametrize(
        "output,expected,score",
        [
            ({"task": "x"}, None, 1.0),  # No expected = pass
            (None, {"task": "x"}, 0.0),  # No output = fail
            (None, None, 1.0),  # Both None = pass
        ],
    )
    def test_none_handling(self, output, expected, score):
        """Should handle None values correctly."""
        evaluator = ExactMatchEvaluator()
        ctx = make_mock_context(output, expected)
        assert evaluator.evaluate(ctx) == score


# ─────────────────────────────────────────────────────────────────────────────
# FieldMatchEvaluator Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFieldMatchEvaluator:
    """Tests for FieldMatchEvaluator.evaluate()."""

    def test_all_fields_match_returns_1(self):
        """All fields matching should return field_match=1.0."""
        evaluator = FieldMatchEvaluator(fields=["task", "mode", "job"])
        output = MockOutput(task="consult", mode="chat", job="analyst")
        expected = MockOutput(task="consult", mode="chat", job="analyst")
        ctx = make_mock_context(output, expected)

        result = evaluator.evaluate(ctx)
        assert result["field_match"] == 1.0

    def test_no_fields_match_returns_0(self):
        """No fields matching should return field_match=0.0."""
        evaluator = FieldMatchEvaluator(fields=["task", "mode", "job"])
        output = MockOutput(task="reflect", mode="auto", job="researcher")
        expected = MockOutput(task="consult", mode="chat", job="analyst")
        ctx = make_mock_context(output, expected)

        result = evaluator.evaluate(ctx)
        assert result["field_match"] == 0.0

    @pytest.mark.parametrize(
        "output_values,expected_values,expected_score",
        [
            (("consult", "chat", "researcher"), ("consult", "chat", "analyst"), 2 / 3),
            (("consult", "auto", "analyst"), ("consult", "chat", "analyst"), 2 / 3),
            (("reflect", "auto", "analyst"), ("consult", "chat", "analyst"), 1 / 3),
        ],
    )
    def test_partial_match_scores(self, output_values, expected_values, expected_score):
        """Partial field match should return proportional score."""
        evaluator = FieldMatchEvaluator(fields=["task", "mode", "job"])
        output = MockOutput(
            task=output_values[0], mode=output_values[1], job=output_values[2]
        )
        expected = MockOutput(
            task=expected_values[0], mode=expected_values[1], job=expected_values[2]
        )
        ctx = make_mock_context(output, expected)

        result = evaluator.evaluate(ctx)
        assert result["field_match"] == pytest.approx(expected_score)

    def test_none_output_returns_0(self):
        """None output should return field_match=0.0."""
        evaluator = FieldMatchEvaluator(fields=["task"])
        expected = MockOutput(task="consult", mode="chat")
        ctx = make_mock_context(None, expected)

        result = evaluator.evaluate(ctx)
        assert result["field_match"] == 0.0

    def test_none_expected_returns_1(self):
        """None expected should return field_match=1.0."""
        evaluator = FieldMatchEvaluator(fields=["task"])
        output = MockOutput(task="consult", mode="chat")
        ctx = make_mock_context(output, None)

        result = evaluator.evaluate(ctx)
        assert result["field_match"] == 1.0

    def test_empty_fields_returns_1(self):
        """Empty fields list should return field_match=1.0."""
        evaluator = FieldMatchEvaluator(fields=[])
        output = MockOutput(task="consult", mode="chat")
        expected = MockOutput(task="reflect", mode="auto")
        ctx = make_mock_context(output, expected)

        result = evaluator.evaluate(ctx)
        assert result["field_match"] == 1.0


# ─────────────────────────────────────────────────────────────────────────────
# FieldClassificationEvaluator Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFieldClassificationEvaluator:
    """Tests for FieldClassificationEvaluator.evaluate()."""

    def test_all_correct_returns_1(self):
        """All fields correct should return field_accuracy=1.0."""
        evaluator = FieldClassificationEvaluator(fields=["task", "mode", "job"])
        output = MockOutput(task="consult", mode="chat", job="analyst")
        expected = MockOutput(task="consult", mode="chat", job="analyst")
        ctx = make_mock_context(output, expected)

        result = evaluator.evaluate(ctx)
        assert result["field_accuracy"] == 1.0

    def test_all_wrong_returns_0(self):
        """All fields wrong should return field_accuracy=0.0."""
        evaluator = FieldClassificationEvaluator(fields=["task", "mode", "job"])
        output = MockOutput(task="reflect", mode="auto", job="researcher")
        expected = MockOutput(task="consult", mode="chat", job="analyst")
        ctx = make_mock_context(output, expected)

        result = evaluator.evaluate(ctx)
        assert result["field_accuracy"] == 0.0

    def test_partial_returns_proportional_score(self):
        """Partial match should return proportional field_accuracy."""
        evaluator = FieldClassificationEvaluator(fields=["task", "mode", "job"])
        output = MockOutput(task="consult", mode="auto", job="analyst")
        expected = MockOutput(task="consult", mode="chat", job="analyst")
        ctx = make_mock_context(output, expected)

        result = evaluator.evaluate(ctx)
        assert result["field_accuracy"] == pytest.approx(2 / 3)

    def test_records_expected_predicted_labels(self):
        """Should record expected/predicted labels for F1 aggregation."""
        evaluator = FieldClassificationEvaluator(fields=["task", "mode", "job"])
        output = MockOutput(task="consult", mode="auto", job="analyst")
        expected = MockOutput(task="consult", mode="chat", job="analyst")
        ctx = make_mock_context(output, expected)

        result = evaluator.evaluate(ctx)

        assert result["expected_task"] == "consult"
        assert result["predicted_task"] == "consult"
        assert result["expected_mode"] == "chat"
        assert result["predicted_mode"] == "auto"
        assert result["expected_job"] == "analyst"
        assert result["predicted_job"] == "analyst"

    def test_none_output_returns_0(self):
        """None output should return field_accuracy=0.0."""
        evaluator = FieldClassificationEvaluator(fields=["task"])
        expected = MockOutput(task="consult", mode="chat")
        ctx = make_mock_context(None, expected)

        result = evaluator.evaluate(ctx)
        assert result["field_accuracy"] == 0.0

    def test_none_expected_returns_1(self):
        """None expected should return field_accuracy=1.0."""
        evaluator = FieldClassificationEvaluator(fields=["task"])
        output = MockOutput(task="consult", mode="chat")
        ctx = make_mock_context(output, None)

        result = evaluator.evaluate(ctx)
        assert result["field_accuracy"] == 1.0

    def test_empty_fields_returns_1(self):
        """Empty fields list should return field_accuracy=1.0."""
        evaluator = FieldClassificationEvaluator(fields=[])
        output = MockOutput(task="consult", mode="chat")
        expected = MockOutput(task="reflect", mode="auto")
        ctx = make_mock_context(output, expected)

        result = evaluator.evaluate(ctx)
        assert result["field_accuracy"] == 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Aggregate Metrics Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestComputeAggregateMetrics:
    """Tests for compute_aggregate_metrics()."""

    def test_success_rate_calculation(self):
        """Should compute correct success rate."""
        report = MagicMock()
        report.cases = [make_mock_case(f"case_{i}") for i in range(5)]
        # Create failure mock with .name attribute properly set
        failure = MagicMock()
        failure.name = "case_3"
        report.failures = [failure]

        result = compute_aggregate_metrics(report)
        assert result["success_rate"] == pytest.approx(0.8)  # 4/5

    def test_field_score_aggregation(self):
        """Should aggregate per-field scores from scores dict."""
        report = MagicMock()
        report.cases = [
            make_mock_case(
                "case_1",
                scores={
                    "task_match": MagicMock(value=1.0),
                    "mode_match": MagicMock(value=1.0),
                },
            ),
            make_mock_case(
                "case_2",
                scores={
                    "task_match": MagicMock(value=1.0),
                    "mode_match": MagicMock(value=0.0),
                },
            ),
            make_mock_case(
                "case_3",
                scores={
                    "task_match": MagicMock(value=0.0),
                    "mode_match": MagicMock(value=0.0),
                },
            ),
        ]
        report.failures = []

        result = compute_aggregate_metrics(report)
        assert result["task_match"] == pytest.approx(2 / 3)
        assert result["mode_match"] == pytest.approx(1 / 3)

    def test_empty_report_returns_zero_success_rate(self):
        """Empty report should return 0.0 success rate."""
        report = MagicMock()
        report.cases = []
        report.failures = []

        result = compute_aggregate_metrics(report)
        assert result["success_rate"] == 0.0

    def test_ignores_non_match_scores(self):
        """Should only aggregate scores ending with _match or _accuracy."""
        report = MagicMock()
        report.cases = [
            make_mock_case(
                "case_1",
                scores={
                    "task_match": MagicMock(value=1.0),
                    "some_other_score": MagicMock(value=0.5),
                },
                labels={"some_label": MagicMock(value="value")},
            )
        ]
        report.failures = []

        result = compute_aggregate_metrics(report)
        assert "task_match" in result
        assert "some_other_score" not in result
        assert "some_label" not in result


class TestClassificationAggregation:
    """Tests for classification metrics (precision, recall, F1) aggregation."""

    def test_computes_f1_from_labels(self):
        """Should compute F1 score from expected/predicted labels."""
        report = MagicMock()
        report.cases = [
            make_mock_case(
                "case_1",
                labels={
                    "expected_task": MagicMock(value="consult"),
                    "predicted_task": MagicMock(value="consult"),
                },
            ),
            make_mock_case(
                "case_2",
                labels={
                    "expected_task": MagicMock(value="reflect"),
                    "predicted_task": MagicMock(value="reflect"),
                },
            ),
            make_mock_case(
                "case_3",
                labels={
                    "expected_task": MagicMock(value="consult"),
                    "predicted_task": MagicMock(value="reflect"),
                },
            ),
        ]
        report.failures = []

        result = compute_aggregate_metrics(report)

        assert "task_f1" in result
        assert "task_precision" in result
        assert "task_recall" in result
        assert "task_accuracy" in result
        assert result["task_accuracy"] == pytest.approx(2 / 3)

    def test_metrics_in_valid_range(self):
        """All classification metrics should be in [0, 1]."""
        report = MagicMock()
        predictions = [("A", "A"), ("A", "A"), ("B", "A"), ("A", "B")]
        report.cases = [
            make_mock_case(
                f"case_{i}",
                labels={
                    "expected_task": MagicMock(value=expected),
                    "predicted_task": MagicMock(value=predicted),
                },
            )
            for i, (expected, predicted) in enumerate(predictions)
        ]
        report.failures = []

        result = compute_aggregate_metrics(report)

        assert 0.0 <= result["task_precision"] <= 1.0
        assert 0.0 <= result["task_recall"] <= 1.0
        assert 0.0 <= result["task_f1"] <= 1.0

    def test_multiple_fields(self):
        """Should compute metrics for multiple classification fields."""
        report = MagicMock()
        report.cases = [
            make_mock_case(
                "case_1",
                labels={
                    "expected_task": MagicMock(value="consult"),
                    "predicted_task": MagicMock(value="consult"),
                    "expected_mode": MagicMock(value="chat"),
                    "predicted_mode": MagicMock(value="auto"),
                },
            ),
            make_mock_case(
                "case_2",
                labels={
                    "expected_task": MagicMock(value="reflect"),
                    "predicted_task": MagicMock(value="consult"),
                    "expected_mode": MagicMock(value="auto"),
                    "predicted_mode": MagicMock(value="auto"),
                },
            ),
        ]
        report.failures = []

        result = compute_aggregate_metrics(report)

        # Should have metrics for both fields
        assert "task_f1" in result
        assert "mode_f1" in result

    def test_single_class_computes_accuracy_only(self):
        """Single class case should only compute accuracy."""
        report = MagicMock()
        report.cases = [
            make_mock_case(
                "case_1",
                labels={
                    "expected_task": MagicMock(value="consult"),
                    "predicted_task": MagicMock(value="consult"),
                },
            ),
            make_mock_case(
                "case_2",
                labels={
                    "expected_task": MagicMock(value="consult"),
                    "predicted_task": MagicMock(value="consult"),
                },
            ),
        ]
        report.failures = []

        result = compute_aggregate_metrics(report)

        assert "task_accuracy" in result
        assert result["task_accuracy"] == 1.0
