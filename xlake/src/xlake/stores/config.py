"""Configuration dataclasses for XLake stores.

Store config dataclasses model tagged-union backend selection (e.g. SQLite vs
Supabase). The ``load_*_store_config()`` helpers populate these dataclasses
from :class:`~xlake.stores.settings.XLakeSettings`, which provides type-safe
access to ``XLAKE_*`` environment variables via Pydantic Settings.
"""

from __future__ import annotations

import os
from dataclasses import field as dc_field
from typing import TYPE_CHECKING, Literal

from pydantic import SecretStr
from pydantic.dataclasses import dataclass

if TYPE_CHECKING:
    from .settings import XLakeSettings

Environment = Literal["development", "staging", "production"]


def get_environment() -> Environment:
    """Get the current environment from APP_ENV, defaulting to 'development'.

    This is the single source of truth for environment detection.
    CI/CD pipelines should set APP_ENV to 'staging' or 'production'.

    Returns:
        Environment literal: 'development', 'staging', or 'production'
    """
    env = os.getenv("APP_ENV", "development")
    if env not in ("development", "staging", "production"):
        raise ValueError(
            f"Invalid APP_ENV: {env}. Must be development, staging, or production"
        )
    return env  # type: ignore[return-value]


# ---------------------------
# CustomerAppLogicStore config
# ---------------------------


@dataclass
class SqliteConfig:
    """Configuration for a SQLite-backed store."""

    database_path: str = ":memory:"


@dataclass
class SupabaseConfig:
    """Configuration for a Supabase-backed store."""

    url: str = ""
    api_key: SecretStr = SecretStr("")
    schema: str = "public"


@dataclass
class CustomerAppLogicStoreConfig:
    """Tagged union configuration for CustomerAppLogicStore backends."""

    backend: Literal["sqlite", "supabase"] = "sqlite"
    sqlite: SqliteConfig | None = None
    supabase: SupabaseConfig | None = None


# ---------------------------
# CustomerDataLakeStore config
# ---------------------------


@dataclass
class DuckDBConfig:
    """Configuration for a DuckDB-backed data lake store."""

    database_path: str = "datalake.duckdb"


@dataclass
class ConnectorsRegistryConfig:
    """Configuration for the external connectors registry database."""

    uri: SecretStr = SecretStr("")


@dataclass
class CustomerDataLakeStoreConfig:
    """Tagged union configuration for CustomerDataLakeStore backends."""

    backend: Literal["duckdb", "connectors"] = "duckdb"
    duckdb: DuckDBConfig | None = None
    connectors_registry: ConnectorsRegistryConfig | None = None


# ---------------------------
# CustomerDocStore config
# ---------------------------


@dataclass
class FSSpecLocalDocConfig:
    """Configuration for fsspec-local document store."""

    base_dir: str = "xlake_docs"


@dataclass
class FSSpecObjectDocConfig:
    """Configuration for fsspec object store-backed document store."""

    # Example: "gcs://my-bucket/xlake/docs"
    base_uri: str = ""


@dataclass
class CustomerDocStoreConfig:
    """Tagged union configuration for CustomerDocStore backends."""

    # development -> fsspec_local, staging/production -> connectors (fsspec object via registry)
    backend: Literal["fsspec_local", "connectors"] = "fsspec_local"
    fsspec_local: FSSpecLocalDocConfig | None = None
    # For now, the connectors-backed implementation may require an explicit base_uri
    # until registry resolution is implemented.
    fsspec_object: FSSpecObjectDocConfig | None = None
    connectors_registry: ConnectorsRegistryConfig | None = None


# ---------------------------
# CustomerContextStore config
# ---------------------------


@dataclass
class QdrantLocalConfig:
    """Configuration for an embedded/local Qdrant instance (developer).

    If `path` is ':memory:' or empty/None, tests will use in-memory mode.
    Otherwise, QdrantClient(path=path) will be used with the provided directory.
    """

    path: str | None = None


