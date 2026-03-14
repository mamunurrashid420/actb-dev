"""XLakeClient - Unified facade for the XLake API.

The XLakeClient composes the three high-level clients (Data, Visualization,
Business) and provides a single entry point for all XLake operations.

Example usage:
    ```python
    from xlake.api import create_xlake_client

    # Simple: Create client using environment variables and .env file
    xlake = create_xlake_client()

    # Or with explicit settings (tests, notebooks)
    from xlake.stores.settings import XLakeSettings
    settings = XLakeSettings(local_sqlite_path=":memory:")
    xlake = create_xlake_client(settings=settings)

    # Or with an explicit StoresConfig
    from xlake.stores.config import load_stores_config
    config = load_stores_config()
    xlake = create_xlake_client(config=config)

    # Use the client
    xlake.data.datasets.query("SELECT * FROM sales", tenant=tenant, user=user)
    xlake.visualization.charts.get("chart_001", tenant=tenant, user=user)
    xlake.business.kpi.get_definition("margin_pct", tenant=tenant, user=user)

    # Clean up when done
    xlake.close()

    # Or use as context manager
    with create_xlake_client() as xlake:
        results = xlake.data.datasets.query("SELECT * FROM sales", tenant=tenant, user=user)
    ```
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .business_client import BusinessClient
from .data_client import DataClient
from .visualization_client import VisualizationClient

if TYPE_CHECKING:
    from ..stores import (
        CoreContextStore,
        CoreExternalSourceStore,
        CustomerAppLogicStore,
        CustomerChartStore,
        CustomerContextStore,
        CustomerDataLakeStore,
        CustomerDocStore,
    )
    from ..stores.config import StoresConfig
    from ..stores.settings import XLakeSettings


@dataclass
class XLakeStores:
    """Container for all XLake store instances.

    This dataclass provides a clean way to pass all required stores to the
    XLakeClient without having to specify each one individually.

    Attributes:
        customer_data_lake: CustomerDataLakeStore for data access.
        customer_doc: CustomerDocStore for document management.
        customer_chart: CustomerChartStore for chart/dashboard storage.
        customer_context: CustomerContextStore for schema and facts.
        customer_app_logic: CustomerAppLogicStore for app state.
        core_context: CoreContextStore for global knowledge.
        core_external_source: Optional CoreExternalSourceStore for external data.
    """

    customer_data_lake: CustomerDataLakeStore
    customer_doc: CustomerDocStore
    customer_chart: CustomerChartStore
    customer_context: CustomerContextStore
    customer_app_logic: CustomerAppLogicStore
    core_context: CoreContextStore
    core_external_source: CoreExternalSourceStore | None = None


class XLakeClient:
    """Unified XLake API client.

    The XLakeClient is the main entry point for all XLake operations. It
    composes three high-level clients, each with nested sub-clients:

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

    All operations are scoped by TenantContext and UserContext for proper
    isolation and permissions.

    Example:
        ```python
        xlake = XLakeClient(stores)

        # Data operations
        results = xlake.data.datasets.query(
            "SELECT * FROM sales WHERE region = 'EMEA'",
            tenant=tenant, user=user
        )

        # Visualization operations
        chart = xlake.visualization.charts.get("chart_001", tenant=tenant, user=user)
        dashboard = xlake.visualization.dashboards.create(
            dashboard, tenant=tenant, user=user
        )

        # Business operations
        kpi = xlake.business.kpi.get_definition("margin_pct", tenant=tenant, user=user)
        graph = xlake.business.semantic.graph("sales.revenue", tenant=tenant, user=user)
        ```
    """

    def __init__(self, stores: XLakeStores) -> None:
        """Initialize the XLakeClient.

        Args:
            stores: XLakeStores container with all required store instances.
        """
        self._stores = stores

        # Initialize the three high-level clients
        self.data = DataClient(
            data_lake_store=stores.customer_data_lake,
            doc_store=stores.customer_doc,
            external_store=stores.core_external_source,
        )

        self.visualization = VisualizationClient(
            chart_store=stores.customer_chart,
            core_context_store=stores.core_context,
        )

        self.business = BusinessClient(
            context_store=stores.customer_context,
            app_logic_store=stores.customer_app_logic,
            core_context_store=stores.core_context,
            external_store=stores.core_external_source,
        )

    @property
    def stores(self) -> XLakeStores:
        """Access the underlying stores container.

        Returns:
            The XLakeStores container for direct store access if needed.
        """
        return self._stores

    def close(self) -> None:
        """Close all underlying store connections.

        Call this method when you're done using the XLakeClient to release
        resources properly.
        """
        stores_to_close = [
            self._stores.customer_data_lake,
            self._stores.customer_doc,
            self._stores.customer_chart,
            self._stores.customer_context,
            self._stores.customer_app_logic,
            self._stores.core_context,
            self._stores.core_external_source,
        ]
        for store in stores_to_close:
            if store is not None:
                store.close()

    def __enter__(self) -> XLakeClient:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit with cleanup."""
        self.close()


