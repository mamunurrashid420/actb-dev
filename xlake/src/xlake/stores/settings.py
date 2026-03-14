"""Pydantic Settings for XLake store configuration.

Uses Pydantic Settings for type-safe configuration loaded from
XLAKE_* environment variables with sensible defaults.

Each field maps 1:1 to an existing environment variable. For example,
``local_sqlite_path`` reads ``XLAKE_LOCAL_SQLITE_PATH``.

Example .env::

    XLAKE_LOCAL_SQLITE_PATH=app_logic.db
    XLAKE_LOCAL_DUCKDB_PATH=datalake.duckdb
    XLAKE_CUSTOMER_SUPABASE_URL=https://xxx.supabase.co
    XLAKE_CUSTOMER_SUPABASE_SERVICE_KEY=eyJ...

Example usage::

    # From environment (production / service startup)
    settings = get_xlake_settings()

    # Direct instantiation (tests, notebooks)
    settings = XLakeSettings(
        local_sqlite_path=":memory:",
        local_duckdb_path=":memory:",
    )
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class XLakeSettings(BaseSettings):
    """Complete configuration for all XLake stores.

    Reads all ``XLAKE_*`` environment variables and provides typed,
    validated access. All fields have sensible defaults so that local
    development works out-of-the-box with no ``.env`` file.

    Fields are grouped by concern:
    - ``local_*`` -- local-development backends (SQLite, DuckDB, Qdrant, fsspec)
    - ``customer_*`` -- customer-scoped cloud backends (Supabase, Qdrant Cloud)
    - ``core_*`` -- ActBI global backends (Qdrant Cloud, Supabase, ClickHouse, Tinybird)
    """

    model_config = SettingsConfigDict(
        env_prefix="XLAKE_",
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =========================================================================
    # Local development backends (XLAKE_LOCAL_*)
    # =========================================================================

    local_sqlite_path: str = "app_logic.db"
    """SQLite database path shared by CustomerAppLogic, CustomerContext, and
    CustomerChart stores in development."""

    local_duckdb_path: str = "datalake.duckdb"
    """DuckDB database path for CustomerDataLake store in development."""

    local_doc_dir: str = ".xlake_doc_store"
    """Base directory for local document storage (CustomerDocStore)."""

    local_qdrant_path: str = ":memory:"
    """Qdrant path for local/embedded mode. Use ':memory:' for in-memory."""

    local_context_snapshots_dir: str = ".xlake_context_store"
    """Base directory for local schema snapshots (CustomerContextStore)."""

    local_chart_data_dir: str = ".xlake_chart_data"
    """Base directory for local chart data storage (CustomerChartStore)."""

    # =========================================================================
    # Customer Supabase -- shared across customer stores (XLAKE_CUSTOMER_*)
    # =========================================================================

    customer_supabase_url: str = ""
    """Supabase project URL (staging/production)."""

    customer_supabase_service_key: SecretStr = SecretStr("")
    """Supabase service role key (staging/production)."""

    customer_supabase_schema: str = "public"
    """Postgres schema for customer Supabase tables."""

    # =========================================================================
    # Customer connectors & documents (XLAKE_CUSTOMER_*)
    # =========================================================================

    customer_connectors_registry_uri: SecretStr = SecretStr("")
    """External DB URI holding connectors configuration."""

    customer_doc_object_base_uri: str = ""
    """Object store base URI for documents (e.g. ``gcs://bucket/prefix``)."""

    # =========================================================================
    # Customer context -- Qdrant + embeddings (XLAKE_CUSTOMER_*)
    # =========================================================================

    customer_qdrant_url: str = ""
    """Qdrant service URL for customer context store (staging/production)."""

    customer_qdrant_api_key: SecretStr = SecretStr("")
    """Qdrant API key for customer context store (staging/production)."""

    customer_context_snapshots_base_uri: str = ""
    """Cloud base URI for schema snapshots (e.g. ``gcs://bucket/prefix``)."""

    customer_context_store_schema_embedder: str = "fields_and_facts"
    """Embedding strategy for customer schemas ('fields_only' | 'fields_and_facts')."""

    customer_embedding_model: str = "fastembed:BAAI/bge-small-en-v1.5"
    """Embedding model identifier for customer context store."""

    # =========================================================================
    # Customer chart data (XLAKE_CUSTOMER_*)
    # =========================================================================

    customer_chart_data_object_base_uri: str = ""
    """Object store base URI for chart data (e.g. ``gcs://bucket/prefix``)."""

    # =========================================================================
    # Core context (XLAKE_CORE_CONTEXT_* / XLAKE_CORE_*)
    # =========================================================================

    core_context_qdrant_url: str = ""
    """Qdrant Cloud URL for core context store (staging/production)."""

    core_context_qdrant_api_key: SecretStr = SecretStr("")
    """Qdrant Cloud API key for core context store (staging/production)."""

    core_context_qdrant_local_path: str = ":memory:"
    """Local Qdrant path for core context store (development)."""

    core_context_local_dir: str = ".xlake_core_context"
    """Local FS base dir for core context snapshots (development)."""

    core_context_object_base_uri: str = ""
    """Object store URI for core context snapshots (staging/production)."""

    core_context_sqlite_path: str = "core_context.db"
    """SQLite path for core context store (development)."""

    core_embedding_strategy: str = "fields_and_facts"
    """Embedding strategy for core stores ('fields_only' | 'fields_and_facts')."""

    core_embedding_model: str = "fastembed:BAAI/bge-small-en-v1.5"
    """Embedding model identifier for core stores."""

    core_supabase_url: str = ""
    """Supabase project URL for core stores (staging/production)."""

    core_supabase_service_key: SecretStr = SecretStr("")
    """Supabase service role key for core stores (staging/production)."""

    core_supabase_schema: str = "public"
    """Postgres schema for core Supabase tables."""

    # =========================================================================
    # Core external source (XLAKE_CORE_EXTERNAL_*)
    # =========================================================================

    core_external_duckdb_path: str = "core_external.duckdb"
    """DuckDB database path for core external source store (development)."""

    core_external_local_dir: str = ".xlake_core_external"
    """Base directory for local external data storage (development)."""

    core_external_object_base_uri: str = ""
    """Object store base URI for external data (staging/production)."""

    core_external_clickhouse_url: str = ""
    """ClickHouse Cloud URL (staging/production)."""

    core_external_clickhouse_database: str = "default"
    """ClickHouse database name."""

    core_external_clickhouse_username: str = ""
    """ClickHouse username."""

    core_external_clickhouse_password: SecretStr = SecretStr("")
    """ClickHouse password."""

    core_external_tinybird_url: str = ""
    """Tinybird URL (staging/production alternative to ClickHouse)."""

    core_external_tinybird_token: SecretStr = SecretStr("")
    """Tinybird token."""

    core_external_tinybird_workspace: str = ""
    """Tinybird workspace."""


@lru_cache
def get_xlake_settings() -> XLakeSettings:
    """Get cached XLake settings instance.

    Called once per process. All configuration loaded from ``XLAKE_*``
    environment variables (and optionally ``.env`` / ``.env.local`` files).
    """
    return XLakeSettings()
