"""XLake Unified API.

The XLake API provides a unified interface for all ActBI agents and the
application to interact with semantic knowledge, schemas, dashboards,
business logic, and real or simulated data.

Three high-level clients with nested sub-clients:

**DataClient** (`xlake.data`):
- `datasets`: Query, list, and manage datasets
- `documents`: List, get, upload, and fetch documents

**VisualizationClient** (`xlake.visualization`):
- `charts`: Create and manage charts
- `dashboards`: Create and manage dashboards
- `stacks`: Create and manage chart stacks
- `rules`: Access visualization design rules

**BusinessClient** (`xlake.business`):
- `kpi`: Define and retrieve KPI/metric definitions
- `schema`: Manage schema semantics and relationships
- `facts`: Store and retrieve business facts
- `semantic`: Semantic search and graph operations
- `conversation`: Conversation context and state

Example:
    ```python
    from xlake.api import create_xlake_client

    # Create the client using environment variables / .env file
    xlake = create_xlake_client()

    # Or with explicit settings (tests, notebooks, DI containers)
    from xlake.stores.settings import XLakeSettings
    settings = XLakeSettings(local_sqlite_path=":memory:")
    xlake = create_xlake_client(settings=settings)

    # Use the client
    xlake.data.datasets.query("SELECT * FROM sales", tenant=tenant, user=user)
    xlake.visualization.charts.get("chart_001", tenant=tenant, user=user)
    xlake.business.kpi.get_definition("margin_pct", tenant=tenant, user=user)

    # Clean up when done
    xlake.close()

    # Or use as a context manager for automatic cleanup
    with create_xlake_client() as xlake:
        results = xlake.data.datasets.query("SELECT * FROM sales", tenant=tenant, user=user)
    ```
"""

from __future__ import annotations

# Settings
from ..stores.settings import XLakeSettings, get_xlake_settings
from .business_client import (
    BusinessClient,
    ConversationBusinessClient,
    FactsBusinessClient,
    KPIBusinessClient,
    SchemaBusinessClient,
    SemanticBusinessClient,
)

# Main client, stores container, and factory function
from .client import XLakeClient, XLakeStores, create_xlake_client

# High-level clients
from .data_client import DataClient, DatasetsDataClient, DocumentsDataClient

# API models
from .models import (
    KPI,
    ActiveState,
    ChartDataSliceInfo,
    # Visualization models
    ChartSummary,
    ColumnInfo,
    ConversationContext,
    DashboardSummary,
    # Data models
    DatasetInfo,
    DatasetMetadata,
    DatasetSchema,
    DocumentInfo,
    DocumentMetadata,
    # Business models
    Entity,
    # Common types
    EntityType,
    FactCreate,
    FactInfo,
    FullSchema,
    GraphNeighbor,
    GraphResult,
    InsightInput,
    KnowledgeObject,
    KPIDefinition,
    KPISummary,
    LineageEdge,
    LineageInfo,
    Relationship,
    SchemaSemantics,
    StackSummary,
    StateUpdate,
)

# Re-export get_version for backwards compatibility
from .public import get_version
from .visualization_client import (
    ChartsVisualizationClient,
    DashboardsVisualizationClient,
    RulesVisualizationClient,
    StacksVisualizationClient,
    VisualizationClient,
)

__all__ = [
    # Main exports
    "XLakeClient",
    "XLakeStores",
    "create_xlake_client",
    # Settings
    "XLakeSettings",
    "get_xlake_settings",
    # High-level clients
    "DataClient",
    "VisualizationClient",
    "BusinessClient",
    # Data sub-clients
    "DatasetsDataClient",
    "DocumentsDataClient",
    # Visualization sub-clients
    "ChartsVisualizationClient",
    "DashboardsVisualizationClient",
    "StacksVisualizationClient",
    "RulesVisualizationClient",
    # Business sub-clients
    "KPIBusinessClient",
    "SchemaBusinessClient",
    "FactsBusinessClient",
    "SemanticBusinessClient",
    "ConversationBusinessClient",
    # Common types
    "EntityType",
    # Data models
    "DatasetInfo",
    "DatasetMetadata",
    "DatasetSchema",
    "ColumnInfo",
    "DocumentInfo",
    "DocumentMetadata",
    "LineageInfo",
    "LineageEdge",
    # Visualization models
    "ChartSummary",
    "DashboardSummary",
    "StackSummary",
    "ChartDataSliceInfo",
    # Business models
    "Entity",
    "Relationship",
    "GraphResult",
    "GraphNeighbor",
    "KPI",
    "KPIDefinition",
    "KPISummary",
    "SchemaSemantics",
    "FullSchema",
    "FactInfo",
    "FactCreate",
    "KnowledgeObject",
    "ConversationContext",
    "ActiveState",
    "InsightInput",
    "StateUpdate",
    # Backwards compatibility
    "get_version",
]
