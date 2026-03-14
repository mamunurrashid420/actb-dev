"""I/O schemas for VisualizationDesigner agent pipeline.

This module defines:
- State schemas (TypedDict) for each pipeline stage
- Response schemas (Pydantic) for structured output from each stage
- Agent output schemas for hybrid response (Option C)

The pipeline is 2-stage: Selection -> Refinement (final)
Agent outputs semantic chart spec; UI handles visual styling.
"""

from typing import Annotated, Any, Literal

from langchain.agents import AgentState
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field, field_validator
from typing_extensions import TypedDict

from shared.data.types import ChartType
from xlake.models import (
    Chart,
    DataSeriesClassification,
    Dimension,
    Filter,
    Highlight,
    Insight,
    ProtoModel,
    ValueRange,
)
from xlake.models import (
    DataMapping as DataMappingProto,
)

# =============================================================================
# Common Types
# =============================================================================

ConfidenceLevel = Literal["high", "medium", "low"]

# Semantic classification types (from protobuf + UI style-guide.ts)
Prominence = Literal[
    "hide", "background", "baseline", "secondary", "primary", "callout"
]
Purpose = Literal["data-focus", "data-comparison", "data-projection"]
Sentiment = Literal["positive", "negative", "neutral", "warning"]
HighlightType = Literal["row", "point_set", "threshold", "range", "point", "annotation"]
DimensionType = Literal["time", "category", "numeric"]


# =============================================================================
# Data Mapping Specs (aligned with protobuf chart.proto)
# =============================================================================


class DataMappingSpec(ProtoModel):
    """Maps schema fields to chart dimensions.

    Aligned with protobuf DataMapping message in chart.proto.
    This is structural (positioning), not semantic (meaning).
    """

    x_axis: str | None = Field(
        default=None,
        description="Field for X-axis (time, category, or numeric)",
    )
    y_axis: str | None = Field(
        default=None,
        description="Field for Y-axis (numeric, or category for horizontal bars)",
    )
    group_by: str | None = Field(
        default=None,
        description="Field to group by for creating series (long-format data)",
    )
    value: str | None = Field(
        default=None,
        description="Primary value field (for KPI, pie, treemap)",
    )
    row: str | None = Field(
        default=None,
        description="Field for grid rows (heatmaps)",
    )
    column: str | None = Field(
        default=None,
        description="Field for grid columns (heatmaps)",
    )

    @classmethod
    def _proto_class(cls):
        return DataMappingProto


class ValueRangeSpec(ProtoModel):
    """Value range for value-based styling (heatmaps, choropleths, gauges).

    Aligned with protobuf ValueRange message in chart.proto.
    """

    min: float = Field(description="Minimum value of the range")
    max: float = Field(description="Maximum value of the range")

    @classmethod
    def _proto_class(cls):
        return ValueRange


class DataSeriesClassificationSpec(ProtoModel):
    """Classification for a data series (agent decision).

    Aligned with protobuf DataSeriesClassification message in chart.proto.
    Semantic metadata that the UI maps to visual styles via style-guide.ts.

    "Series" means: "A group of data points sharing the same styling rules"
    Three ways to identify which data points belong to a series:
    - field: column name (wide-format data)
    - group_value: value in group_by field (long-format data)
    - value_range: numeric range (value-based styling)
    """

    series_id: str = Field(description="Unique identifier for this series")

    # Reference - HOW to identify this series in the data
    field: str | None = Field(
        default=None,
        description="For wide-format data (column name, e.g., 'revenue')",
    )
    group_value: str | None = Field(
        default=None,
        description="For long-format data (value in group_by field, e.g., 'Product A')",
    )

    # Semantic classifications (agent decisions)
    prominence: Prominence = Field(
        description="Visual importance: hide | background | baseline | secondary | primary | callout"
    )
    purpose: Purpose = Field(
        description="Role in story: data-focus | data-comparison | data-projection"
    )
    sentiment: Sentiment | None = Field(
        default=None,
        description="Emotional valence: positive | negative | neutral | warning",
    )

    # Display
    label: str | None = Field(
        default=None,
        description="Human-readable label for legend/tooltip",
    )

    # For value-based styling (heatmaps, choropleths)
    value_range: ValueRangeSpec | None = Field(
        default=None,
        description="For value-based styling (points within this range share styling)",
    )

    @classmethod
    def _proto_class(cls):
        return DataSeriesClassification


