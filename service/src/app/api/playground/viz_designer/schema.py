"""Request/response schemas for viz designer playground endpoint."""

from typing import Any

from pydantic import BaseModel, Field


class VisualizationCreateRequest(BaseModel):
    """Request body for creating a visualization.

    Matches the test data shape from nlp_chart_test_data.yaml:
    nlp_query, output_schema, materialized_data.

    Playground-specific fields:
    - model: Optional LLM model override.
    - tenant_id / user_id: For xlake persistence (defaults to "playground").
    """

    nlp_query: str = Field(
        description="Natural language query describing the desired visualization."
    )
    output_schema: dict[str, Any] = Field(
        description="Schema of data returned by DB (fields, types, roles)."
    )
    materialized_data: list[dict[str, Any]] = Field(
        description="The actual data rows to visualize."
    )
    conversation_id: str | None = Field(
        default=None,
        description="Conversation ID for frozen data snapshots.",
    )
    model: str | None = Field(
        default=None,
        description="Optional model override (e.g. 'anthropic:claude-sonnet-4-20250514').",
    )
    tenant_id: str = Field(
        default="playground",
        description="Tenant ID for xlake persistence.",
    )
    user_id: str = Field(
        default="playground",
        description="User ID for xlake persistence.",
    )


class VisualizationCreateResponse(BaseModel):
    """Response body from visualization creation."""

    chart_id: str = Field(description="Chart ID for persistence and refresh.")
    data_slice_id: str = Field(description="Data slice ID for data refresh.")
    conversation_id: str = Field(description="Conversation ID.")
    chart_spec: dict[str, Any] = Field(
        description="Complete chart spec for inline rendering."
    )
    data: dict[str, Any] = Field(description="Raw data rows for immediate rendering.")
    highlights: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Highlights for chart.",
    )
    insights: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Insights with recommendations.",
    )
