"""Store setup utilities for XLake notebooks.

Provides helpers for creating in-memory stores and test contexts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xlake.core import TenantContext, UserContext
    from xlake.stores.core_context_store import QdrantSqliteLocalFSCoreContextStore


def create_test_store() -> QdrantSqliteLocalFSCoreContextStore:
    """Create an in-memory CoreContextStore for testing.

    Returns:
        A QdrantSqliteLocalFSCoreContextStore with in-memory backends.
    """
    from xlake.stores.config import QdrantLocalConfig, SqliteConfig
    from xlake.stores.core_context_store import QdrantSqliteLocalFSCoreContextStore

    return QdrantSqliteLocalFSCoreContextStore(
        qdrant_config=QdrantLocalConfig(path=":memory:"),
        sqlite_config=SqliteConfig(database_path=":memory:"),
    )


def create_test_contexts() -> tuple[TenantContext, UserContext]:
    """Create admin TenantContext and UserContext for testing.

    Returns:
        Tuple of (TenantContext, UserContext) with admin permissions
        suitable for writing to CoreContextStore.
    """
    from xlake.core import TenantContext, UserContext
    from xlake.models.tenant import TenantIdentity

    tenant_identity = TenantIdentity(
        tenant_id="actbi",
        tenant_name="ActBI",
        industry="technology",
        region="US",
        timezone="America/New_York",
        locale="en_US",
    )
    tenant = TenantContext(identity=tenant_identity)
    user = UserContext(user_id="admin", tenant_id="actbi", role="admin")

    return tenant, user