@dataclass
class QdrantServiceConfig:
    """Configuration for a Qdrant Cloud/service instance (staging/prod)."""

    url: str = ""
    api_key: SecretStr = SecretStr("")


@dataclass
class CustomerContextStoreConfig:
    """Tagged union configuration for CustomerContextStore backends."""

    backend: Literal["qdrant_sqlite_localfs", "qdrant_supabase_cloudfs"] = (
        "qdrant_sqlite_localfs"
    )
    # Qdrant
    qdrant_local: QdrantLocalConfig | None = None
    qdrant_service: QdrantServiceConfig | None = None
    # Relational
    sqlite: SqliteConfig | None = None
    supabase: SupabaseConfig | None = None
    # Files (schema snapshots)
    fsspec_local: FSSpecLocalDocConfig | None = None
    fsspec_object: FSSpecObjectDocConfig | None = None
    # New: schema embedder config object for clearer separation of concerns
    schema_embedder: SchemaEmbedderConfig | None = None


@dataclass
class SchemaEmbedderConfig:
    """Configuration for SchemaEmbedder."""

    strategy: Literal["fields_only", "fields_and_facts"] = "fields_and_facts"
    model: str = "fastembed:BAAI/bge-small-en-v1.5"


# ---------------------------
# CoreContextStore config
# ---------------------------


@dataclass
class CoreContextStoreConfig:
    """Tagged union configuration for CoreContextStore backends.

    The CoreContextStore is ActBI's global semantic memory containing cross-industry
    domain knowledge. It uses separate env vars from Customer stores since Core and
    Customer stores may run on different instances.
    """

    backend: Literal["qdrant_sqlite_localfs", "qdrant_supabase_cloudfs"] = (
        "qdrant_sqlite_localfs"
    )
    # Qdrant
    qdrant_local: QdrantLocalConfig | None = None
    qdrant_service: QdrantServiceConfig | None = None
    # Relational
    sqlite: SqliteConfig | None = None
    supabase: SupabaseConfig | None = None
    # Files (knowledge snapshots)
    fsspec_local: FSSpecLocalDocConfig | None = None
    fsspec_object: FSSpecObjectDocConfig | None = None
    # Embedder config
    embedder: SchemaEmbedderConfig | None = None


# ---------------------------
# CoreExternalSourceStore config
# ---------------------------


@dataclass
class ClickHouseCloudConfig:
    """Configuration for ClickHouse Cloud instance (staging/production)."""

    url: str = ""
    database: str = "default"
    username: str = ""
    password: SecretStr = SecretStr("")


@dataclass
class TinybirdConfig:
    """Configuration for Tinybird instance (staging/production alternative)."""

    url: str = ""
    token: SecretStr = SecretStr("")
    workspace: str = ""


@dataclass
class CoreExternalSourceStoreConfig:
    """Tagged union configuration for CoreExternalSourceStore backends."""

    backend: Literal["duckdb", "clickhouse_cloud", "tinybird"] = "duckdb"
    # OLAP - reuse DuckDBConfig for local development, ClickHouseCloudConfig/TinybirdConfig for production
    duckdb: DuckDBConfig | None = None
    clickhouse_cloud: ClickHouseCloudConfig | None = None
    tinybird: TinybirdConfig | None = None
    # RAG (Qdrant) for metadata
    qdrant_local: QdrantLocalConfig | None = None
    qdrant_service: QdrantServiceConfig | None = None
    # Object Store for staged parquet files
    fsspec_local: FSSpecLocalDocConfig | None = None
    fsspec_object: FSSpecObjectDocConfig | None = None
    # Embedder for metadata
    metadata_embedder: SchemaEmbedderConfig | None = None


# ---------------------------
# CustomerChartStore config
# ---------------------------


