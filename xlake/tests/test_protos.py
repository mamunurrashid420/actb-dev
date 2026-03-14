"""Tests for protobuf message definitions.

Verifies that:
1. All proto messages can be imported from xlake.models
2. Messages can be instantiated with valid data
3. Serialization/deserialization roundtrip works
4. Timestamp fields serialize correctly
5. Enum values are accessible
"""

from __future__ import annotations

from datetime import UTC, datetime

from google.protobuf.timestamp_pb2 import Timestamp

from xlake.models import (
    # Insights messages
    AnnotationTarget,
    # Chart
    Chart,
    # ChartDataSlice
    ChartDataSlice,
    # Dashboard
    ChartPlacement,
    # ChartStack
    ChartStack,
    ChartType,
    Dashboard,
    DashboardLayout,
    # DataBinding
    DataBinding,
    DataSource,
    Dimension,
    # OutputSchema
    FieldRole,
    FieldType,
    Filter,
    Highlight,
    # Insights enums
    HighlightType,
    Insight,
    InsightType,
    LogicalFilter,
    OutputField,
    OutputSchema,
    Projection,
    Recommendation,
    RecommendationType,
)


class TestChartMessages:
    """Tests for Chart, Filter, and Dimension messages."""

    def test_filter_creation(self) -> None:
        """Test Filter message instantiation."""
        f = Filter(field="amount", operator=">=", value="100")
        assert f.field == "amount"
        assert f.operator == ">="
        assert f.value == "100"

    def test_dimension_creation(self) -> None:
        """Test Dimension message instantiation."""
        d = Dimension(field="product_category", type="category")
        assert d.field == "product_category"
        assert d.type == "category"

    def test_chart_creation(self) -> None:
        """Test Chart message instantiation."""
        chart = Chart(
            id="chart_violin_sales_v1",
            title="Sales Distribution by Category",
            chart_type="violin_plot",
            dimensions=[
                Dimension(field="name", type="category"),
                Dimension(field="value", type="numeric"),
            ],
            filters=[Filter(field="year", operator="=", value="2024")],
            chart_data_slice_ids=["slice_1", "slice_2"],
            version=1,
            schema_version=1,
        )
        assert chart.id == "chart_violin_sales_v1"
        assert chart.title == "Sales Distribution by Category"
        assert chart.chart_type == ChartType.Value("violin_plot")
        assert len(chart.dimensions) == 2
        assert len(chart.filters) == 1
        assert len(chart.chart_data_slice_ids) == 2
        assert chart.version == 1
        assert chart.schema_version == 1

    def test_chart_serialization_roundtrip(self) -> None:
        """Test Chart serialization and deserialization."""
        original = Chart(
            id="test_chart",
            title="Test Chart",
            chart_type="bar_chart_vertical",
            version=1,
            schema_version=1,
        )
        serialized = original.SerializeToString()
        deserialized = Chart()
        deserialized.ParseFromString(serialized)

        assert deserialized.id == original.id
        assert deserialized.title == original.title
        assert deserialized.chart_type == original.chart_type

    def test_combo_chart_with_sub_charts(self) -> None:
        """Test Chart with sub_charts for combo chart type."""
        combo = Chart(
            id="combo_revenue_margin",
            title="Revenue vs Costs with Profit Margin",
            chart_type="combo",
            chart_data_slice_ids=["slice_quarterly_financials"],
            version=1,
            schema_version=1,
            sub_charts=[
                Chart(
                    id="combo_revenue_margin__bars",
                    title="Revenue & Operating Costs",
                    chart_type="bar_chart_vertical",
                    dimensions=[
                        Dimension(field="quarter", type="time"),
                        Dimension(field="revenue", type="numeric"),
                    ],
                ),
                Chart(
                    id="combo_revenue_margin__line",
                    title="Profit Margin Trend",
                    chart_type="line_chart",
                    dimensions=[
                        Dimension(field="quarter", type="time"),
                        Dimension(field="profit_margin_pct", type="numeric"),
                    ],
                ),
            ],
        )
        assert combo.chart_type == ChartType.Value("combo")
        assert len(combo.sub_charts) == 2
        assert combo.sub_charts[0].id == "combo_revenue_margin__bars"
        assert combo.sub_charts[0].chart_type == ChartType.Value("bar_chart_vertical")
        assert combo.sub_charts[1].id == "combo_revenue_margin__line"
        assert combo.sub_charts[1].chart_type == ChartType.Value("line_chart")

    def test_combo_chart_serialization_roundtrip(self) -> None:
        """Test combo Chart serialization preserves sub_charts."""
        original = Chart(
            id="combo_test",
            title="Combo Test",
            chart_type="combo",
            version=1,
            schema_version=1,
            sub_charts=[
                Chart(
                    id="sub_bar",
                    title="Bar Sub",
                    chart_type="bar_chart_vertical",
                ),
                Chart(
                    id="sub_line",
                    title="Line Sub",
                    chart_type="line_chart",
                ),
            ],
        )
        serialized = original.SerializeToString()
        deserialized = Chart()
        deserialized.ParseFromString(serialized)

        assert deserialized.id == original.id
        assert deserialized.chart_type == original.chart_type
        assert len(deserialized.sub_charts) == 2
        assert deserialized.sub_charts[0].id == "sub_bar"
        assert deserialized.sub_charts[0].chart_type == ChartType.Value(
            "bar_chart_vertical"
        )
        assert deserialized.sub_charts[1].id == "sub_line"
        assert deserialized.sub_charts[1].chart_type == ChartType.Value("line_chart")

    def test_combo_chart_json_roundtrip(self) -> None:
        """Test combo Chart JSON serialization preserves sub_charts."""
        from google.protobuf.json_format import MessageToJson, Parse

        original = Chart(
            id="combo_json_test",
            title="Combo JSON Test",
            chart_type="combo",
            chart_data_slice_ids=["slice_1"],
            version=1,
            schema_version=1,
            sub_charts=[
                Chart(
                    id="sub_bar",
                    title="Bar",
                    chart_type="bar_chart_vertical",
                    dimensions=[Dimension(field="quarter", type="time")],
                ),
                Chart(
                    id="sub_line",
                    title="Line",
                    chart_type="line_chart",
                    dimensions=[Dimension(field="quarter", type="time")],
                ),
            ],
        )

        json_str = MessageToJson(original)
        import json

        json_data = json.loads(json_str)
        assert "subCharts" in json_data
        assert len(json_data["subCharts"]) == 2
        assert json_data["subCharts"][0]["chartType"] == "bar_chart_vertical"
        assert json_data["subCharts"][1]["chartType"] == "line_chart"

        restored = Parse(json_str, Chart())
        assert len(restored.sub_charts) == 2
        assert restored.sub_charts[0].id == "sub_bar"
        assert restored.sub_charts[1].id == "sub_line"


