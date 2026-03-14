"""XLake shared data models."""

from __future__ import annotations

# Protobuf-backed models (re-exported)
from ._proto import (  # noqa: F401
    # Insights messages
    AnnotationTarget,
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
    DataBinding,
    DataMapping,
    DataSeriesClassification,
    # DataBinding
    DataSource,
    Dimension,
    FieldRole,
    # OutputSchema
    FieldType,
    # Chart
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
    RefreshPolicy,
    ValueRange,
)

# Core domain models (moved from stores)
from .core import (  # noqa: F401
    BusinessMetric,
    # CoreExternalSourceStore models
    ExternalDataset,
    IndustryTerm,
    # CoreContextStore models
    KnowledgeNugget,
    MetadataMatch,
    # Proto-Pydantic base class
    ProtoModel,
    QueryResult,
    # Retrieval models
    RetrievalStats,
    # CustomerContextStore models
    SchemaContextRecord,
    VizDesignRule,
    VizDesignRuleResponse,
)

# Schema models
from .schema import (  # noqa: F401
    DatabaseSchema,
    DataSchema,
    Fact,
    FactCreate,
    FieldSchema,
    TableSchema,
    iter_field_ids,
    normalize_schema_dict_to_model,
    parse_field_id,
    schema_from_json,
    schema_to_json,
    to_field_id,
)

# Tenant/context models
from .tenant import (  # noqa: F401
    ConnectorRef,
    ContextRef,
    NarrativePolicy,
    Permissions,
    Preferences,
    TenantContext,
    TenantIdentity,
    TenantPermissions,
    UserContext,
)

__all__ = [
    # Tenant/context
    "ContextRef",
    "Preferences",
    "Permissions",
    "UserContext",
    "TenantIdentity",
    "TenantPermissions",
    "ConnectorRef",
    "NarrativePolicy",
    "TenantContext",
    # Schema
    "FieldSchema",
    "TableSchema",
    "DatabaseSchema",
    "DataSchema",
    "to_field_id",
    "parse_field_id",
    "schema_from_json",
    "schema_to_json",
    "iter_field_ids",
    "normalize_schema_dict_to_model",
    "Fact",
    "FactCreate",
    # Proto-Pydantic base
    "ProtoModel",
    # Core domain models
    "KnowledgeNugget",
    "BusinessMetric",
    "IndustryTerm",
    "VizDesignRule",
    "ExternalDataset",
    "QueryResult",
    "MetadataMatch",
    "SchemaContextRecord",
    # Retrieval models
    "RetrievalStats",
    "VizDesignRuleResponse",
    # Protobuf models
    "Filter",
    "Dimension",
    "DataMapping",
    "ValueRange",
    "DataSeriesClassification",
    "Chart",
    "ChartType",
    "ChartStack",
    "ChartPlacement",
    "DashboardLayout",
    "Dashboard",
    "HighlightType",
    "InsightType",
    "RecommendationType",
    "AnnotationTarget",
    "Highlight",
    "Insight",
    "Recommendation",
    "DataSource",
    "LogicalFilter",
    "Projection",
    "DataBinding",
    "FieldType",
    "FieldRole",
    "OutputField",
    "OutputSchema",
    "ChartDataSlice",
    "RefreshPolicy",
]