@dataclass
class CustomerChartStoreConfig:
    """Tagged union configuration for CustomerChartStore backends."""

    backend: Literal["sqlite", "supabase"] = "sqlite"
    sqlite: SqliteConfig | None = None
    supabase: SupabaseConfig | None = None
    # For JSON data slice storage
    fsspec_local: FSSpecLocalDocConfig | None = None  # dev
    fsspec_object: FSSpecObjectDocConfig | None = None  # staging/prod


@dataclass
class StoresConfig:
    """Top-level stores configuration (master config)."""

    env: Environment = "development"
    customer_app_logic: CustomerAppLogicStoreConfig = dc_field(
        default_factory=CustomerAppLogicStoreConfig
    )
    customer_data_lake: CustomerDataLakeStoreConfig = dc_field(
        default_factory=CustomerDataLakeStoreConfig
    )
    # New: Customer Document Store
    customer_doc_store: CustomerDocStoreConfig = dc_field(  # type: ignore[name-defined]
        default_factory=lambda: CustomerDocStoreConfig()  # type: ignore[name-defined]
    )
    # New: Customer Context Store
    customer_context_store: CustomerContextStoreConfig = dc_field(
        default_factory=lambda: CustomerContextStoreConfig()
    )
    # New: Customer Chart Store
    customer_chart_store: CustomerChartStoreConfig = dc_field(
        default_factory=lambda: CustomerChartStoreConfig()
    )
    # Core Context Store (ActBI global knowledge)
    core_context_store: CoreContextStoreConfig = dc_field(
        default_factory=lambda: CoreContextStoreConfig()
    )
    # Core External Source Store (ActBI global external data)
    core_external_source: CoreExternalSourceStoreConfig = dc_field(
        default_factory=lambda: CoreExternalSourceStoreConfig()
    )


def load_customer_app_logic_store_config(
    env: Environment,
    settings: XLakeSettings,
) -> CustomerAppLogicStoreConfig:
    """Decide CustomerAppLogic store backend from environment and settings."""
    # Infer app logic backend from environment: development -> sqlite, otherwise supabase
    if env == "development":
        return CustomerAppLogicStoreConfig(
            backend="sqlite",
            sqlite=SqliteConfig(database_path=settings.local_sqlite_path),
        )
    return CustomerAppLogicStoreConfig(
        backend="supabase",
        supabase=SupabaseConfig(
            url=settings.customer_supabase_url,
            api_key=settings.customer_supabase_service_key,
            schema=settings.customer_supabase_schema,
        ),
    )


def load_customer_data_lake_store_config(
    env: Environment,
    settings: XLakeSettings,
) -> CustomerDataLakeStoreConfig:
    """Decide CustomerDataLake store backend from environment and settings."""
    # Infer data lake backend from environment: development -> duckdb, otherwise connectors
    if env == "development":
        return CustomerDataLakeStoreConfig(
            backend="duckdb",
            duckdb=DuckDBConfig(database_path=settings.local_duckdb_path),
        )
    return CustomerDataLakeStoreConfig(
        backend="connectors",
        connectors_registry=ConnectorsRegistryConfig(
            uri=settings.customer_connectors_registry_uri,
        ),
    )


def load_customer_doc_store_config(
    env: Environment,
    settings: XLakeSettings,
) -> CustomerDocStoreConfig:
    """Decide CustomerDoc store backend from environment and settings.

    - development: fsspec_local using ``local_doc_dir``
    - staging/production: connectors via registry + object store
    """
    if env == "development":
        return CustomerDocStoreConfig(
            backend="fsspec_local",
            fsspec_local=FSSpecLocalDocConfig(base_dir=settings.local_doc_dir),
        )
    return CustomerDocStoreConfig(
        backend="connectors",
        connectors_registry=ConnectorsRegistryConfig(
            uri=settings.customer_connectors_registry_uri,
        ),
        fsspec_object=FSSpecObjectDocConfig(
            base_uri=settings.customer_doc_object_base_uri,
        ),
    )


