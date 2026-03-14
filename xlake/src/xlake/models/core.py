"""Core domain models for XLake stores.

This module contains domain models that were previously defined in individual stores.
By centralizing them here, we maintain a single source of truth for all domain models.

Includes ProtoModel, a Pydantic BaseModel subclass with bidirectional protobuf
conversion (to_proto / from_proto) for models that mirror protobuf messages.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar, Self

from google.protobuf.json_format import MessageToDict, ParseDict
from google.protobuf.message import Message
from pydantic import BaseModel, Field

from .schema import Fact

# =============================================================================
# ProtoModel Base Class (Pydantic <-> Protobuf)
# =============================================================================


class ProtoModel(BaseModel):
    """Pydantic model with bidirectional protobuf conversion.

    Subclass this for any Pydantic model that mirrors a protobuf message.
    Override ``_proto_class()`` to specify the target protobuf message type.

    Conversion details:
    - ``to_proto()`` serialises via ``model_dump(exclude_none=True)`` then
      ``ParseDict``.  Proto3 has no null concept, so ``None`` fields are
      simply omitted (the proto field keeps its default).
    - ``from_proto()`` deserialises via ``MessageToDict`` with
      ``preserving_proto_field_name=True`` (both Pydantic and proto use
      snake_case) and ``always_print_fields_with_no_presence=True`` (so
      proto3 scalar defaults like 0 / "" are included for Pydantic
      validation).

    Override the ``_prepare_for_proto`` / ``_prepare_from_proto`` hooks in
    subclasses that need field-level transforms (e.g. enum case conversion).

    Example::

        from xlake.models import ProtoModel, DataMapping

        class DataMappingSpec(ProtoModel):
            x_axis: str | None = None
            y_axis: str | None = None

            @classmethod
            def _proto_class(cls):
                return DataMapping

        spec = DataMappingSpec(x_axis="date", y_axis="revenue")
        proto = spec.to_proto()          # -> DataMapping protobuf message
        roundtrip = DataMappingSpec.from_proto(proto)  # -> DataMappingSpec
    """

    # Subclasses can set this as a ClassVar shortcut instead of overriding
    # _proto_class().  Left as None here so the base class stays generic.
    _proto_message: ClassVar[type[Message] | None] = None

    @classmethod
    def _proto_class(cls) -> type[Message]:
        """Return the protobuf message class for this model.

        Override in subclasses, or set ``_proto_message`` as a ClassVar.
        """
        if cls._proto_message is not None:
            return cls._proto_message
        raise NotImplementedError(
            f"{cls.__name__} must override _proto_class() or set _proto_message"
        )

    # -- Conversion methods ---------------------------------------------------

    def to_proto(self) -> Message:
        """Convert this Pydantic model to its protobuf counterpart."""
        data = self.model_dump(exclude_none=True)
        data = self._prepare_for_proto(data)
        return ParseDict(data, self._proto_class()())

    @classmethod
    def from_proto(cls, proto: Message) -> Self:
        """Construct a Pydantic model from a protobuf message."""
        data = MessageToDict(
            proto,
            preserving_proto_field_name=True,
            always_print_fields_with_no_presence=True,
        )
        data = cls._prepare_from_proto(data)
        return cls.model_validate(data)

    # -- Hooks for subclass transforms ----------------------------------------

    def _prepare_for_proto(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform the dict *before* ``ParseDict``.

        Override in subclasses for enum case conversion, field renaming, etc.
        """
        return data

    @classmethod
    def _prepare_from_proto(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Transform the dict *after* ``MessageToDict``.

        Override in subclasses for enum case conversion, field renaming, etc.
        """
        return data


# =============================================================================
# CoreContextStore Domain Models
# =============================================================================


class KnowledgeNugget(BaseModel):
    """Expert knowledge about business domains (finance, supply chain, CRM, etc.)."""

    nugget_id: str
    domain: str  # e.g., "finance", "supply_chain", "crm"
    category: str  # sub-category within domain
    content: str  # the knowledge text
    tags: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)  # where this knowledge came from
    reference_uris: list[str] = Field(
        default_factory=list
    )  # links to external reference pages
    confidence: float = 1.0
    created_at: datetime
    updated_at: datetime


class BusinessMetric(BaseModel):
    """KPI/metric definitions with formulas, lineage, and computation rules."""

    metric_id: str
    name: str
    domain: str
    formula: str | None = None  # e.g., "(revenue - cost) / revenue"
    formula_type: str = "arithmetic"  # "arithmetic", "sql", "aggregation"
    input_fields: list[str] = Field(
        default_factory=list
    )  # fields/tables this metric depends on
    output_unit: str | None = None  # e.g., "percentage", "currency"
    description: str
    lineage: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    reference_uris: list[str] = Field(
        default_factory=list
    )  # links to external reference pages
    created_at: datetime
    updated_at: datetime


class IndustryTerm(BaseModel):
    """Industry-specific terms with definitions, synonyms, and relationships to other terms."""

    term_id: str
    term: str
    definition: str
    industry: str  # e.g., "coffee", "automotive", "retail"
    synonyms: list[str] = Field(default_factory=list)
    related_terms: list[str] = Field(
        default_factory=list
    )  # IDs of related IndustryTerms
    antonyms: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    reference_uris: list[str] = Field(
        default_factory=list
    )  # links to external reference pages
    created_at: datetime
    updated_at: datetime


class VizDesignRule(BaseModel):
    """Visualization knowledge chunk from data-viz-bible.

    Represents a semantic chunk of visualization design knowledge, sourced from
    the data-viz-bible knowledge base. Each rule captures metadata from the
    document's YAML frontmatter plus the content itself.

    Document types:
    - "reference": Foundation documents (schema-reference, classification-system, index)
    - "action-interface": Pipeline stage blueprints (selection.md, refinement.md, etc.)
    - "action-implementation": Chart-specific rules (selection-line-chart.md, etc.)

    Pipeline stages:
    - "selection": Choosing the right chart type for data patterns
    - "refinement": Classifying elements and applying design principles
    - "formatting": Applying visual styles based on classifications
    - "implementation": Generating library-specific code
    """

    rule_id: str

    # Document Identity
    document_type: str  # "reference" | "action-interface" | "action-implementation"
    origin_path: str  # "/data-viz-bible/selection/selection-line-chart.md"

    # Pipeline Context (nullable for foundation/reference docs)
    pipeline_stage: str | None = (
        None  # "selection" | "refinement" | "formatting" | "implementation"
    )
    chart_type: str | None = (
        None  # snake_case values: "line_chart" | "bar_chart_vertical" | etc. (matches proto ChartType enum)
    )
    library: str | None = None  # "recharts" | "d3" | "react" (for implementation docs)

    # Selection-Specific Metadata
    data_pattern: str | None = None  # "temporal-measure" | "categorical-comparison"
    chart_family: str | None = None  # "evolution" | "comparison" | "distribution"
    priority: str | None = None  # "P0" | "P1" | "P2"
    aliases: list[str] = Field(default_factory=list)  # ["line graph", "trend chart"]

    # Content
    section_path: str  # "Data Viz Bible > Selection > When to Use"
    content: str  # The actual text chunk
    tags: list[str] = Field(default_factory=list)  # From frontmatter tags

    # Reference category (for foundation docs)
    category: str | None = None  # "schema" | "classification" | "index"

    # Timestamps
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Retrieval Models (for semantic search results)
# =============================================================================


class RetrievalStats(BaseModel):
    """Retrieval metadata for semantic search results.

    Used across all context stores for vector search results.
    """

    rank: int = Field(description="1-indexed position in results")
    score: float = Field(description="Similarity score from vector search (0-1)")


class VizDesignRuleResponse(BaseModel):
    """Search result containing VizDesignRule with retrieval stats."""

    rule: VizDesignRule
    stats: RetrievalStats


# =============================================================================
# CoreExternalSourceStore Domain Models
# =============================================================================


class ExternalDataset(BaseModel):
    """Metadata for an external dataset."""

    dataset_id: str = Field(..., description="Unique dataset identifier")
    name: str = Field(..., description="Human-readable dataset name")
    description: str = Field(..., description="Dataset description")
    category: str = Field(
        ..., description="Category: weather, macroeconomic, market, regulatory, etc."
    )
    tags: list[str] = Field(
        default_factory=list, description="Tags for filtering and discovery"
    )
    data_schema: dict[str, Any] = Field(
        default_factory=dict, description="Column definitions and types"
    )
    source: str = Field(..., description="Original data source")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))
    table_name: str = Field(..., description="OLAP table name")
    parquet_uri: str | None = Field(
        default=None, description="Staged parquet file location"
    )
    metadata_embedding_id: str | None = Field(
        default=None, description="Qdrant point ID for metadata"
    )
    version: int = Field(default=1, description="Dataset version")


class QueryResult(BaseModel):
    """Result of a SQL query execution."""

    columns: list[str] = Field(..., description="Column names")
    rows: list[dict[str, Any]] = Field(..., description="Query result rows")
    row_count: int = Field(..., description="Number of rows returned")


class MetadataMatch(BaseModel):
    """Result of semantic metadata search."""

    dataset_id: str = Field(..., description="Dataset identifier")
    score: float = Field(..., description="Similarity score")
    matched_text: str | None = Field(default=None, description="Matched text snippet")


# =============================================================================
# CustomerContextStore Domain Models
# =============================================================================


class SchemaContextRecord(BaseModel):
    """Schema context record with facts grouped by entity."""

    data_schema: dict[str, Any] = Field(..., description="Schema JSON snapshot")
    facts_by_entity: dict[str, list[Fact]] = Field(
        default_factory=dict, description="Map: entity_id -> list of facts"
    )


__all__ = [
    # Proto-Pydantic base
    "ProtoModel",
    # CoreContextStore models
    "KnowledgeNugget",
    "BusinessMetric",
    "IndustryTerm",
    "VizDesignRule",
    # Retrieval models
    "RetrievalStats",
    "VizDesignRuleResponse",
    # CoreExternalSourceStore models
    "ExternalDataset",
    "QueryResult",
    "MetadataMatch",
    # CustomerContextStore models
    "SchemaContextRecord",
]
