"""DataClient for the XLake Unified API.

The DataClient provides access to datasets and raw data only, independent
of business meaning or interpretation. It wraps CustomerDataLakeStore,
CustomerDocStore, and CoreExternalSourceStore (data fetching).

Two sub-clients:
- DatasetsDataClient: Query, list, and manage datasets
- DocumentsDataClient: List, get, upload, and fetch documents
"""

from __future__ import annotations

from typing import IO, TYPE_CHECKING, Any

from ..core import TenantContext, UserContext
from .models import (
    DatasetInfo,
    DatasetMetadata,
    DatasetSchema,
    DocumentInfo,
    DocumentMetadata,
    LineageInfo,
)

if TYPE_CHECKING:
    from ..stores import (
        CoreExternalSourceStore,
        CustomerDataLakeStore,
        CustomerDocStore,
    )


# =============================================================================
# DatasetsDataClient
# =============================================================================


class DatasetsDataClient:
    """Sub-client for dataset operations.

    Accessed via `data.datasets`.

    Backed by:
    - CustomerDataLakeStore (primary data access)
    - CoreExternalSourceStore (external data fetching)
    """

    def __init__(
        self,
        data_lake_store: CustomerDataLakeStore,
        external_store: CoreExternalSourceStore | None = None,
    ) -> None:
        """Initialize the datasets sub-client.

        Args:
            data_lake_store: CustomerDataLakeStore instance for data access.
            external_store: Optional CoreExternalSourceStore for external data.
        """
        self._data_lake = data_lake_store
        self._external = external_store

    def query(
        self,
        sql: str,
        bindings: dict[str, Any] | None = None,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[dict[str, Any]]:
        """Execute a SQL query on real and simulated data via the OLAP engine.

        Args:
            sql: SQL query string (read-only SELECT queries only).
            bindings: Optional parameter bindings (not yet implemented).
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            List of result rows as dictionaries.

        Raises:
            PermissionError: If the user lacks query permissions or SQL is not read-only.
        """
        if not user.permissions.can_run_queries:
            raise PermissionError("User does not have permission to run queries.")

        tenant_id = tenant.identity.tenant_id
        # Use a default datalake_id; in production this would be resolved from context
        datalake_id = "default"

        return self._data_lake.execute_query(tenant_id, datalake_id, sql)

    def list(
        self,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[DatasetInfo]:
        """List available real and simulated datasets.

        Args:
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            List of dataset information summaries.
        """
        # TODO: Implement dataset catalog listing in CustomerDataLakeStore
        # For now, return empty list as placeholder
        return []

    def get_schema(
        self,
        dataset_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> DatasetSchema:
        """Get the schema for a dataset.

        Args:
            dataset_id: Identifier of the dataset.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Dataset schema with column information.

        Raises:
            KeyError: If the dataset is not found.
        """
        # TODO: Implement schema retrieval in CustomerDataLakeStore
        # For now, return a placeholder
        return DatasetSchema(
            dataset_id=dataset_id, columns=[], primary_keys=[], partitions=[]
        )

    def get_metadata(
        self,
        dataset_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> DatasetMetadata:
        """Get extended metadata for a dataset.

        Args:
            dataset_id: Identifier of the dataset.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Dataset metadata including tags and properties.

        Raises:
            KeyError: If the dataset is not found.
        """
        # TODO: Implement metadata retrieval in CustomerDataLakeStore
        return DatasetMetadata(dataset_id=dataset_id, name=dataset_id)

    def get_lineage(
        self,
        dataset_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> LineageInfo:
        """Get lineage information for a dataset.

        Args:
            dataset_id: Identifier of the dataset.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Lineage information with upstream and downstream connections.
        """
        # TODO: Implement lineage retrieval
        return LineageInfo(
            entity_id=dataset_id, entity_type="dataset", upstream=[], downstream=[]
        )

    def add(
        self,
        metadata: DatasetMetadata,
        file_stream: IO[bytes],
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> str:
        """Add/register a new dataset.

        Args:
            metadata: Dataset metadata including name and description.
            file_stream: Binary file stream containing the dataset (parquet format).
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Identifier of the registered dataset.

        Raises:
            PermissionError: If the user lacks write permissions.
        """
        tenant_id = tenant.identity.tenant_id
        namespace = metadata.properties.get("namespace", "default")
        dataset_name = metadata.name
        table_name = metadata.properties.get("table_name", dataset_name)
        source_type = metadata.properties.get("source_type", "uploaded")

        return self._data_lake.add_dataset(
            tenant_id=tenant_id,
            namespace=namespace,
            dataset_name=dataset_name,
            table_name=table_name,
            source_type=source_type,
            file_stream=file_stream,
            file_format="parquet",
            schema=None,
            metadata=metadata.properties,
        )

    def delete(
        self,
        dataset_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        """Delete a dataset.

        Args:
            dataset_id: Identifier of the dataset to delete.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Raises:
            PermissionError: If the user lacks delete permissions.
            KeyError: If the dataset is not found.
        """
        # TODO: Implement dataset deletion in CustomerDataLakeStore
        raise NotImplementedError("Dataset deletion is not yet implemented.")


# =============================================================================
# DocumentsDataClient
# =============================================================================


class DocumentsDataClient:
    """Sub-client for document operations.

    Accessed via `data.documents`.

    Backed by CustomerDocStore.
    """

    def __init__(self, doc_store: CustomerDocStore) -> None:
        """Initialize the documents sub-client.

        Args:
            doc_store: CustomerDocStore instance for document access.
        """
        self._doc_store = doc_store

    def list(
        self,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[DocumentInfo]:
        """List all documents for the tenant.

        Args:
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            List of document information summaries.
        """
        tenant_id = tenant.identity.tenant_id
        doc_names = self._doc_store.list_documents(tenant_id=tenant_id)
        return [
            DocumentInfo(
                doc_id=name,
                filename=name,
            )
            for name in doc_names
        ]

    def get(
        self,
        doc_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> DocumentMetadata:
        """Get metadata for a document.

        Args:
            doc_id: Identifier of the document (document_name).
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Document metadata.

        Raises:
            FileNotFoundError: If the document is not found.
        """
        tenant_id = tenant.identity.tenant_id
        metadata = self._doc_store.get_metadata(
            tenant_id=tenant_id, document_name=doc_id
        )
        return DocumentMetadata(
            doc_id=doc_id,
            filename=metadata.get("filename", doc_id),
            title=metadata.get("title"),
            author=metadata.get("author"),
            category=metadata.get("category"),
            page_count=metadata.get("page_count"),
            source=metadata.get("source"),
            version=metadata.get("version"),
            tags=metadata.get("tags", []),
            created_at=metadata.get("created_at"),
            updated_at=metadata.get("updated_at"),
        )

    def fetch(
        self,
        doc_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> bytes:
        """Fetch the raw content of a document.

        Args:
            doc_id: Identifier of the document (document_name).
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Raw bytes of the document content.

        Raises:
            FileNotFoundError: If the document is not found.
        """
        tenant_id = tenant.identity.tenant_id
        content, _extension = self._doc_store.get_document(
            tenant_id=tenant_id, document_name=doc_id
        )
        return content

    def upload(
        self,
        metadata: DocumentMetadata,
        file_stream: IO[bytes],
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> str:
        """Upload a new document.

        Args:
            metadata: Document metadata including filename.
            file_stream: Binary file stream containing the document.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Identifier (document_name) of the uploaded document.

        Raises:
            PermissionError: If the user lacks upload permissions.
        """
        tenant_id = tenant.identity.tenant_id
        # Extract extension from filename
        filename = metadata.filename
        extension = filename.split(".")[-1] if "." in filename else ""
        document_name = filename.rsplit(".", 1)[0] if "." in filename else filename

        self._doc_store.save_document(
            tenant_id=tenant_id,
            document_name=document_name,
            extension=extension,
            content=file_stream,
            metadata={
                "filename": metadata.filename,
                "title": metadata.title,
                "author": metadata.author,
                "category": metadata.category,
                "source": metadata.source,
                "tags": metadata.tags,
            },
        )
        return document_name

    def delete(
        self,
        doc_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        """Delete a document.

        Args:
            doc_id: Identifier of the document (document_name) to delete.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Raises:
            PermissionError: If the user lacks delete permissions.
            FileNotFoundError: If the document is not found.
        """
        tenant_id = tenant.identity.tenant_id
        self._doc_store.delete_document(tenant_id=tenant_id, document_name=doc_id)


# =============================================================================
# DataClient (Facade)
# =============================================================================


class DataClient:
    """High-level data access client for XLake.

    Provides access to datasets and documents independent of business
    meaning or interpretation.

    Sub-clients:
    - `datasets`: Query, list, and manage datasets
    - `documents`: List, get, upload, and fetch documents

    Example:
        ```python
        data = DataClient(stores)
        results = data.datasets.query("SELECT * FROM sales", tenant=tenant, user=user)
        docs = data.documents.list(tenant=tenant, user=user)
        ```
    """

    def __init__(
        self,
        data_lake_store: CustomerDataLakeStore,
        doc_store: CustomerDocStore,
        external_store: CoreExternalSourceStore | None = None,
    ) -> None:
        """Initialize the DataClient.

        Args:
            data_lake_store: CustomerDataLakeStore instance.
            doc_store: CustomerDocStore instance.
            external_store: Optional CoreExternalSourceStore instance.
        """
        self.datasets = DatasetsDataClient(
            data_lake_store=data_lake_store,
            external_store=external_store,
        )
        self.documents = DocumentsDataClient(
            doc_store=doc_store,
        )