def load_customer_context_store_config(
    env: Environment,
    settings: XLakeSettings,
) -> CustomerContextStoreConfig:
    """Decide CustomerContext store backend from environment and settings."""
    embedder = SchemaEmbedderConfig(
        strategy=settings.customer_context_store_schema_embedder,  # type: ignore[arg-type]
        model=settings.customer_embedding_model,
    )

    if env == "development":
        return CustomerContextStoreConfig(
            backend="qdrant_sqlite_localfs",
            qdrant_local=QdrantLocalConfig(path=settings.local_qdrant_path),
            sqlite=SqliteConfig(database_path=settings.local_sqlite_path),
            fsspec_local=FSSpecLocalDocConfig(
                base_dir=settings.local_context_snapshots_dir,
            ),
            schema_embedder=embedder,
        )

    # staging/production
    return CustomerContextStoreConfig(
        backend="qdrant_supabase_cloudfs",
        qdrant_service=QdrantServiceConfig(
            url=settings.customer_qdrant_url,
            api_key=settings.customer_qdrant_api_key,
        ),
        supabase=SupabaseConfig(
            url=settings.customer_supabase_url,
            api_key=settings.customer_supabase_service_key,
            schema=settings.customer_supabase_schema,
        ),
        fsspec_object=FSSpecObjectDocConfig(
            base_uri=settings.customer_context_snapshots_base_uri,
        ),
        schema_embedder=embedder,
    )


def load_customer_chart_store_config(
    env: Environment,
    settings: XLakeSettings,
) -> CustomerChartStoreConfig:
    """Decide CustomerChart store backend from environment and settings.

    - development: SQLite + fsspec local
    - staging/production: Supabase + fsspec object store
    """
    if env == "development":
        return CustomerChartStoreConfig(
            backend="sqlite",
            sqlite=SqliteConfig(database_path=settings.local_sqlite_path),
            fsspec_local=FSSpecLocalDocConfig(base_dir=settings.local_chart_data_dir),
        )

    # staging/production
    return CustomerChartStoreConfig(
        backend="supabase",
        supabase=SupabaseConfig(
            url=settings.customer_supabase_url,
            api_key=settings.customer_supabase_service_key,
            schema=settings.customer_supabase_schema,
        ),
        fsspec_object=FSSpecObjectDocConfig(
            base_uri=settings.customer_chart_data_object_base_uri,
        ),
    )


def load_core_context_store_config(
    env: Environment,
    settings: XLakeSettings,
) -> CoreContextStoreConfig:
    """Decide CoreContext store backend from environment and settings.

    The CoreContextStore uses separate settings fields from Customer stores
    since Core and Customer stores may run on different instances.
    """
    embedder = SchemaEmbedderConfig(
        strategy=settings.core_embedding_strategy,  # type: ignore[arg-type]
        model=settings.core_embedding_model,
    )

    if env == "development":
        return CoreContextStoreConfig(
            backend="qdrant_sqlite_localfs",
            qdrant_local=QdrantLocalConfig(
                path=settings.core_context_qdrant_local_path
            ),
            sqlite=SqliteConfig(database_path=settings.core_context_sqlite_path),
            fsspec_local=FSSpecLocalDocConfig(base_dir=settings.core_context_local_dir),
            embedder=embedder,
        )

    # staging/production
    return CoreContextStoreConfig(
        backend="qdrant_supabase_cloudfs",
        qdrant_service=QdrantServiceConfig(
            url=settings.core_context_qdrant_url,
            api_key=settings.core_context_qdrant_api_key,
        ),
        supabase=SupabaseConfig(
            url=settings.core_supabase_url,
            api_key=settings.core_supabase_service_key,
            schema=settings.core_supabase_schema,
        ),
        fsspec_object=FSSpecObjectDocConfig(
            base_uri=settings.core_context_object_base_uri,
        ),
        embedder=embedder,
    )