class TestChartStackMessages:
    """Tests for ChartStack message."""

    def test_chart_stack_creation(self) -> None:
        """Test ChartStack message instantiation."""
        stack = ChartStack(
            id="stack_sales_overview",
            title="Sales Overview",
            charts=[
                Chart(id="chart_1", title="Chart 1", chart_type="bar_chart_vertical"),
                Chart(id="chart_2", title="Chart 2", chart_type="line_chart"),
            ],
            schema_version=1,
        )
        assert stack.id == "stack_sales_overview"
        assert stack.title == "Sales Overview"
        assert len(stack.charts) == 2

    def test_chart_stack_with_timestamps(self) -> None:
        """Test ChartStack with timestamp fields."""
        now = Timestamp()
        now.FromDatetime(datetime.now(UTC))

        stack = ChartStack(
            id="stack_with_timestamps",
            title="Timestamped Stack",
            created_at=now,
            updated_at=now,
            schema_version=1,
        )
        assert stack.created_at.seconds > 0
        assert stack.updated_at.seconds > 0


class TestDashboardMessages:
    """Tests for Dashboard, ChartPlacement, and DashboardLayout messages."""

    def test_chart_placement_creation(self) -> None:
        """Test ChartPlacement message instantiation."""
        placement = ChartPlacement(chart_id="chart_1", level=1, order=0)
        assert placement.chart_id == "chart_1"
        assert placement.level == 1
        assert placement.order == 0

    def test_dashboard_layout_creation(self) -> None:
        """Test DashboardLayout message instantiation."""
        layout = DashboardLayout(
            placements=[
                ChartPlacement(chart_id="chart_1", level=1, order=0),
                ChartPlacement(chart_id="chart_2", level=2, order=0),
            ]
        )
        assert len(layout.placements) == 2

    def test_dashboard_creation(self) -> None:
        """Test Dashboard message instantiation."""
        dashboard = Dashboard(
            id="dashboard_main",
            title="Main Dashboard",
            description="Overview of key metrics",
            stacks=[
                ChartStack(id="stack_1", title="Stack 1"),
            ],
            layout=DashboardLayout(
                placements=[ChartPlacement(chart_id="chart_1", level=1, order=0)]
            ),
            schema_version=1,
        )
        assert dashboard.id == "dashboard_main"
        assert dashboard.title == "Main Dashboard"
        assert len(dashboard.stacks) == 1
        assert len(dashboard.layout.placements) == 1


