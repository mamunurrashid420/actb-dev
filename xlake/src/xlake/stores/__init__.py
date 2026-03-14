"""Store abstractions and base types for XLake."""

from __future__ import annotations

# Domain models are canonical in xlake.models - re-export for convenience
from ..models import (  # noqa: E402
    BusinessMetric,
    ExternalDataset,
    IndustryTerm,
    KnowledgeNugget,
    MetadataMatch,
    QueryResult,
    SchemaContextRecord,
    VizDesignRule,
)
from .core_context_store import CoreContextStore, create_core_context_store
from .core_external_source_store import (
    CoreExternalSourceStore,
    create_core_external_source_store,
)
from .customer_app_logic_store import (
    CustomerAppLogicStore,
    create_customer_app_logic_store,
)
from .customer_chart_store import CustomerChartStore, create_customer_chart_store
from .customer_context_store import (
    CustomerContextStore,
    create_customer_context_store,
)
from .customer_data_lake_store import (
    CustomerDataLakeStore,
    create_customer_data_lake_store,
)
from .customer_doc_store import CustomerDocStore, create_customer_doc_store
from .settings import XLakeSettings, get_xlake_settings

__all__ = [
    # Settings
    "XLakeSettings",
    "get_xlake_settings",
    # Core stores
    "CoreContextStore",
    "create_core_context_store",
    "CoreExternalSourceStore",
    "create_core_external_source_store",
    # Customer stores
    "CustomerAppLogicStore",
    "create_customer_app_logic_store",
    "CustomerChartStore",
    "create_customer_chart_store",
    "CustomerContextStore",
    "create_customer_context_store",
    "CustomerDataLakeStore",
    "create_customer_data_lake_store",
    "CustomerDocStore",
    "create_customer_doc_store",
    # Domain models (re-exported from xlake.models)
    "BusinessMetric",
    "ExternalDataset",
    "IndustryTerm",
    "KnowledgeNugget",
    "MetadataMatch",
    "QueryResult",
    "SchemaContextRecord",
    "VizDesignRule",
]
