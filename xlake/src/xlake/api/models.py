"""Shared Pydantic models for the XLake Unified API.

These models represent the API-level types used across DataClient,
VisualizationClient, and BusinessClient. Domain models are re-exported
from xlake.models (single source of truth).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# =============================================================================
# Re-exports from xlake.models (single source of truth)
# =============================================================================
from xlake.models import (  # noqa: F401
    BusinessMetric,
    DatabaseSchema,
    DataSchema,
    ExternalDataset,
    # Schema models
    Fact,
    FactCreate,
    FieldSchema,
    IndustryTerm,
    # Core domain models
    KnowledgeNugget,
    MetadataMatch,
    QueryResult,
    SchemaContextRecord,
    TableSchema,
    VizDesignRule,
)

# Type aliases for backward compatibility and API naming conventions
FactInfo = Fact
KnowledgeNuggetInfo = KnowledgeNugget
IndustryTermInfo = IndustryTerm


# =============================================================================
# Common Types
# =============================================================================


EntityType = Literal[
    "field",
    "table",
    "kpi",
    "concept",
    "doc_chunk",
    "external_signal",
    "scenario",
    "chart",
    "dashboard",
    "metadata_sentence",
]


# =============================================================================
# Data Client Models
# =============================================================================


class DatasetInfo(BaseModel):
    """Summary information about a dataset."""

    dataset_id: str
    name: str
    namespace: str
    table_name: str
    source_type: str
    file_format: str = "parquet"
    row_count: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DatasetSchema(BaseModel):
    """Schema information for a dataset."""

    dataset_id: str
    columns: list[ColumnInfo] = Field(default_factory=list)
    primary_keys: list[str] = Field(default_factory=list)
    partitions: list[str] = Field(default_factory=list)


class ColumnInfo(BaseModel):
    """Information about a dataset column."""

    name: str
    data_type: str
    nullable: bool = True
    description: str | None = None
    stats: dict[str, Any] | None = None


class DatasetMetadata(BaseModel):
    """Extended metadata for a dataset."""

    dataset_id: str
    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    freshness: datetime | None = None


class LineageInfo(BaseModel):
    """Lineage information for a dataset or entity."""

    entity_id: str
    entity_type: str
    upstream: list[LineageEdge] = Field(default_factory=list)
    downstream: list[LineageEdge] = Field(default_factory=list)


class LineageEdge(BaseModel):
    """A single edge in the lineage graph."""

    source_id: str
    target_id: str
    relationship: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentInfo(BaseModel):
    """Summary information about a document."""

    doc_id: str
    filename: str
    mime_type: str | None = None
    size_bytes: int | None = None
    created_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)


class DocumentMetadata(BaseModel):
    """Extended metadata for a document."""

    doc_id: str
    filename: str
    title: str | None = None
    author: str | None = None
    category: str | None = None
    page_count: int | None = None
    source: str | None = None
    version: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


# =============================================================================
# Visualization Client Models
# =============================================================================


class ChartSummary(BaseModel):
    """Summary information about a chart."""

    chart_id: str
    title: str
    chart_type: str
    version: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DashboardSummary(BaseModel):
    """Summary information about a dashboard."""

    dashboard_id: str
    title: str
    description: str | None = None
    chart_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class StackSummary(BaseModel):
    """Summary information about a chart stack."""

    stack_id: str
    title: str
    chart_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ChartDataSliceInfo(BaseModel):
    """Information about chart data slice for retrieval."""

    slice_id: str
    chart_id: str
    chart_version: int
    data_hash: str | None = None
    generated_at: datetime | None = None
    row_count: int | None = None


# =============================================================================
# Business Client Models
# =============================================================================


class Entity(BaseModel):
    """A semantic entity in the XLake graph."""

    entity_id: str
    entity_type: EntityType
    name: str
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    relationships: list[Relationship] = Field(default_factory=list)
    tenant_id: str | None = None
    confidence: float = 1.0


class Relationship(BaseModel):
    """A relationship between entities."""

    target_id: str
    target_type: EntityType
    relationship_type: str
    confidence: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphResult(BaseModel):
    """Result of a semantic.graph() call."""

    entity: Entity
    neighbors: list[GraphNeighbor] = Field(default_factory=list)


class GraphNeighbor(BaseModel):
    """A neighbor in the semantic graph."""

    id: str
    type: EntityType
    name: str | None = None
    relationship: str
    source: str | None = None  # "structured", "semantic", "document_metadata", etc.
    text: str | None = None  # For metadata sentences
    confidence: float = 1.0


class KPISummary(BaseModel):
    """Summary information about a KPI."""

    kpi_id: str
    name: str
    domain: str
    description: str | None = None
    output_unit: str | None = None


class KPI(BaseModel):
    """Full KPI information."""

    kpi_id: str
    name: str
    domain: str
    description: str
    formula: str | None = None
    formula_type: str = "arithmetic"
    input_fields: list[str] = Field(default_factory=list)
    output_unit: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class KPIDefinition(BaseModel):
    """KPI definition with full formula and lineage."""

    kpi_id: str
    name: str
    domain: str
    description: str
    formula: str | None = None
    formula_type: str = "arithmetic"
    input_fields: list[str] = Field(default_factory=list)
    output_unit: str | None = None
    lineage: dict[str, Any] = Field(default_factory=dict)
    examples: list[str] = Field(default_factory=list)


class SchemaSemantics(BaseModel):
    """Semantic information about a schema entity."""

    schema_id: str
    name: str
    version: int
    description: str | None = None
    entity_count: int = 0


class FullSchema(BaseModel):
    """Complete schema with all entities and relationships."""

    schema_id: str
    name: str
    version: int
    description: str | None = None
    databases: list[dict[str, Any]] = Field(default_factory=list)
    facts_by_entity: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)


class KnowledgeObject(BaseModel):
    """A piece of knowledge to add to the semantic store."""

    content: str
    knowledge_type: Literal[
        "explanation", "relationship", "correction", "definition", "metadata"
    ]
    entity_id: str | None = None
    related_entities: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    source: str | None = None
    tags: list[str] = Field(default_factory=list)


class ConversationContext(BaseModel):
    """Context from a conversation thread."""

    thread_id: str
    summary: str | None = None
    mentioned_entities: list[str] = Field(default_factory=list)
    recent_queries: list[str] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)


class ActiveState(BaseModel):
    """Current active state in a conversation."""

    thread_id: str
    active_chart_id: str | None = None
    active_stack_id: str | None = None
    active_dashboard_id: str | None = None
    active_simulations: list[str] = Field(default_factory=list)
    active_filters: list[dict[str, Any]] = Field(default_factory=list)
    last_referenced_entities: list[str] = Field(default_factory=list)


class InsightInput(BaseModel):
    """Input for adding an insight to a conversation."""

    summary: str
    detail: str | None = None
    related_entities: list[str] = Field(default_factory=list)
    related_charts: list[str] = Field(default_factory=list)
    confidence: float = 1.0


class StateUpdate(BaseModel):
    """Update to conversation state."""

    active_chart_id: str | None = None
    active_stack_id: str | None = None
    active_dashboard_id: str | None = None
    active_simulations: list[str] | None = None
    active_filters: list[dict[str, Any]] | None = None
    last_referenced_entities: list[str] | None = None
    summary: str | None = None


# =============================================================================
# Create Models (API request types - exclude IDs and timestamps)
# =============================================================================


class KnowledgeNuggetCreate(BaseModel):
    """Input for creating a new knowledge nugget."""

    domain: str
    category: str
    content: str
    tags: list[str] | None = None
    sources: list[str] | None = None
    reference_uris: list[str] | None = None
    confidence: float = 1.0


class IndustryTermCreate(BaseModel):
    """Input for creating a new industry term."""

    term: str
    definition: str
    industry: str
    synonyms: list[str] | None = None
    related_terms: list[str] | None = None
    antonyms: list[str] | None = None
    examples: list[str] | None = None
    tags: list[str] | None = None
    reference_uris: list[str] | None = None


# =============================================================================
# Summary Models (lightweight list views)
# =============================================================================


class KnowledgeNuggetSummary(BaseModel):
    """Summary information about a knowledge nugget."""

    nugget_id: str
    domain: str
    category: str
    content: str
    confidence: float = 1.0


class IndustryTermSummary(BaseModel):
    """Summary information about an industry term."""

    term_id: str
    term: str
    industry: str
    definition: str