class TestInsightMessages:
    """Tests for AnnotationTarget, Highlight, Insight, and Recommendation messages."""

    def test_annotation_target_chart(self) -> None:
        """Test AnnotationTarget with chart_id."""
        target = AnnotationTarget(chart_id="chart_1")
        assert target.chart_id == "chart_1"
        assert target.WhichOneof("target") == "chart_id"

    def test_annotation_target_dashboard(self) -> None:
        """Test AnnotationTarget with dashboard_id."""
        target = AnnotationTarget(dashboard_id="dashboard_1")
        assert target.dashboard_id == "dashboard_1"
        assert target.WhichOneof("target") == "dashboard_id"

    def test_highlight_creation(self) -> None:
        """Test Highlight message instantiation."""
        highlight = Highlight(
            id="highlight_1",
            type=HighlightType.Value("ROW"),
            chart_data_slice_id="slice_1",
            row_ids=["r1", "r2"],
            description="Outlier values",
        )
        assert highlight.id == "highlight_1"
        assert highlight.type == HighlightType.Value("ROW")
        assert len(highlight.row_ids) == 2

    def test_highlight_with_threshold(self) -> None:
        """Test Highlight with threshold value."""
        highlight = Highlight(
            id="highlight_threshold",
            type=HighlightType.Value("THRESHOLD"),
            chart_data_slice_id="slice_1",
            threshold_value=100.0,
        )
        assert highlight.threshold_value == 100.0

    def test_highlight_with_range(self) -> None:
        """Test Highlight with range values."""
        highlight = Highlight(
            id="highlight_range",
            type=HighlightType.Value("RANGE"),
            chart_data_slice_id="slice_1",
            range_min=50.0,
            range_max=150.0,
        )
        assert highlight.range_min == 50.0
        assert highlight.range_max == 150.0

    def test_highlight_type_enum_values(self) -> None:
        """Test HighlightType enum values are accessible."""
        assert HighlightType.Value("ROW") == 1
        assert HighlightType.Value("POINT_SET") == 2
        assert HighlightType.Value("THRESHOLD") == 3
        assert HighlightType.Value("RANGE") == 4
        assert HighlightType.Value("POINT") == 5
        assert HighlightType.Value("ANNOTATION") == 6

    def test_insight_creation(self) -> None:
        """Test Insight message instantiation."""
        insight = Insight(
            id="insight_1",
            type=InsightType.Value("ALERT"),
            summary="Sales dropped 15%",
            detail="Sales in Q4 were significantly lower than Q3",
            confidence=0.85,
            target=AnnotationTarget(chart_id="chart_1"),
            highlight_ids=["h1"],
            schema_version=1,
        )
        assert insight.id == "insight_1"
        assert insight.type == InsightType.Value("ALERT")
        assert insight.confidence == 0.85
        assert len(insight.highlight_ids) == 1

    def test_insight_type_enum_values(self) -> None:
        """Test InsightType enum values are accessible."""
        assert InsightType.Value("ALERT") == 1
        assert InsightType.Value("WARNING") == 2
        assert InsightType.Value("NEGATIVE") == 3
        assert InsightType.Value("NEUTRAL") == 4
        assert InsightType.Value("POSITIVE") == 5
        assert InsightType.Value("THUMBS_UP") == 6
        assert InsightType.Value("LIGHTBULB") == 7
        assert InsightType.Value("ANOMALY") == 8
        assert InsightType.Value("TREND") == 9
        assert InsightType.Value("COMPARISON") == 10
        assert InsightType.Value("CONFIRMATION") == 11

    def test_recommendation_creation(self) -> None:
        """Test Recommendation message instantiation."""
        rec = Recommendation(
            id="rec_1",
            type=RecommendationType.Value("REPORT"),
            summary="Schedule weekly sales report",
            detail="Based on the volatility, consider monitoring more frequently",
            priority="high",
            action_params={
                "frequency": "weekly",
                "recipients": "sales-team@example.com",
            },
        )
        assert rec.id == "rec_1"
        assert rec.type == RecommendationType.Value("REPORT")
        assert rec.priority == "high"
        assert rec.action_params["frequency"] == "weekly"

    def test_recommendation_type_enum_values(self) -> None:
        """Test RecommendationType enum values are accessible."""
        assert RecommendationType.Value("FYI") == 1
        assert RecommendationType.Value("REPORT") == 2
        assert RecommendationType.Value("NOTIFICATION") == 3
        assert RecommendationType.Value("EXPORT") == 4
        assert RecommendationType.Value("SHARE") == 5
        assert RecommendationType.Value("EXPERIMENT") == 6
        assert RecommendationType.Value("INVESTIGATION") == 7
        assert RecommendationType.Value("ENRICH_DATA") == 8


