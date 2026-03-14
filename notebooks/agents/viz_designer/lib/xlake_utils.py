"""XLake utilities for visualization designer notebooks.

Provides helpers for creating in-memory XLakeClient instances for testing.
"""

from __future__ import annotations

from xlake.api.client import XLakeClient, create_xlake_client
from xlake.stores.settings import XLakeSettings


def create_xlake_test_client() -> XLakeClient:
    """Create an XLakeClient with all in-memory stores for testing.

    All stores are configured with in-memory backends via XLakeSettings:
    - SQLite stores use ':memory:'
    - DuckDB stores use ':memory:'
    - Qdrant stores use ':memory:'
    - FSSpec stores use '/tmp/' paths

    Returns:
        XLakeClient with all stores initialized in-memory.

    Example:
        ```python
        from lib.xlake_utils import create_xlake_test_client

        xlake_client = create_xlake_test_client()
        # Use the client...
        xlake_client.close()  # Clean up when done
        ```
    """
    settings = XLakeSettings(
        local_sqlite_path=":memory:",
        local_duckdb_path=":memory:",
        local_doc_dir="/tmp/xlake_test_docs",
        local_qdrant_path=":memory:",
        local_context_snapshots_dir="/tmp/xlake_test_context",
        local_chart_data_dir="/tmp/xlake_test_charts",
        core_context_sqlite_path=":memory:",
        core_context_local_dir="/tmp/xlake_test_core",
        core_context_qdrant_local_path=":memory:",
        core_external_duckdb_path=":memory:",
        core_external_local_dir="/tmp/xlake_test_external",
    )

    return create_xlake_client(settings=settings)
