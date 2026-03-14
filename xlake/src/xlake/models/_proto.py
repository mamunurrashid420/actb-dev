"""Protobuf-backed models re-exported for xlake.models access.

This module bridges generated protobuf code to the xlake.models namespace,
enabling clean imports like:

    from xlake.models import Chart, Dashboard, Insight, OutputSchema
"""

from __future__ import annotations

# ChartDataSlice messages
from xlake.generated.actbi.v1.chart_data_slice_pb2 import ChartDataSlice, RefreshPolicy

# Chart messages
from xlake.generated.actbi.v1.chart_pb2 import (
    Chart,
    ChartType,
    DataMapping,
    DataSeriesClassification,
    Dimension,
    Filter,
    ValueRange,
)

# ChartStack messages
from xlake.generated.actbi.v1.chart_stack_pb2 import ChartStack

# Dashboard messages
from xlake.generated.actbi.v1.dashboard_pb2 import (
    ChartPlacement,
    Dashboard,
    DashboardLayout,
)

# DataBinding messages
from xlake.generated.actbi.v1.data_binding_pb2 import (
    DataBinding,
    DataSource,
    LogicalFilter,
    Projection,
)

# Insights messages and enums
from xlake.generated.actbi.v1.insights_pb2 import (
    # Messages
    AnnotationTarget,
    Highlight,
    # Enums
    HighlightType,
    Insight,
    InsightType,
    Recommendation,
    RecommendationType,
)

# OutputSchema messages and enums
from xlake.generated.actbi.v1.output_schema_pb2 import (
    # Enums
    FieldRole,
    FieldType,
    # Messages
    OutputField,
    OutputSchema,
)

__all__ = [
    # Chart
    "Filter",
    "Dimension",
    "DataMapping",
    "ValueRange",
    "DataSeriesClassification",
    "Chart",
    "ChartType",
    # ChartStack
    "ChartStack",
    # Dashboard
    "ChartPlacement",
    "DashboardLayout",
    "Dashboard",
    # Insights enums
    "HighlightType",
    "InsightType",
    "RecommendationType",
    # Insights messages
    "AnnotationTarget",
    "Highlight",
    "Insight",
    "Recommendation",
    # DataBinding
    "DataSource",
    "LogicalFilter",
    "Projection",
    "DataBinding",
    # OutputSchema
    "FieldType",
    "FieldRole",
    "OutputField",
    "OutputSchema",
    # ChartDataSlice
    "ChartDataSlice",
    "RefreshPolicy",
]