class TestDataBindingMessages:
    """Tests for DataSource, LogicalFilter, Projection, and DataBinding messages."""

    def test_data_source_creation(self) -> None:
        """Test DataSource message instantiation."""
        source = DataSource(system="customer_datalake", table="sales")
        assert source.system == "customer_datalake"
        assert source.table == "sales"

    def test_logical_filter_creation(self) -> None:
        """Test LogicalFilter message instantiation."""
        f = LogicalFilter(field="year", operator="=", value="2024")
        assert f.field == "year"
        assert f.operator == "="
        assert f.value == "2024"

    def test_projection_creation(self) -> None:
        """Test Projection message instantiation."""
        proj = Projection(field="product_category", alias="name")
        assert proj.field == "product_category"
        assert proj.alias == "name"

    def test_data_binding_creation(self) -> None:
        """Test DataBinding message instantiation."""
        binding = DataBinding(
            id="binding_sales_by_category",
            version=1,
            sources=[DataSource(system="customer_datalake", table="sales")],
            filters=[LogicalFilter(field="year", operator="=", value="2024")],
            projections=[
                Projection(field="product_category", alias="name"),
                Projection(field="amount", alias="value"),
            ],
            schema_version=1,
        )
        assert binding.id == "binding_sales_by_category"
        assert len(binding.sources) == 1
        assert len(binding.projections) == 2