# =============================================================================
# Highlight and Insight Specs (aligned with protobuf insights.proto)
# =============================================================================


class HighlightSpec(ProtoModel):
    """Visual instruction for emphasizing data in charts.

    Aligned with protobuf Highlight message in insights.proto.
    References data via selectors, not embedded data.

    Note: The Pydantic ``type`` field uses lowercase (e.g. "row", "point_set")
    while the proto HighlightType enum uses uppercase ("ROW", "POINT_SET").
    The ``_prepare_for_proto`` / ``_prepare_from_proto`` hooks handle this.
    """

    id: str = Field(description="Unique identifier for this highlight")
    type: HighlightType = Field(
        description="Type of highlight: row | point_set | threshold | range | point | annotation"
    )
    insight_id: str = Field(
        description="Back-reference to owning insight (for UI color coordination)"
    )

    # Reference to data slice
    chart_data_slice_id: str | None = Field(
        default=None,
        description="Reference to the data slice this highlight applies to",
    )

    # Data selectors
    row_ids: list[str] | None = Field(
        default=None,
        description="Specific row IDs to highlight (for row/point_set types)",
    )
    field_filters: dict[str, str] | None = Field(
        default=None,
        description="Field-value pairs to filter data points (all values must be strings)",
    )

    @field_validator("field_filters", mode="before")
    @classmethod
    def _coerce_field_filter_values_to_str(
        cls, v: dict[str, Any] | None
    ) -> dict[str, str] | None:
        """Coerce non-string filter values (e.g. booleans) to strings."""
        if v is None:
            return v
        return {k: str(val) for k, val in v.items()}

    # Threshold/range values
    threshold_value: float | None = Field(
        default=None,
        description="Value for threshold line highlights",
    )
    range_min: float | None = Field(
        default=None,
        description="Minimum value for range highlights",
    )
    range_max: float | None = Field(
        default=None,
        description="Maximum value for range highlights",
    )

    # Human-readable description
    description: str | None = Field(
        default=None,
        description="Description of what this highlight represents",
    )

    # Field name for threshold/range highlights
    threshold_range_field: str | None = Field(
        default=None,
        description="Field name for threshold/range (e.g., 'revenue', 'price')",
    )

    @classmethod
    def _proto_class(cls):
        return Highlight

    def _prepare_for_proto(self, data: dict[str, Any]) -> dict[str, Any]:
        """Uppercase the HighlightType enum value for proto."""
        if "type" in data and data["type"] is not None:
            data["type"] = data["type"].upper()
        return data

    @classmethod
    def _prepare_from_proto(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Lowercase the HighlightType enum value for Pydantic."""
        if "type" in data and data["type"] is not None:
            data["type"] = data["type"].lower()
        return data


class InsightSpec(ProtoModel):
    """Observation about data with linked visual evidence.

    Aligned with protobuf Insight message in insights.proto.
    InsightType enum values are already uppercase (e.g. "TREND", "ANOMALY")
    matching the proto enum names, so no case conversion is needed.
    """

    id: str = Field(description="Unique identifier for this insight")
    type: str = Field(description="InsightType enum value (e.g., 'TREND', 'ANOMALY')")
    summary: str = Field(description="Short, user-facing message")
    detail: str | None = Field(
        default=None,
        description="Optional longer explanation",
    )
    confidence: float | None = Field(
        default=None,
        description="Confidence score in [0, 1]",
    )
    highlight_ids: list[str] = Field(
        default_factory=list,
        description="IDs of highlights this insight generated",
    )

    @classmethod
    def _proto_class(cls):
        return Insight


# =============================================================================
# Legacy DataMapping (for Selection stage backwards compatibility)
# =============================================================================


class DataMapping(BaseModel):
    """How schema fields map to chart visual dimensions.

    Based on data-viz-bible schema-to-chart mapping patterns.
    NOTE: This is the legacy format used by Selection stage.
    Use DataMappingSpec for Refinement stage output.
    """

    x_axis: str | None = Field(
        default=None,
        description="Field mapped to X-axis (category, temporal, or measure)",
    )
    y_axis: str | None = Field(
        default=None, description="Field mapped to Y-axis (typically measure)"
    )
    series: str | None = Field(
        default=None,
        description="Field used for grouping/series (dimension for multi-line/grouped)",
    )
    color: str | None = Field(
        default=None,
        description="Field mapped to color encoding (dimension or measure)",
    )
    size: str | None = Field(
        default=None,
        description="Field mapped to size encoding (measure, for bubble charts)",
    )
    value: str | None = Field(
        default=None, description="Field for primary value (KPI cards, single metrics)"
    )


class ChartAlternative(BaseModel):
    """Alternative chart type with trade-off explanation.

    Per data-viz-bible: always identify 1-2 alternatives with trade-offs
    to help downstream refinement if primary choice has issues.
    """

    chart_type: ChartType
    tradeoff: str = Field(
        description="Explanation of trade-off vs primary selection (e.g., 'Better for X but loses Y')"
    )


class VizSelectionResponseSchema(BaseModel):
    """Structured output for chart selection stage.

    Based on data-viz-bible selection/selection.md output specification.
    Captures the systematic evaluation process from the SELECTION_PROMPT.
    """

    chart_type: ChartType = Field(description="Selected chart type identifier")

    reasoning: str = Field(
        description="2-3 sentence explanation of why this chart was selected, "
        "covering data pattern match, user intent alignment, and key deciding factors"
    )

    confidence: ConfidenceLevel = Field(
        description="Selection confidence: 'high' (clear best choice, score >=8), "
        "'medium' (good choice with viable alternatives), 'low' (no clear winner, consider combinations)"
    )

    data_mapping: DataMapping = Field(
        description="How schema fields map to chart visual dimensions"
    )

    alternatives: list[ChartAlternative] = Field(
        default_factory=list,
        min_length=0,
        max_length=3,
        description="1-2 alternative chart types with trade-offs (up to 3 for complex cases)",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="Potential issues or considerations (e.g., 'Too many categories for pie chart', "
        "'Data cardinality may affect readability')",
    )

    combination_suggestion: str | None = Field(
        default=None,
        description="If confidence is 'low' or data has multiple insight layers, "
        "suggest pairing with KPI cards or other charts (per data-viz-bible Step 6)",
    )


# =============================================================================
# Refinement Stage - Response Schema (FINAL AGENT OUTPUT)
# =============================================================================


class VizRefinementResponseSchema(BaseModel):
    """Structured output for refinement stage - the FINAL agent step.

    Per data-viz-bible/refinement/refinement.md:
    "The Refinement action is the final agent step that outputs the
    complete chart specification."

    Agent outputs semantic classifications; UI handles visual styling
    via style-guide.ts (colors, opacity, line styles, structural config).
    """

    reasoning: str = Field(
        description="Agent's reasoning about data series classification and highlights"
    )

    chart_type: ChartType = Field(
        description="Final chart type (may be refined from selection)"
    )

    title: str = Field(
        description="Chart title derived from user query and data context"
    )

    data_mapping: DataMappingSpec = Field(
        description="How data fields map to chart dimensions (x_axis, y_axis, group_by, etc.)"
    )

    data_series: list[DataSeriesClassificationSpec] = Field(
        default_factory=list,
        description="Semantic classifications for each data series (prominence, purpose, sentiment)",
    )

    insights: list[InsightSpec] = Field(
        default_factory=list,
        description="Insights about notable data patterns (generate BEFORE highlights)",
    )

    highlights: list[HighlightSpec] = Field(
        default_factory=list,
        description="Highlights linking to insights for visual emphasis (each must reference an insight_id)",
    )

    sub_charts: list["SubChartSpec"] = Field(
        default_factory=list,
        description="For combo charts: each sub-chart with its own chart_type, "
        "data_mapping, and data_series. Only populated when chart_type is 'combo'.",
    )


# =============================================================================
# Sub-Chart Spec (for combo charts)
# =============================================================================


class SubChartSpec(BaseModel):
    """A sub-chart within a combo. Self-contained chart spec.

    Each sub-chart inherits the parent's chart_data_slice_ids and uses
    its own data_mapping to select which fields to render.
    """

    id: str = Field(description="Sub-chart ID (unique within parent combo)")
    chart_type: ChartType = Field(description="Chart type for this sub-chart")
    title: str = Field(description="Sub-chart title")
    data_mapping: DataMappingSpec = Field(
        description="Field-to-dimension mapping for this sub-chart"
    )
    data_series: list[DataSeriesClassificationSpec] = Field(
        default_factory=list,
        description="Data series classifications for this sub-chart",
    )


# =============================================================================
# Agent Output Schemas (Option C: Hybrid Response)
# =============================================================================


class DimensionSpec(ProtoModel):
    """Dimension definition for a chart axis or grouping.

    Aligned with protobuf Dimension message in chart.proto.
    """

    field: str = Field(description="Field name in the data")
    type: DimensionType = Field(description="Dimension type: time | category | numeric")

    @classmethod
    def _proto_class(cls):
        return Dimension


class FilterSpec(ProtoModel):
    """Filter applied to chart data.

    Aligned with protobuf Filter message in chart.proto.
    """

    field: str = Field(description="Field to filter on")
    operator: str = Field(description="Filter operator (e.g., '=', '>', 'in')")
    value: str = Field(description="Filter value")

    @classmethod
    def _proto_class(cls):
        return Filter


class FullAgentChartSpec(ProtoModel):
    """Complete chart spec for inline rendering.

    Mirrors protobuf Chart message + UI ChartSpec interface.
    This is what gets persisted to CustomerChartStore and returned inline.
    """

    id: str = Field(description="Chart ID (for persistence and refresh)")
    title: str = Field(description="Chart title")
    chart_type: ChartType = Field(description="Chart type identifier")

    dimensions: list[DimensionSpec] = Field(
        default_factory=list,
        description="Dimension definitions for axes and grouping",
    )
    filters: list[FilterSpec] = Field(
        default_factory=list,
        description="Active filters on the chart data",
    )
    chart_data_slice_ids: list[str] = Field(
        default_factory=list,
        description="References to materialized data slices",
    )

    version: int = Field(default=1, description="Chart spec version")
    schema_version: int = Field(default=1, description="Schema version for migrations")

    # Semantic metadata from agent (Refinement output)
    data_mapping: DataMappingSpec | None = Field(
        default=None,
        description="How data fields map to chart dimensions",
    )
    data_series: list[DataSeriesClassificationSpec] = Field(
        default_factory=list,
        description="Semantic classifications for each data series",
    )

    # For combo charts: list of child chart specs
    sub_charts: list["FullAgentChartSpec"] = Field(
        default_factory=list,
        description="For combo charts: list of child chart specs, each fully self-contained. "
        "Sub-charts inherit parent's chart_data_slice_ids if their own is empty.",
    )

    @classmethod
    def _proto_class(cls):
        return Chart


class AgentChartResponse(BaseModel):
    """Final response from viz_designer agent to UI (Option C: Hybrid).

    The agent does BOTH:
    1. Persists chart spec + data slice to CustomerChartStore
    2. Returns full chart_spec + data inline for immediate UI rendering

    This enables:
    - Immediate rendering: UI has everything, no extra API calls
    - Persistence: chart_id enables conversation history, dashboard pinning, sharing
    - Refresh: UI can call get_chart_data(slice_id, context="dashboard") for fresh data
    """

    # Persistence references
    chart_id: str = Field(
        description="Chart ID in CustomerChartStore (for refresh/sharing)"
    )
    data_slice_id: str = Field(description="Data slice ID (for data refresh)")
    conversation_id: str = Field(
        description="Conversation ID (for frozen data snapshots)"
    )

    # Inline data for immediate rendering
    chart_spec: FullAgentChartSpec = Field(
        description="Complete chart spec for inline rendering"
    )
    data: dict[str, Any] = Field(
        description="Raw data rows for immediate rendering (JSON-serializable)"
    )

    # Highlights and insights
    highlights: list[HighlightSpec] = Field(
        default_factory=list,
        description="Highlights for chart (linked to insights via insight_id)",
    )
    insights: list[InsightSpec] = Field(
        default_factory=list,
        description="Insights with recommendations",
    )


# =============================================================================
# State Schemas (TypedDict extending AgentState)
# =============================================================================


class VizSelectionState(AgentState[VizSelectionResponseSchema]):
    """State for selection stage - receives initial NLP query and data."""

    nlp_query: str  # User's natural language query
    output_schema: dict[
        str, Any
    ]  # Schema of data returned by DB (fields, types, roles)
    materialized_data: list[dict[str, Any]]  # The actual data rows


class VizRefinementState(AgentState[VizRefinementResponseSchema]):
    """State for refinement stage (FINAL) - receives selection output.

    This is the final agent stage. After refinement, the agent:
    1. Persists chart spec to CustomerChartStore
    2. Returns AgentChartResponse with inline spec + data
    """

    # From selection stage
    selection_result: VizSelectionResponseSchema

    # Original context (needed for refinement decisions)
    nlp_query: str  # User's natural language query
    output_schema: dict[str, Any]  # Schema of data
    materialized_data: list[dict[str, Any]]  # The actual data rows

    # Conversation context (for persistence)
    conversation_id: str | None  # For frozen data snapshots


# =============================================================================
# Pipeline State Schemas (input / output / internal graph state)
# =============================================================================
#
# These follow the LangGraph ``StateGraph(State, input=Input, output=Output)``
# pattern (see open_deep_research for a production example).
#
#   - ``VizDesignerInput``      – what the caller provides
#   - ``VizDesignerOutput``     – what the caller receives
#   - ``VizDesignerGraphState`` – internal wiring (includes bridge fields
#                                  hidden from the caller by input=/output=)
#
# Sub-agent states (``VizSelectionState``, ``VizRefinementState``) are
# completely independent and are invoked from within node functions
# using the LangGraph "invoke from a node" pattern.
# =============================================================================


class VizDesignerInput(TypedDict):
    """What the caller provides when invoking the pipeline."""

    messages: Annotated[list[AnyMessage], add_messages]
    nlp_query: str
    output_schema: dict[str, Any]
    materialized_data: list[dict[str, Any]]
    conversation_id: str | None


class VizDesignerOutput(TypedDict):
    """What the caller receives back from the pipeline."""

    agent_response: AgentChartResponse | None


class VizDesignerGraphState(TypedDict):
    """Internal orchestration state for the VisualizationDesigner graph.

    Includes all ``VizDesignerInput`` fields plus internal bridge fields
    that are hidden from the caller via the ``input=`` / ``output=``
    schema separation on the ``StateGraph``.
    """

    # ---- From input (provided by the caller) ----
    messages: Annotated[list[AnyMessage], add_messages]
    nlp_query: str
    output_schema: dict[str, Any]
    materialized_data: list[dict[str, Any]]
    conversation_id: str | None

    # ---- Bridge (internal, hidden from caller) ----
    selection_result: VizSelectionResponseSchema | None

    # ---- Output ----
    agent_response: AgentChartResponse | None


# Rebuild models that use forward references (self-referential or cross-references)
VizRefinementResponseSchema.model_rebuild()
FullAgentChartSpec.model_rebuild()
