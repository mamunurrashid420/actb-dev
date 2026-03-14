"""Visualization-specific evaluators."""

from dataclasses import dataclass

from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from agents.viz_designer.schemas import VizInput, VizOutput


@dataclass
class ChartTypeMatch(Evaluator[VizInput, VizOutput]):
    """Exact match on chart type."""

    expected: str

    async def evaluate(self, ctx: EvaluatorContext[VizInput, VizOutput]) -> float:
        return 1.0 if ctx.output.chart_type == self.expected else 0.0


@dataclass
class EncodingFieldsPresent(Evaluator[VizInput, VizOutput]):
    """Check that encoding uses expected fields."""

    required_fields: list[str]

    async def evaluate(self, ctx: EvaluatorContext[VizInput, VizOutput]) -> float:
        encoding = ctx.output.encoding
        present = [encoding.x, encoding.y, encoding.color, encoding.size]
        matches = sum(1 for f in self.required_fields if f in present)
        return matches / len(self.required_fields)


@dataclass
class RationaleQuality(Evaluator[VizInput, VizOutput]):
    """Check rationale mentions key concepts."""

    must_contain: list[str]

    async def evaluate(self, ctx: EvaluatorContext[VizInput, VizOutput]) -> float:
        text = ctx.output.rationale.lower()
        matches = sum(1 for kw in self.must_contain if kw.lower() in text)
        return matches / len(self.must_contain)


@dataclass
class SafetyRules(Evaluator[VizInput, VizOutput]):
    """Validate visualization safety constraints from architecture doc."""

    async def evaluate(self, ctx: EvaluatorContext[VizInput, VizOutput]) -> float:
        violations = []

        # Temporal data should use line/area/bar
        if ctx.input.data_shape == "temporal" and ctx.output.chart_type not in [
            "line_chart",
            "area_chart",
            "bar_chart_vertical",
        ]:
            violations.append("wrong_chart_for_temporal")

        # No pie for temporal
        if ctx.output.chart_type == "pie_chart" and ctx.input.data_shape == "temporal":
            violations.append("pie_for_temporal")

        return 0.0 if violations else 1.0