class TestOutputSchemaMessages:
    """Tests for FieldType, FieldRole, OutputField, and OutputSchema messages."""

    def test_field_type_enum_values(self) -> None:
        """Test FieldType enum values are accessible."""
        # Access via the enum wrapper
        assert FieldType.Value("STRING") == 1
        assert FieldType.Value("INT") == 2
        assert FieldType.Value("FLOAT") == 3
        assert FieldType.Value("BOOLEAN") == 4
        assert FieldType.Value("DATE") == 5
        assert FieldType.Value("TIMESTAMP") == 6

    def test_field_role_enum_values(self) -> None:
        """Test FieldRole enum values are accessible."""
        assert FieldRole.Value("IDENTIFIER") == 1
        assert FieldRole.Value("DIMENSION") == 2
        assert FieldRole.Value("MEASURE") == 3

    def test_output_field_creation(self) -> None:
        """Test OutputField message instantiation."""
        field = OutputField(
            name="value",
            type=FieldType.Value("FLOAT"),
            role=FieldRole.Value("MEASURE"),
            context="Sales amount in EUR",
            nullable=False,
        )
        assert field.name == "value"
        assert field.type == FieldType.Value("FLOAT")
        assert field.role == FieldRole.Value("MEASURE")
        assert field.context == "Sales amount in EUR"
        assert field.nullable is False

    def test_output_schema_creation(self) -> None:
        """Test OutputSchema message instantiation."""
        schema = OutputSchema(
            id="schema_violin_sales_v1",
            version=1,
            name="violin_sales_by_category",
            fields=[
                OutputField(
                    name="row_id",
                    type=FieldType.Value("STRING"),
                    role=FieldRole.Value("IDENTIFIER"),
                    context="Stable identifier for a single sales record",
                ),
                OutputField(
                    name="name",
                    type=FieldType.Value("STRING"),
                    role=FieldRole.Value("DIMENSION"),
                    context="Product category sold",
                ),
                OutputField(
                    name="value",
                    type=FieldType.Value("FLOAT"),
                    role=FieldRole.Value("MEASURE"),
                    context="Sales amount in EUR",
                ),
            ],
            primary_key=["row_id"],
            schema_version=1,
        )
        assert schema.id == "schema_violin_sales_v1"
        assert schema.name == "violin_sales_by_category"
        assert len(schema.fields) == 3
        assert schema.primary_key == ["row_id"]

    def test_output_schema_serialization_roundtrip(self) -> None:
        """Test OutputSchema serialization and deserialization."""
        original = OutputSchema(
            id="test_schema",
            version=1,
            name="test",
            fields=[
                OutputField(
                    name="id",
                    type=FieldType.Value("STRING"),
                    role=FieldRole.Value("IDENTIFIER"),
                )
            ],
            primary_key=["id"],
            schema_version=1,
        )
        serialized = original.SerializeToString()
        deserialized = OutputSchema()
        deserialized.ParseFromString(serialized)

        assert deserialized.id == original.id
        assert deserialized.name == original.name
        assert len(deserialized.fields) == 1


class TestChartDataSliceMessages:
    """Tests for ChartDataSlice message."""

    def test_chart_data_slice_creation(self) -> None:
        """Test ChartDataSlice message instantiation."""
        slice_ = ChartDataSlice(
            id="slice_chart_violin_sales_v1",
            chart_id="chart_violin_sales_v1",
            chart_version=1,
            data_binding_id="binding_sales_by_category",
            data_binding_version=1,
            output_schema_id="schema_violin_sales_v1",
            json_uri="db://chart_data/slice_chart_violin_sales_v1",
            data_hash="9baf...",
            schema_hash="1a22...",
        )
        assert slice_.id == "slice_chart_violin_sales_v1"
        assert slice_.chart_id == "chart_violin_sales_v1"
        assert slice_.data_binding_id == "binding_sales_by_category"
        assert slice_.json_uri == "db://chart_data/slice_chart_violin_sales_v1"

    def test_chart_data_slice_with_timestamp(self) -> None:
        """Test ChartDataSlice with generated_at timestamp."""
        now = Timestamp()
        now.FromDatetime(datetime.now(UTC))

        slice_ = ChartDataSlice(
            id="slice_with_timestamp",
            chart_id="chart_1",
            chart_version=1,
            generated_at=now,
        )
        assert slice_.generated_at.seconds > 0

    def test_chart_data_slice_serialization_roundtrip(self) -> None:
        """Test ChartDataSlice serialization and deserialization."""
        original = ChartDataSlice(
            id="test_slice",
            chart_id="chart_1",
            chart_version=1,
            data_binding_id="binding_1",
            data_binding_version=1,
            output_schema_id="schema_1",
        )
        serialized = original.SerializeToString()
        deserialized = ChartDataSlice()
        deserialized.ParseFromString(serialized)

        assert deserialized.id == original.id
        assert deserialized.chart_id == original.chart_id


