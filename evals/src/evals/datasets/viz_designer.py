"""Test case datasets for VisualizationDesigner agent."""

from pydantic import BaseModel, ConfigDict
from pydantic_evals import Case
from pydantic_evals.evaluators import Evaluator

from agents.viz_designer.schemas import VizInput, VizOutput
from evals.evaluators.viz import (
    ChartTypeMatch,
    EncodingFieldsPresent,
    RationaleQuality,
)


class VizCase(BaseModel):
    """VizDesigner test case with dict validation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    inputs: VizInput
    expected_output: VizOutput | None = None
    evaluators: list[Evaluator] = []
    metadata: dict = {}

    def to_case(self) -> Case[VizInput, VizOutput, dict]:
        """Convert to pydantic_evals Case for evaluation."""
        return Case(
            name=self.name,
            inputs=self.inputs,
            expected_output=self.expected_output,
            evaluators=tuple(self.evaluators),
            metadata=self.metadata,
        )


# ─────────────────────────────────────────────────────────────
# Basic Chart Selection
# ─────────────────────────────────────────────────────────────

TEMPORAL_TREND = VizCase.model_validate({
    "name": "temporal_trend",
    "inputs": {
        "intent": "show me revenue trends over time",
        "data_shape": "temporal",
        "fields": ["date", "revenue"],
    },
    "expected_output": {
        "chart_type": "line_chart",
        "encoding": {"x": "date", "y": "revenue"},
        "rationale": "Line chart shows temporal trends",
    },
    "evaluators": [
        ChartTypeMatch(expected="line_chart"),
        EncodingFieldsPresent(required_fields=["date", "revenue"]),
        RationaleQuality(must_contain=["trend", "time"]),
    ],
    "metadata": {"category": "basic", "difficulty": "easy"},
})

CATEGORICAL_COMPARISON = VizCase.model_validate({
    "name": "categorical_comparison",
    "inputs": {
        "intent": "compare sales by region",
        "data_shape": "categorical",
        "fields": ["region", "sales"],
    },
    "expected_output": {
        "chart_type": "bar_chart_vertical",
        "encoding": {"x": "region", "y": "sales"},
        "rationale": "Bar chart for categorical comparison",
    },
    "evaluators": [
        ChartTypeMatch(expected="bar_chart_vertical"),
        EncodingFieldsPresent(required_fields=["region", "sales"]),
    ],
    "metadata": {"category": "basic"},
})

DISTRIBUTION = VizCase.model_validate({
    "name": "distribution",
    "inputs": {
        "intent": "show the distribution of customer ages",
        "data_shape": "distribution",
        "fields": ["age", "count"],
    },
    "expected_output": {
        "chart_type": "histogram",
        "encoding": {"x": "age", "y": "count"},
        "rationale": "Histogram for distribution",
    },
    "evaluators": [ChartTypeMatch(expected="histogram")],
    "metadata": {"category": "basic"},
})

CORRELATION = VizCase.model_validate({
    "name": "correlation",
    "inputs": {
        "intent": "show the relationship between price and quantity sold",
        "data_shape": "correlation",
        "fields": ["price", "quantity"],
    },
    "expected_output": {
        "chart_type": "scatter_plot",
        "encoding": {"x": "price", "y": "quantity"},
        "rationale": "Scatter plot for correlation",
    },
    "evaluators": [
        ChartTypeMatch(expected="scatter_plot"),
        EncodingFieldsPresent(required_fields=["price", "quantity"]),
    ],
    "metadata": {"category": "basic"},
})

# ─────────────────────────────────────────────────────────────
# Edge Cases
# ─────────────────────────────────────────────────────────────

AMBIGUOUS_INTENT = VizCase.model_validate({
    "name": "ambiguous_intent",
    "inputs": {
        "intent": "show me the data",
        "data_shape": "categorical",
        "fields": ["category", "value"],
    },
    "expected_output": None,
    "evaluators": [EncodingFieldsPresent(required_fields=["category", "value"])],
    "metadata": {"category": "edge_case"},
})

# ─────────────────────────────────────────────────────────────
# Exports
# ─────────────────────────────────────────────────────────────

_BASIC = [TEMPORAL_TREND, CATEGORICAL_COMPARISON, DISTRIBUTION, CORRELATION]
_EDGE = [AMBIGUOUS_INTENT]

BASIC_CASES = [c.to_case() for c in _BASIC]
EDGE_CASES = [c.to_case() for c in _EDGE]
ALL_CASES = BASIC_CASES + EDGE_CASES
