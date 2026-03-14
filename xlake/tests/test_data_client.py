"""Tests for DataClient and its sub-clients."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import Mock

import pytest

from xlake.api.data_client import DataClient, DatasetsDataClient, DocumentsDataClient
from xlake.api.models import (
    DatasetMetadata,
    DatasetSchema,
    DocumentInfo,
    DocumentMetadata,
)
from xlake.core import (
    Permissions,
    Preferences,
    TenantContext,
    TenantIdentity,
    UserContext,
)

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
def user_context_no_query() -> UserContext:
    """Create a test UserContext without query permissions."""
    return UserContext(
        user_id="test-user-002",
        tenant_id="test-tenant-001",
        role="viewer",
        permissions=Permissions(
            can_view_fields=["*"],
            can_view_tables=["*"],
            can_view_kpis=["*"],
            can_view_dashboards=["*"],
            can_run_queries=False,
            can_modify_schema=False,
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
    store.execute_query.return_value = [
        {"id": 1, "name": "Product A", "price": 100.0},
        {"id": 2, "name": "Product B", "price": 200.0},
    ]
    store.add_dataset.return_value = "dataset_001"
    return store


@pytest.fixture
def mock_doc_store() -> Mock:
    """Create a mock CustomerDocStore."""
    store = Mock()
    store.list_documents.return_value = ["report.pdf", "data.xlsx", "notes.txt"]
    store.get_metadata.return_value = {
        "filename": "report.pdf",
        "title": "Annual Report 2025",
        "author": "John Doe",
        "category": "finance",
        "page_count": 42,
        "source": "manual_upload",
        "version": "1.0",
        "tags": ["annual", "finance", "report"],
    }
    store.get_document.return_value = (b"PDF content here", "pdf")
    store.save_document.return_value = None
    store.delete_document.return_value = None
    return store


@pytest.fixture
def mock_external_store() -> Mock:
    """Create a mock CoreExternalSourceStore."""
    return Mock()


# =============================================================================
# DatasetsDataClient Tests
# =============================================================================


class TestDatasetsDataClient:
    """Tests for DatasetsDataClient."""

    def test_query_success(
        self,
        mock_data_lake_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test successful SQL query execution."""
        client = DatasetsDataClient(data_lake_store=mock_data_lake_store)

        result = client.query(
            "SELECT * FROM products",
            tenant=tenant_context,
            user=user_context,
        )

        assert len(result) == 2
        assert result[0]["name"] == "Product A"
        assert result[1]["price"] == 200.0
        mock_data_lake_store.execute_query.assert_called_once_with(
            "test-tenant-001", "default", "SELECT * FROM products"
        )

    def test_query_permission_denied(
        self,
        mock_data_lake_store: Mock,
        tenant_context: TenantContext,
        user_context_no_query: UserContext,
    ) -> None:
        """Test query fails without permission."""
        client = DatasetsDataClient(data_lake_store=mock_data_lake_store)

        with pytest.raises(PermissionError, match="User does not have permission"):
            client.query(
                "SELECT * FROM products",
                tenant=tenant_context,
                user=user_context_no_query,
            )

        mock_data_lake_store.execute_query.assert_not_called()

    def test_list_datasets(
        self,
        mock_data_lake_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test listing datasets returns empty list (placeholder)."""
        client = DatasetsDataClient(data_lake_store=mock_data_lake_store)

        result = client.list(tenant=tenant_context, user=user_context)

        assert result == []

    def test_get_schema(
        self,
        mock_data_lake_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting dataset schema returns placeholder."""
        client = DatasetsDataClient(data_lake_store=mock_data_lake_store)

        result = client.get_schema(
            "dataset_001",
            tenant=tenant_context,
            user=user_context,
        )

        assert isinstance(result, DatasetSchema)
        assert result.dataset_id == "dataset_001"
        assert result.columns == []

    def test_get_metadata(
        self,
        mock_data_lake_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting dataset metadata returns placeholder."""
        client = DatasetsDataClient(data_lake_store=mock_data_lake_store)

        result = client.get_metadata(
            "dataset_001",
            tenant=tenant_context,
            user=user_context,
        )

        assert isinstance(result, DatasetMetadata)
        assert result.dataset_id == "dataset_001"
        assert result.name == "dataset_001"

    def test_add_dataset(
        self,
        mock_data_lake_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test adding a new dataset."""
        client = DatasetsDataClient(data_lake_store=mock_data_lake_store)

        metadata = DatasetMetadata(
            dataset_id="",
            name="new_dataset",
            description="Test dataset",
            properties={"namespace": "test", "table_name": "my_table"},
        )
        file_stream = BytesIO(b"parquet data")

        result = client.add(
            metadata=metadata,
            file_stream=file_stream,
            tenant=tenant_context,
            user=user_context,
        )

        assert result == "dataset_001"
        mock_data_lake_store.add_dataset.assert_called_once()

    def test_delete_dataset_not_implemented(
        self,
        mock_data_lake_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test delete raises NotImplementedError."""
        client = DatasetsDataClient(data_lake_store=mock_data_lake_store)

        with pytest.raises(
            NotImplementedError, match="deletion is not yet implemented"
        ):
            client.delete(
                "dataset_001",
                tenant=tenant_context,
                user=user_context,
            )


# =============================================================================
# DocumentsDataClient Tests
# =============================================================================


class TestDocumentsDataClient:
    """Tests for DocumentsDataClient."""

    def test_list_documents(
        self,
        mock_doc_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test listing documents."""
        client = DocumentsDataClient(doc_store=mock_doc_store)

        result = client.list(tenant=tenant_context, user=user_context)

        assert len(result) == 3
        assert isinstance(result[0], DocumentInfo)
        assert result[0].doc_id == "report.pdf"
        assert result[0].filename == "report.pdf"
        mock_doc_store.list_documents.assert_called_once_with(
            tenant_id="test-tenant-001"
        )

    def test_get_document_metadata(
        self,
        mock_doc_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting document metadata."""
        client = DocumentsDataClient(doc_store=mock_doc_store)

        result = client.get(
            "report.pdf",
            tenant=tenant_context,
            user=user_context,
        )

        assert isinstance(result, DocumentMetadata)
        assert result.doc_id == "report.pdf"
        assert result.title == "Annual Report 2025"
        assert result.author == "John Doe"
        assert result.category == "finance"
        assert result.page_count == 42
        assert "annual" in result.tags
        mock_doc_store.get_metadata.assert_called_once_with(
            tenant_id="test-tenant-001", document_name="report.pdf"
        )

    def test_fetch_document_content(
        self,
        mock_doc_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test fetching document content."""
        client = DocumentsDataClient(doc_store=mock_doc_store)

        result = client.fetch(
            "report.pdf",
            tenant=tenant_context,
            user=user_context,
        )

        assert result == b"PDF content here"
        mock_doc_store.get_document.assert_called_once_with(
            tenant_id="test-tenant-001", document_name="report.pdf"
        )

    def test_upload_document(
        self,
        mock_doc_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test uploading a new document."""
        client = DocumentsDataClient(doc_store=mock_doc_store)

        metadata = DocumentMetadata(
            doc_id="",
            filename="new_report.pdf",
            title="New Report",
            author="Jane Doe",
            category="marketing",
            tags=["new", "marketing"],
        )
        file_stream = BytesIO(b"New PDF content")

        result = client.upload(
            metadata=metadata,
            file_stream=file_stream,
            tenant=tenant_context,
            user=user_context,
        )

        assert result == "new_report"
        mock_doc_store.save_document.assert_called_once()
        call_args = mock_doc_store.save_document.call_args
        assert call_args.kwargs["tenant_id"] == "test-tenant-001"
        assert call_args.kwargs["document_name"] == "new_report"
        assert call_args.kwargs["extension"] == "pdf"

    def test_upload_document_no_extension(
        self,
        mock_doc_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test uploading a document without extension."""
        client = DocumentsDataClient(doc_store=mock_doc_store)

        metadata = DocumentMetadata(
            doc_id="",
            filename="readme",
        )
        file_stream = BytesIO(b"README content")

        result = client.upload(
            metadata=metadata,
            file_stream=file_stream,
            tenant=tenant_context,
            user=user_context,
        )

        assert result == "readme"
        call_args = mock_doc_store.save_document.call_args
        assert call_args.kwargs["extension"] == ""

    def test_delete_document(
        self,
        mock_doc_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test deleting a document."""
        client = DocumentsDataClient(doc_store=mock_doc_store)

        client.delete(
            "report.pdf",
            tenant=tenant_context,
            user=user_context,
        )

        mock_doc_store.delete_document.assert_called_once_with(
            tenant_id="test-tenant-001", document_name="report.pdf"
        )


# =============================================================================
# DataClient (Facade) Tests
# =============================================================================


class TestDataClient:
    """Tests for the DataClient facade."""

    def test_initialization(
        self,
        mock_data_lake_store: Mock,
        mock_doc_store: Mock,
        mock_external_store: Mock,
    ) -> None:
        """Test DataClient initializes sub-clients correctly."""
        client = DataClient(
            data_lake_store=mock_data_lake_store,
            doc_store=mock_doc_store,
            external_store=mock_external_store,
        )

        assert hasattr(client, "datasets")
        assert hasattr(client, "documents")
        assert isinstance(client.datasets, DatasetsDataClient)
        assert isinstance(client.documents, DocumentsDataClient)

    def test_datasets_query_via_facade(
        self,
        mock_data_lake_store: Mock,
        mock_doc_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test querying datasets through the facade."""
        client = DataClient(
            data_lake_store=mock_data_lake_store,
            doc_store=mock_doc_store,
        )

        result = client.datasets.query(
            "SELECT * FROM sales",
            tenant=tenant_context,
            user=user_context,
        )

        assert len(result) == 2
        mock_data_lake_store.execute_query.assert_called_once()

    def test_documents_list_via_facade(
        self,
        mock_data_lake_store: Mock,
        mock_doc_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test listing documents through the facade."""
        client = DataClient(
            data_lake_store=mock_data_lake_store,
            doc_store=mock_doc_store,
        )

        result = client.documents.list(tenant=tenant_context, user=user_context)

        assert len(result) == 3
        mock_doc_store.list_documents.assert_called_once()

    def test_initialization_without_external_store(
        self,
        mock_data_lake_store: Mock,
        mock_doc_store: Mock,
    ) -> None:
        """Test DataClient can be initialized without external store."""
        client = DataClient(
            data_lake_store=mock_data_lake_store,
            doc_store=mock_doc_store,
            external_store=None,
        )

        assert client.datasets._external is None