class TestIntegration:
    """Integration tests for combined protobuf usage."""

    def test_full_dashboard_hierarchy(self) -> None:
        """Test creating a complete dashboard with all related artifacts."""
        # Create output schema
        schema = OutputSchema(
            id="schema_sales",
            version=1,
            name="sales_schema",
            fields=[
                OutputField(
                    name="row_id",
                    type=FieldType.Value("STRING"),
                    role=FieldRole.Value("IDENTIFIER"),
                ),
                OutputField(
                    name="category",
                    type=FieldType.Value("STRING"),
                    role=FieldRole.Value("DIMENSION"),
                ),
                OutputField(
                    name="amount",
                    type=FieldType.Value("FLOAT"),
                    role=FieldRole.Value("MEASURE"),
                ),
            ],
            primary_key=["row_id"],
        )

        # Create data binding
        binding = DataBinding(
            id="binding_sales",
            version=1,
            sources=[DataSource(system="datalake", table="sales")],
            projections=[
                Projection(field="product_category", alias="category"),
                Projection(field="sale_amount", alias="amount"),
            ],
        )

        # Create chart
        chart = Chart(
            id="chart_sales",
            title="Sales by Category",
            chart_type="bar_chart_vertical",
            dimensions=[
                Dimension(field="category", type="category"),
                Dimension(field="amount", type="numeric"),
            ],
            chart_data_slice_ids=["slice_1"],
            version=1,
        )

        # Create chart stack
        stack = ChartStack(
            id="stack_overview",
            title="Overview",
            charts=[chart],
        )

        # Create dashboard
        dashboard = Dashboard(
            id="dashboard_main",
            title="Sales Dashboard",
            stacks=[stack],
            layout=DashboardLayout(
                placements=[ChartPlacement(chart_id="chart_sales", level=1, order=0)]
            ),
        )

        # Create insight
        insight = Insight(
            id="insight_trend",
            type=InsightType.Value("LIGHTBULB"),
            summary="Sales trending upward",
            target=AnnotationTarget(chart_id="chart_sales"),
            confidence=0.9,
        )

        # Verify relationships
        assert dashboard.stacks[0].id == stack.id
        assert dashboard.stacks[0].charts[0].id == chart.id
        assert insight.target.chart_id == chart.id

        # Verify all can be serialized
        assert len(schema.SerializeToString()) > 0
        assert len(binding.SerializeToString()) > 0
        assert len(chart.SerializeToString()) > 0
        assert len(stack.SerializeToString()) > 0
        assert len(dashboard.SerializeToString()) > 0
        assert len(insight.SerializeToString()) > 0


