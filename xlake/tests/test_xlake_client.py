"""Tests for XLakeClient facade and XLakeStores container."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from xlake.api.business_client import BusinessClient
from xlake.api.client import XLakeClient, XLakeStores, create_xlake_client
from xlake.api.data_client import DataClient
from xlake.api.visualization_client import VisualizationClient
from xlake.core import (
    Permissions,
    Preferences,
    TenantContext,
    TenantIdentity,
    UserContext,
)
from xlake.stores.settings import XLakeSettings

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tenant_context() -> TenantContext:
    """Create a test TenantContext."""
    return TenantContext(
        identity=TenantIdentity(
            tenant_id="test-tenant-001",
            tenant_name="Test Tenant",
            industry="technology",
            region="EU",
            timezone="Europe/Rome",
            locale="en_US",
        ),
    )


@pytest.fixture
def user_context() -> UserContext:
    """Create a test UserContext with full permissions."""
    return UserContext(
        user_id="test-user-001",
        tenant_id="test-tenant-001",
        role="admin",
        permissions=Permissions(
            can_view_fields=["*"],
            can_view_tables=["*"],
            can_view_kpis=["*"],
            can_view_dashboards=["*"],
            can_run_queries=True,
            can_modify_schema=True,
        ),
        preferences=Preferences(
            units="EUR",
            timezone="Europe/Rome",
            verbosity="concise",
        ),
    )


@pytest.fixture
def mock_data_lake_store() -> Mock:
    """Create a mock CustomerDataLakeStore."""
    store = Mock()
    store.execute_query.return_value = [{"id": 1, "value": 100}]
    store.add_dataset.return_value = "dataset_001"
    return store


@pytest.fixture
def mock_doc_store() -> Mock:
    """Create a mock CustomerDocStore."""
    store = Mock()
    store.list_documents.return_value = ["doc1.pdf", "doc2.xlsx"]
    store.get_metadata.return_value = {"filename": "doc1.pdf", "title": "Test Doc"}
    store.get_document.return_value = (b"content", "pdf")
    return store


@pytest.fixture
def mock_chart_store() -> Mock:
    """Create a mock CustomerChartStore."""
    store = Mock()
    chart = Mock()
    chart.id = "chart_001"
    chart.title = "Test Chart"
    chart.version = 1
    store.get_chart.return_value = chart
    store.upsert_chart.return_value = chart

    dashboard = Mock()
    dashboard.id = "dashboard_001"
    dashboard.title = "Test Dashboard"
    store.get_dashboard.return_value = dashboard
    store.upsert_dashboard.return_value = dashboard

    stack = Mock()
    stack.id = "stack_001"
    store.get_chart_stack.return_value = stack
    store.upsert_chart_stack.return_value = stack
    return store


@pytest.fixture
def mock_context_store() -> Mock:
    """Create a mock CustomerContextStore."""
    store = Mock()
    record = Mock()
    record.data_schema = {
        "schema_id": "schema_001",
        "name": "Test Schema",
        "version": 1,
    }
    record.facts_by_entity = {}
    store.get_schema_context.return_value = record
    store.search_context.return_value = [record]
    store.add_fact.return_value = {"fact_id": "fact_001"}
    store.get_entity_facts.return_value = {}
    return store


@pytest.fixture
def mock_app_logic_store() -> Mock:
    """Create a mock CustomerAppLogicStore."""
    store = Mock()
    store.get_conversation.return_value = {
        "thread_id": "thread_001",
        "summary": "Test conversation",
        "messages": [],
        "active_state": {},
    }
    return store


@pytest.fixture
def mock_core_context_store() -> Mock:
    """Create a mock CoreContextStore."""
    store = Mock()
    metric = Mock()
    metric.metric_id = "metric_001"
    metric.name = "Test Metric"
    metric.domain = "test"
    metric.description = "A test metric"
    metric.formula = "a + b"
    metric.formula_type = "sum"
    metric.input_fields = ["a", "b"]
    metric.output_unit = "units"
    metric.tags = []
    metric.lineage = []
    metric.created_at = None
    metric.updated_at = None
    store.search_business_metrics.return_value = [metric]
    store.get_business_metric.return_value = metric
    store.search_knowledge_nuggets.return_value = []

    rule = Mock()
    rule.rule_id = "rule_001"
    rule.document_type = "action-implementation"
    rule.pipeline_stage = "selection"
    rule.chart_type = "line_chart"
    rule.content = "Test rule content"
    store.get_viz_design_rule.return_value = rule
    store.get_blueprint_rule.return_value = rule
    store.get_chart_rules.return_value = [rule]
    store.get_foundation_rules.return_value = [rule]
    store.search_viz_design_rules.return_value = [rule]
    return store


@pytest.fixture
def mock_external_store() -> Mock:
    """Create a mock CoreExternalSourceStore."""
    return Mock()


@pytest.fixture
def xlake_stores(
    mock_data_lake_store: Mock,
    mock_doc_store: Mock,
    mock_chart_store: Mock,
    mock_context_store: Mock,
    mock_app_logic_store: Mock,
    mock_core_context_store: Mock,
    mock_external_store: Mock,
) -> XLakeStores:
    """Create a fully configured XLakeStores container."""
    return XLakeStores(
        customer_data_lake=mock_data_lake_store,
        customer_doc=mock_doc_store,
        customer_chart=mock_chart_store,
        customer_context=mock_context_store,
        customer_app_logic=mock_app_logic_store,
        core_context=mock_core_context_store,
        core_external_source=mock_external_store,
    )


# =============================================================================
# XLakeStores Tests
# =============================================================================


class TestXLakeStores:
    """Tests for XLakeStores container."""

    def test_all_stores_accessible(self, xlake_stores: XLakeStores) -> None:
        """Test all stores are accessible via the container."""
        assert xlake_stores.customer_data_lake is not None
        assert xlake_stores.customer_doc is not None
        assert xlake_stores.customer_chart is not None
        assert xlake_stores.customer_context is not None
        assert xlake_stores.customer_app_logic is not None
        assert xlake_stores.core_context is not None
        assert xlake_stores.core_external_source is not None

    def test_optional_external_store(
        self,
        mock_data_lake_store: Mock,
        mock_doc_store: Mock,
        mock_chart_store: Mock,
        mock_context_store: Mock,
        mock_app_logic_store: Mock,
        mock_core_context_store: Mock,
    ) -> None:
        """Test XLakeStores can be created without external store."""
        stores = XLakeStores(
            customer_data_lake=mock_data_lake_store,
            customer_doc=mock_doc_store,
            customer_chart=mock_chart_store,
            customer_context=mock_context_store,
            customer_app_logic=mock_app_logic_store,
            core_context=mock_core_context_store,
            core_external_source=None,
        )

        assert stores.core_external_source is None


# =============================================================================
# XLakeClient Tests
# =============================================================================


class TestXLakeClient:
    """Tests for XLakeClient facade."""

    def test_initialization(self, xlake_stores: XLakeStores) -> None:
        """Test XLakeClient initializes all sub-clients."""
        client = XLakeClient(xlake_stores)

        assert hasattr(client, "data")
        assert hasattr(client, "visualization")
        assert hasattr(client, "business")
        assert isinstance(client.data, DataClient)
        assert isinstance(client.visualization, VisualizationClient)
        assert isinstance(client.business, BusinessClient)

    def test_data_client_accessible(
        self,
        xlake_stores: XLakeStores,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test data client is accessible and functional."""
        client = XLakeClient(xlake_stores)

        # Test datasets sub-client
        result = client.data.datasets.query(
            "SELECT * FROM test",
            tenant=tenant_context,
            user=user_context,
        )
        assert len(result) == 1

        # Test documents sub-client
        docs = client.data.documents.list(tenant=tenant_context, user=user_context)
        assert len(docs) == 2

    def test_visualization_client_accessible(
        self,
        xlake_stores: XLakeStores,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test visualization client is accessible and functional."""
        client = XLakeClient(xlake_stores)

        # Test charts sub-client
        chart = client.visualization.charts.get(
            "chart_001", tenant=tenant_context, user=user_context
        )
        assert chart.id == "chart_001"

        # Test dashboards sub-client
        dashboard = client.visualization.dashboards.get(
            "dashboard_001", tenant=tenant_context, user=user_context
        )
        assert dashboard.id == "dashboard_001"

        # Test rules sub-client
        rule = client.visualization.rules.get(
            "rule_001", tenant=tenant_context, user=user_context
        )
        assert rule.rule_id == "rule_001"

    def test_business_client_accessible(
        self,
        xlake_stores: XLakeStores,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test business client is accessible and functional."""
        client = XLakeClient(xlake_stores)

        # Test KPI sub-client
        kpis = client.business.kpi.list(tenant=tenant_context, user=user_context)
        assert len(kpis) == 1

        # Test schema sub-client
        schema = client.business.schema.get(
            "schema_001", tenant=tenant_context, user=user_context
        )
        assert schema.schema_id == "schema_001"

        # Test conversation sub-client
        context = client.business.conversation.get_context(
            "thread_001", tenant=tenant_context, user=user_context
        )
        assert context.thread_id == "thread_001"

    def test_chained_operations(
        self,
        xlake_stores: XLakeStores,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test chained operations across clients."""
        client = XLakeClient(xlake_stores)

        # Typical workflow: search for KPIs, get chart, update dashboard
        kpis = client.business.kpi.list(tenant=tenant_context, user=user_context)
        assert len(kpis) > 0

        chart = client.visualization.charts.get(
            "chart_001", tenant=tenant_context, user=user_context
        )
        assert chart is not None

        dashboard = client.visualization.dashboards.get(
            "dashboard_001", tenant=tenant_context, user=user_context
        )
        assert dashboard is not None

    def test_stores_property(self, xlake_stores: XLakeStores) -> None:
        """Test stores property returns the stores container."""
        client = XLakeClient(xlake_stores)

        assert client.stores is xlake_stores


# =============================================================================
# Integration-like Tests
# =============================================================================


class TestXLakeClientIntegration:
    """Integration-like tests for XLakeClient."""

    def test_end_to_end_data_workflow(
        self,
        xlake_stores: XLakeStores,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test end-to-end data access workflow."""
        client = XLakeClient(xlake_stores)

        # 1. List documents
        docs = client.data.documents.list(tenant=tenant_context, user=user_context)
        assert len(docs) > 0

        # 2. Query data
        data = client.data.datasets.query(
            "SELECT * FROM sales",
            tenant=tenant_context,
            user=user_context,
        )
        assert len(data) > 0

    def test_end_to_end_visualization_workflow(
        self,
        xlake_stores: XLakeStores,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test end-to-end visualization workflow."""
        client = XLakeClient(xlake_stores)

        # 1. Search design rules for chart type selection
        rules = client.visualization.rules.search(
            "chart selection", tenant=tenant_context, user=user_context
        )
        assert len(rules) > 0

        # 2. Get existing chart
        chart = client.visualization.charts.get(
            "chart_001", tenant=tenant_context, user=user_context
        )
        assert chart.id == "chart_001"

        # 3. Get dashboard
        dashboard = client.visualization.dashboards.get(
            "dashboard_001", tenant=tenant_context, user=user_context
        )
        assert dashboard.id == "dashboard_001"

    def test_end_to_end_business_workflow(
        self,
        xlake_stores: XLakeStores,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test end-to-end business knowledge workflow."""
        client = XLakeClient(xlake_stores)

        # 1. Search for relevant KPIs
        kpis = client.business.kpi.list(tenant=tenant_context, user=user_context)
        assert len(kpis) > 0

        # 2. Get schema information
        schema = client.business.schema.get(
            "schema_001", tenant=tenant_context, user=user_context
        )
        assert schema is not None

        # 3. Get conversation context
        context = client.business.conversation.get_context(
            "thread_001", tenant=tenant_context, user=user_context
        )
        assert context is not None

    def test_cross_client_workflow(
        self,
        xlake_stores: XLakeStores,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test workflow that spans multiple clients."""
        client = XLakeClient(xlake_stores)

        # Scenario: User asks about revenue metrics and wants to see a chart

        # 1. Business: Get KPI definitions
        kpis = client.business.kpi.list(tenant=tenant_context, user=user_context)

        # 2. Business: Get schema context
        schema = client.business.schema.get(
            "schema_001", tenant=tenant_context, user=user_context
        )

        # 3. Data: Query the data
        data = client.data.datasets.query(
            "SELECT * FROM revenue",
            tenant=tenant_context,
            user=user_context,
        )

        # 4. Visualization: Get chart for display
        chart = client.visualization.charts.get(
            "chart_001", tenant=tenant_context, user=user_context
        )

        # 5. Visualization: Search design rules
        rules = client.visualization.rules.search(
            "visualization", tenant=tenant_context, user=user_context
        )

        # All operations should complete successfully
        assert kpis is not None
        assert schema is not None
        assert data is not None
        assert chart is not None
        assert rules is not None


# =============================================================================
# create_xlake_client Tests
# =============================================================================


class TestCreateXLakeClient:
    """Tests for the create_xlake_client factory function."""

    def test_create_xlake_client_with_settings(self) -> None:
        """Test create_xlake_client works with explicit XLakeSettings.

        This test creates a real client using XLakeSettings with temporary
        directory paths (SQLite, DuckDB, local filesystem stores).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = XLakeSettings(
                local_sqlite_path=os.path.join(tmpdir, "app_logic.db"),
                local_duckdb_path=os.path.join(tmpdir, "datalake.duckdb"),
                local_doc_dir=os.path.join(tmpdir, "docs"),
                local_context_snapshots_dir=os.path.join(tmpdir, "context"),
                local_qdrant_path=":memory:",
                local_chart_data_dir=os.path.join(tmpdir, "chart_data"),
                core_context_sqlite_path=os.path.join(tmpdir, "core_context.db"),
                core_context_local_dir=os.path.join(tmpdir, "core_context"),
                core_context_qdrant_local_path=":memory:",
                core_external_duckdb_path=os.path.join(tmpdir, "core_external.duckdb"),
                core_external_local_dir=os.path.join(tmpdir, "core_external"),
            )

            with patch.dict(os.environ, {"APP_ENV": "development"}, clear=False):
                client = create_xlake_client(settings=settings)

                # Verify client is properly initialized
                assert isinstance(client, XLakeClient)
                assert isinstance(client.data, DataClient)
                assert isinstance(client.visualization, VisualizationClient)
                assert isinstance(client.business, BusinessClient)

                # Verify stores are accessible
                assert client.stores.customer_data_lake is not None
                assert client.stores.customer_doc is not None
                assert client.stores.customer_chart is not None
                assert client.stores.customer_context is not None
                assert client.stores.customer_app_logic is not None
                assert client.stores.core_context is not None
                assert client.stores.core_external_source is not None

                # Clean up
                client.close()

    def test_create_xlake_client_with_explicit_config(self) -> None:
        """Test create_xlake_client works with explicit StoresConfig."""
        from xlake.stores.config import (
            CoreContextStoreConfig,
            CoreExternalSourceStoreConfig,
            CustomerAppLogicStoreConfig,
            CustomerChartStoreConfig,
            CustomerContextStoreConfig,
            CustomerDataLakeStoreConfig,
            CustomerDocStoreConfig,
            DuckDBConfig,
            FSSpecLocalDocConfig,
            QdrantLocalConfig,
            SchemaEmbedderConfig,
            SqliteConfig,
            StoresConfig,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            sqlite_path = os.path.join(tmpdir, "app_logic.db")
            duckdb_path = os.path.join(tmpdir, "datalake.duckdb")
            doc_dir = os.path.join(tmpdir, "docs")
            context_dir = os.path.join(tmpdir, "context")
            chart_dir = os.path.join(tmpdir, "chart_data")
            core_context_path = os.path.join(tmpdir, "core_context.db")
            core_context_dir = os.path.join(tmpdir, "core_context")
            core_external_path = os.path.join(tmpdir, "core_external.duckdb")
            core_external_dir = os.path.join(tmpdir, "core_external")

            config = StoresConfig(
                env="development",
                customer_app_logic=CustomerAppLogicStoreConfig(
                    backend="sqlite",
                    sqlite=SqliteConfig(database_path=sqlite_path),
                ),
                customer_data_lake=CustomerDataLakeStoreConfig(
                    backend="duckdb",
                    duckdb=DuckDBConfig(database_path=duckdb_path),
                ),
                customer_doc_store=CustomerDocStoreConfig(
                    backend="fsspec_local",
                    fsspec_local=FSSpecLocalDocConfig(base_dir=doc_dir),
                ),
                customer_context_store=CustomerContextStoreConfig(
                    backend="qdrant_sqlite_localfs",
                    qdrant_local=QdrantLocalConfig(path=":memory:"),
                    sqlite=SqliteConfig(database_path=sqlite_path),
                    fsspec_local=FSSpecLocalDocConfig(base_dir=context_dir),
                    schema_embedder=SchemaEmbedderConfig(),
                ),
                customer_chart_store=CustomerChartStoreConfig(
                    backend="sqlite",
                    sqlite=SqliteConfig(database_path=sqlite_path),
                    fsspec_local=FSSpecLocalDocConfig(base_dir=chart_dir),
                ),
                core_context_store=CoreContextStoreConfig(
                    backend="qdrant_sqlite_localfs",
                    qdrant_local=QdrantLocalConfig(path=":memory:"),
                    sqlite=SqliteConfig(database_path=core_context_path),
                    fsspec_local=FSSpecLocalDocConfig(base_dir=core_context_dir),
                    embedder=SchemaEmbedderConfig(),
                ),
                core_external_source=CoreExternalSourceStoreConfig(
                    backend="duckdb",
                    duckdb=DuckDBConfig(database_path=core_external_path),
                    qdrant_local=QdrantLocalConfig(path=":memory:"),
                    fsspec_local=FSSpecLocalDocConfig(base_dir=core_external_dir),
                    metadata_embedder=SchemaEmbedderConfig(),
                ),
            )

            client = create_xlake_client(config=config)

            # Verify client is properly initialized
            assert isinstance(client, XLakeClient)

            # Clean up
            client.close()

    def test_create_xlake_client_context_manager(self) -> None:
        """Test create_xlake_client works as context manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = XLakeSettings(
                local_sqlite_path=os.path.join(tmpdir, "app_logic.db"),
                local_duckdb_path=os.path.join(tmpdir, "datalake.duckdb"),
                local_doc_dir=os.path.join(tmpdir, "docs"),
                local_context_snapshots_dir=os.path.join(tmpdir, "context"),
                local_qdrant_path=":memory:",
                local_chart_data_dir=os.path.join(tmpdir, "chart_data"),
                core_context_sqlite_path=os.path.join(tmpdir, "core_context.db"),
                core_context_local_dir=os.path.join(tmpdir, "core_context"),
                core_context_qdrant_local_path=":memory:",
                core_external_duckdb_path=os.path.join(tmpdir, "core_external.duckdb"),
                core_external_local_dir=os.path.join(tmpdir, "core_external"),
            )

            with (
                patch.dict(os.environ, {"APP_ENV": "development"}, clear=False),
                create_xlake_client(settings=settings) as client,
            ):
                assert isinstance(client, XLakeClient)
                # Client should be fully functional within context
                assert client.data is not None
                assert client.visualization is not None
                assert client.business is not None
            # Client is automatically closed after context exits
