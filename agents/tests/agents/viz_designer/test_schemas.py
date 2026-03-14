"""Unit tests for viz_designer Pydantic schemas."""

import pytest
from pydantic import ValidationError

from agents.viz_designer.schemas import (
    ChartAlternative,
    DataMapping,
    DataMappingSpec,
    DataSeriesClassificationSpec,
    SubChartSpec,
    VizRefinementResponseSchema,
    VizSelectionResponseSchema,
)


class TestDataMapping:
    """Tests for DataMapping schema."""

    def test_minimal(self):
        mapping = DataMapping()
        assert mapping.x_axis is None
        assert mapping.y_axis is None
        assert mapping.series is None
        assert mapping.color is None
        assert mapping.size is None
        assert mapping.value is None

    def test_with_axes(self):
        mapping = DataMapping(x_axis="date", y_axis="sales")
        assert mapping.x_axis == "date"
        assert mapping.y_axis == "sales"

    def test_with_all_fields(self):
        mapping = DataMapping(
            x_axis="date",
            y_axis="sales",
            series="region",
            color="category",
            size="count",
            value="total",
        )
        assert mapping.series == "region"
        assert mapping.color == "category"
        assert mapping.size == "count"
        assert mapping.value == "total"


class TestChartAlternative:
    """Tests for ChartAlternative schema."""

    def test_valid(self):
        alt = ChartAlternative(
            chart_type="bar_chart_vertical",
            tradeoff="Better for comparison but loses temporal context",
        )
        assert alt.chart_type == "bar_chart_vertical"
        assert "Better for comparison" in alt.tradeoff


class TestVizSelectionResponseSchema:
    """Tests for VizSelectionResponseSchema."""

    def test_minimal(self):
        response = VizSelectionResponseSchema(
            chart_type="line_chart",
            reasoning="Line charts are best for showing trends over time",
            confidence="high",
            data_mapping=DataMapping(x_axis="date", y_axis="value"),
        )
        assert response.chart_type == "line_chart"
        assert response.confidence == "high"
        assert response.alternatives == []
        assert response.warnings == []
        assert response.combination_suggestion is None

    def test_with_alternatives(self):
        response = VizSelectionResponseSchema(
            chart_type="line_chart",
            reasoning="Line charts show trends",
            confidence="medium",
            data_mapping=DataMapping(x_axis="date", y_axis="value"),
            alternatives=[
                ChartAlternative(
                    chart_type="area_chart",
                    tradeoff="Shows magnitude but harder to compare",
                )
            ],
        )
        assert len(response.alternatives) == 1
        assert response.alternatives[0].chart_type == "area_chart"

    def test_with_warnings(self):
        response = VizSelectionResponseSchema(
            chart_type="pie_chart",
            reasoning="Pie chart for part-to-whole",
            confidence="low",
            data_mapping=DataMapping(value="percentage"),
            warnings=["Too many categories for pie chart"],
            combination_suggestion="Consider pairing with a bar chart for detailed comparison",
        )
        assert len(response.warnings) == 1
        assert response.combination_suggestion is not None

    def test_invalid_confidence(self):
        with pytest.raises(ValidationError):
            VizSelectionResponseSchema(
                chart_type="line_chart",
                reasoning="Test",
                confidence="invalid",  # Must be high/medium/low
                data_mapping=DataMapping(),
            )


class TestVizRefinementResponseSchema:
    """Tests for VizRefinementResponseSchema."""

    def test_minimal(self):
        response = VizRefinementResponseSchema(
            reasoning="Refined the mapping based on data distribution",
            chart_type="line_chart",
            title="Revenue Over Time",
            data_mapping=DataMappingSpec(x_axis="month", y_axis="revenue"),
        )
        assert "Refined" in response.reasoning
        assert response.chart_type == "line_chart"
        assert response.title == "Revenue Over Time"
        assert response.data_mapping.x_axis == "month"
        assert response.data_series == []
        assert response.highlights == []

    def test_with_data_series(self):
        response = VizRefinementResponseSchema(
            reasoning="Classified series for multi-line chart",
            chart_type="line_chart",
            title="Revenue vs Costs",
            data_mapping=DataMappingSpec(
                x_axis="month", y_axis="value", group_by="metric_type"
            ),
            data_series=[],
        )
        assert response.data_mapping.group_by == "metric_type"

    def test_combo_with_sub_charts(self):
        """Test combo chart refinement response with sub_charts."""
        response = VizRefinementResponseSchema(
            reasoning="Combo chart: bars for revenue/costs, line for margin",
            chart_type="combo",
            title="Revenue vs Costs with Profit Margin",
            data_mapping=DataMappingSpec(x_axis="quarter"),
            sub_charts=[
                SubChartSpec(
                    id="combo__bars",
                    chart_type="bar_chart_vertical",
                    title="Revenue & Costs",
                    data_mapping=DataMappingSpec(x_axis="quarter", y_axis="revenue"),
                    data_series=[
                        DataSeriesClassificationSpec(
                            series_id="revenue",
                            field="revenue",
                            prominence="primary",
                            purpose="data-focus",
                            sentiment="positive",
                            label="Revenue",
                        ),
                        DataSeriesClassificationSpec(
                            series_id="costs",
                            field="operating_costs",
                            prominence="secondary",
                            purpose="data-comparison",
                            sentiment="negative",
                            label="Operating Costs",
                        ),
                    ],
                ),
                SubChartSpec(
                    id="combo__line",
                    chart_type="line_chart",
                    title="Profit Margin Trend",
                    data_mapping=DataMappingSpec(
                        x_axis="quarter", y_axis="profit_margin_pct"
                    ),
                    data_series=[
                        DataSeriesClassificationSpec(
                            series_id="margin",
                            field="profit_margin_pct",
                            prominence="primary",
                            purpose="data-focus",
                            sentiment="positive",
                            label="Margin %",
                        ),
                    ],
                ),
            ],
        )
        assert response.chart_type == "combo"
        assert len(response.sub_charts) == 2
        assert response.sub_charts[0].chart_type == "bar_chart_vertical"
        assert response.sub_charts[0].id == "combo__bars"
        assert len(response.sub_charts[0].data_series) == 2
        assert response.sub_charts[1].chart_type == "line_chart"
        assert response.sub_charts[1].id == "combo__line"
        assert len(response.sub_charts[1].data_series) == 1

    def test_combo_empty_sub_charts(self):
        """Test that combo with empty sub_charts is valid (defaults to [])."""
        response = VizRefinementResponseSchema(
            reasoning="Combo with no sub-charts yet",
            chart_type="combo",
            title="Placeholder Combo",
            data_mapping=DataMappingSpec(x_axis="date"),
        )
        assert response.sub_charts == []

    def test_sub_chart_spec_validation(self):
        """Test SubChartSpec validates required fields."""
        sub = SubChartSpec(
            id="sub_1",
            chart_type="line_chart",
            title="Test Sub",
            data_mapping=DataMappingSpec(x_axis="date", y_axis="value"),
        )
        assert sub.id == "sub_1"
        assert sub.chart_type == "line_chart"
        assert sub.data_series == []

    def test_sub_chart_spec_invalid_chart_type(self):
        """Test SubChartSpec rejects invalid chart types."""
        with pytest.raises(ValidationError):
            SubChartSpec(
                id="sub_bad",
                chart_type="invalid_type",
                title="Bad",
                data_mapping=DataMappingSpec(),
            )