class TestJsonSerialization:
    """Tests for JSON serialization and deserialization of protobuf messages."""

    def test_dashboard_to_json_roundtrip(self) -> None:
        """Test exporting a Dashboard to JSON and reading it back."""
        from google.protobuf.json_format import MessageToJson, Parse

        # Create a complete dashboard with nested structures
        now = Timestamp()
        now.FromDatetime(datetime.now(UTC))

        original = Dashboard(
            id="dashboard_sales_q4",
            title="Q4 Sales Dashboard",
            description="Quarterly sales performance overview",
            stacks=[
                ChartStack(
                    id="stack_overview",
                    title="Sales Overview",
                    charts=[
                        Chart(
                            id="chart_revenue",
                            title="Revenue by Region",
                            chart_type="bar_chart_vertical",
                            dimensions=[
                                Dimension(field="region", type="category"),
                                Dimension(field="revenue", type="numeric"),
                            ],
                            filters=[
                                Filter(field="quarter", operator="=", value="Q4"),
                            ],
                            chart_data_slice_ids=["slice_revenue_q4"],
                            version=1,
                            schema_version=1,
                        ),
                        Chart(
                            id="chart_trend",
                            title="Monthly Trend",
                            chart_type="line_chart",
                            dimensions=[
                                Dimension(field="month", type="time"),
                                Dimension(field="sales", type="numeric"),
                            ],
                            version=1,
                            schema_version=1,
                        ),
                    ],
                    created_at=now,
                    updated_at=now,
                    schema_version=1,
                ),
            ],
            layout=DashboardLayout(
                placements=[
                    ChartPlacement(chart_id="chart_revenue", level=1, order=0),
                    ChartPlacement(chart_id="chart_trend", level=2, order=0),
                ]
            ),
            created_at=now,
            updated_at=now,
            schema_version=1,
        )

        # Export to JSON
        json_str = MessageToJson(original)

        # Verify JSON is valid and contains expected fields
        import json

        json_data = json.loads(json_str)
        assert json_data["id"] == "dashboard_sales_q4"
        assert json_data["title"] == "Q4 Sales Dashboard"
        assert len(json_data["stacks"]) == 1
        assert len(json_data["stacks"][0]["charts"]) == 2
        assert len(json_data["layout"]["placements"]) == 2

        # Parse JSON back to protobuf
        restored = Parse(json_str, Dashboard())

        # Verify restored message matches original
        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.description == original.description
        assert len(restored.stacks) == len(original.stacks)
        assert restored.stacks[0].id == original.stacks[0].id
        assert len(restored.stacks[0].charts) == len(original.stacks[0].charts)
        assert restored.stacks[0].charts[0].id == original.stacks[0].charts[0].id
        assert (
            restored.stacks[0].charts[0].chart_type
            == original.stacks[0].charts[0].chart_type
        )
        assert len(restored.layout.placements) == len(original.layout.placements)
        assert restored.schema_version == original.schema_version

    def test_insight_to_json_with_enums(self) -> None:
        """Test that enum values serialize correctly to JSON."""
        from google.protobuf.json_format import MessageToJson, Parse

        original = Insight(
            id="insight_anomaly",
            type=InsightType.Value("ANOMALY"),
            summary="Unusual spike in orders",
            detail="Orders increased 300% compared to same period last year",
            confidence=0.92,
            target=AnnotationTarget(chart_id="chart_orders"),
            highlight_ids=["h1", "h2"],
            recommendations=[
                Recommendation(
                    id="rec_1",
                    type=RecommendationType.Value("INVESTIGATION"),
                    summary="Investigate the spike",
                    priority="high",
                ),
            ],
            schema_version=1,
        )

        # Export to JSON
        json_str = MessageToJson(original)

        # Verify enum is serialized as string name
        import json

        json_data = json.loads(json_str)
        assert json_data["type"] == "ANOMALY"
        assert json_data["highlightIds"] == ["h1", "h2"]
        assert json_data["recommendations"][0]["type"] == "INVESTIGATION"

        # Parse back
        restored = Parse(json_str, Insight())
        assert restored.type == InsightType.Value("ANOMALY")
        assert list(restored.highlight_ids) == ["h1", "h2"]
        assert restored.recommendations[0].type == RecommendationType.Value(
            "INVESTIGATION"
        )

    def test_recommendation_to_json_with_action_params(self) -> None:
        """Test that map fields serialize correctly to JSON."""
        from google.protobuf.json_format import MessageToJson, Parse

        original = Recommendation(
            id="rec_experiment",
            type=RecommendationType.Value("EXPERIMENT"),
            summary="Test alternative pricing strategy",
            detail="Run A/B test with 10% discount in selected regions",
            priority="high",
            action_params={
                "experiment_type": "ab_test",
                "variant_a": "current_pricing",
                "variant_b": "10_percent_discount",
                "duration_days": "30",
                "target_regions": "EMEA,APAC",
            },
        )

        # Export to JSON
        json_str = MessageToJson(original)

        # Verify map is serialized correctly
        import json

        json_data = json.loads(json_str)
        assert json_data["actionParams"]["experiment_type"] == "ab_test"
        assert json_data["actionParams"]["duration_days"] == "30"

        # Parse back
        restored = Parse(json_str, Recommendation())
        assert restored.action_params["experiment_type"] == "ab_test"
        assert restored.action_params["target_regions"] == "EMEA,APAC"
        assert len(restored.action_params) == 5