def create_xlake_client(
    settings: XLakeSettings | None = None,
    config: StoresConfig | None = None,
) -> XLakeClient:
    """Create an XLakeClient with all stores initialized from configuration.

    This factory function handles the initialization of all underlying stores.
    It supports three modes:

    1. **From environment variables** (default):
       Calling ``create_xlake_client()`` with no arguments loads ``XLAKE_*``
       environment variables via :class:`~xlake.stores.settings.XLakeSettings`.

    2. **From explicit settings** (tests, notebooks, DI containers):
       Pass an :class:`~xlake.stores.settings.XLakeSettings` instance.

    3. **From an explicit StoresConfig**:
       Pass a pre-built :class:`~xlake.stores.config.StoresConfig`.

    Args:
        settings: Optional XLakeSettings instance. Used to build the
            StoresConfig if *config* is not provided. Falls back to
            ``get_xlake_settings()`` when both are ``None``.
        config: Optional pre-built StoresConfig. If provided, *settings*
            is ignored and this config is used directly.

    Returns:
        A fully initialized XLakeClient ready for use.

    Example:
        ```python
        # Using environment variables (simplest)
        xlake = create_xlake_client()

        # Using explicit settings (tests, DI)
        from xlake.stores.settings import XLakeSettings
        settings = XLakeSettings(local_sqlite_path=":memory:")
        xlake = create_xlake_client(settings=settings)

        # Using an explicit config
        from xlake.stores.config import load_stores_config
        config = load_stores_config()
        xlake = create_xlake_client(config=config)

        # Use as context manager for automatic cleanup
        with create_xlake_client() as xlake:
            results = xlake.data.datasets.query("SELECT * FROM sales", ...)
        ```

    Environment Variables:
        See :class:`xlake.stores.settings.XLakeSettings` for the full list of
        supported ``XLAKE_*`` environment variables.
    """
    # Import here to avoid circular imports
    from ..stores.config import load_stores_config
    from ..stores.core_context_store import create_core_context_store
    from ..stores.core_external_source_store import create_core_external_source_store
    from ..stores.customer_app_logic_store import create_customer_app_logic_store
    from ..stores.customer_chart_store import create_customer_chart_store
    from ..stores.customer_context_store import create_customer_context_store
    from ..stores.customer_data_lake_store import create_customer_data_lake_store
    from ..stores.customer_doc_store import create_customer_doc_store

    # Load configuration if not provided
    if config is None:
        config = load_stores_config(settings=settings)

    # Create all stores using their respective factory functions
    customer_app_logic = create_customer_app_logic_store(config.customer_app_logic)
    customer_data_lake = create_customer_data_lake_store(config.customer_data_lake)
    customer_doc = create_customer_doc_store(config.customer_doc_store)
    customer_context = create_customer_context_store(config.customer_context_store)
    customer_chart = create_customer_chart_store(config.customer_chart_store)
    core_context = create_core_context_store(config.core_context_store)
    core_external_source = create_core_external_source_store(
        config.core_external_source
    )

    # Create the stores container
    stores = XLakeStores(
        customer_data_lake=customer_data_lake,
        customer_doc=customer_doc,
        customer_chart=customer_chart,
        customer_context=customer_context,
        customer_app_logic=customer_app_logic,
        core_context=core_context,
        core_external_source=core_external_source,
    )

    return XLakeClient(stores)