def load_core_external_source_store_config(
    env: Environment,
    settings: XLakeSettings,
) -> CoreExternalSourceStoreConfig:
    """Decide CoreExternalSource store backend from environment and settings.

    - development: DuckDB + local Qdrant + local filesystem
    - staging/production: ClickHouse Cloud or Tinybird + Qdrant Cloud + object store
    """
    embedder = SchemaEmbedderConfig(
        strategy=settings.core_embedding_strategy,  # type: ignore[arg-type]
        model=settings.core_embedding_model,
    )

    if env == "development":
        return CoreExternalSourceStoreConfig(
            backend="duckdb",
            duckdb=DuckDBConfig(database_path=settings.core_external_duckdb_path),
            qdrant_local=QdrantLocalConfig(
                path=settings.core_context_qdrant_local_path,
            ),
            fsspec_local=FSSpecLocalDocConfig(
                base_dir=settings.core_external_local_dir,
            ),
            metadata_embedder=embedder,
        )

    # staging/production: prefer Tinybird if configured, else ClickHouse Cloud
    tinybird_url = settings.core_external_tinybird_url
    tinybird_token = settings.core_external_tinybird_token

    if tinybird_url and tinybird_token.get_secret_value():
        return CoreExternalSourceStoreConfig(
            backend="tinybird",
            tinybird=TinybirdConfig(
                url=tinybird_url,
                token=tinybird_token,
                workspace=settings.core_external_tinybird_workspace,
            ),
            qdrant_service=QdrantServiceConfig(
                url=settings.core_context_qdrant_url,
                api_key=settings.core_context_qdrant_api_key,
            ),
            fsspec_object=FSSpecObjectDocConfig(
                base_uri=settings.core_external_object_base_uri,
            ),
            metadata_embedder=embedder,
        )

    # Default to ClickHouse Cloud
    return CoreExternalSourceStoreConfig(
        backend="clickhouse_cloud",
        clickhouse_cloud=ClickHouseCloudConfig(
            url=settings.core_external_clickhouse_url,
            database=settings.core_external_clickhouse_database,
            username=settings.core_external_clickhouse_username,
            password=settings.core_external_clickhouse_password,
        ),
        qdrant_service=QdrantServiceConfig(
            url=settings.core_context_qdrant_url,
            api_key=settings.core_context_qdrant_api_key,
        ),
        fsspec_object=FSSpecObjectDocConfig(
            base_uri=settings.core_external_object_base_uri,
        ),
        metadata_embedder=embedder,
    )


def load_stores_config(settings: XLakeSettings | None = None) -> StoresConfig:
    """Load StoresConfig from :class:`XLakeSettings`.

    If *settings* is ``None``, a default instance is created via
    :func:`get_xlake_settings` (which reads ``XLAKE_*`` environment
    variables and ``.env`` files automatically).

    Args:
        settings: Optional pre-built XLakeSettings. Pass explicitly in
            tests or notebooks; omit for automatic env-based loading.

    Returns:
        Fully populated StoresConfig ready for store creation.

    Environment variables are documented in
    :class:`~xlake.stores.settings.XLakeSettings`.
    """
    if settings is None:
        from .settings import get_xlake_settings

        settings = get_xlake_settings()

    env = get_environment()
    cal_cfg = load_customer_app_logic_store_config(env, settings)
    cdl_cfg = load_customer_data_lake_store_config(env, settings)
    cdocs_cfg = load_customer_doc_store_config(env, settings)
    cctx_cfg = load_customer_context_store_config(env, settings)
    cchart_cfg = load_customer_chart_store_config(env, settings)
    core_ctx_cfg = load_core_context_store_config(env, settings)
    cext_cfg = load_core_external_source_store_config(env, settings)
    return StoresConfig(
        env=env,
        customer_app_logic=cal_cfg,
        customer_data_lake=cdl_cfg,
        customer_doc_store=cdocs_cfg,
        customer_context_store=cctx_cfg,
        customer_chart_store=cchart_cfg,
        core_context_store=core_ctx_cfg,
        core_external_source=cext_cfg,
    )
