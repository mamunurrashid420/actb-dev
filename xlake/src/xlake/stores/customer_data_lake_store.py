"""CustomerDataLakeStore protocol, implementations, and factory."""

from __future__ import annotations

import contextlib
import json
import os
import re
from typing import IO, Any, Protocol, runtime_checkable

import fsspec

from .config import (
    ConnectorsRegistryConfig,
    CustomerDataLakeStoreConfig,
    DuckDBConfig,
)


@runtime_checkable
class CustomerDataLakeStore(Protocol):
    """Protocol for executing SQL against a tenant-scoped data lake."""

    def execute_query(
        self, tenant_id: str, datalake_id: str, sql: str
    ) -> list[dict[str, Any]]:  # pragma: no cover
        """Execute a SQL query for the given tenant and data lake, returning rows."""
        ...

    def add_dataset(  # pragma: no cover
        self,
        tenant_id: str,
        namespace: str,
        dataset_name: str,
        table_name: str,
        source_type: str,
        file_stream: IO[bytes],
        file_format: str = "parquet",
        schema: dict | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Add/register a dataset file and expose it as a table/view.

        Steps:
        1) Write the provided file to local filesystem using fsspec under:
           /{tenant_id}/{namespace}/{dataset_name}/{table_name}.{file_format}
           (path is rooted at the DuckDB database directory)
        2) Store the (provided) schema as:
           {table_name}.schema.json in the same directory.
        3) Register the file with the backend (DuckDB) as a parquet-backed view.

        Returns:
            Fully-qualified identifier for the registered table/view.
        """
        ...

    def close(self) -> None:  # pragma: no cover
        """Release resources held by the store (connections, clients)."""
        ...


_DISALLOWED_SQL_KEYWORDS = re.compile(
    r"\b("
    r"insert|update|delete|merge|"
    r"create|alter|drop|truncate|replace|"
    r"copy|attach|detach|grant|revoke|vacuum|analyze|pragma|set|load|export|import"
    r")\b",
    re.IGNORECASE,
)


def assert_read_only_sql(sql: str) -> None:
    """Raise if the provided SQL contains non-read operations.

    Allowed: SELECT statements (optionally using CTEs via WITH).
    Disallowed: DDL/DML like CREATE/INSERT/UPDATE/DELETE/etc.
    """
    # Strip simple SQL comments
    cleaned = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)
    # Split on semicolons to validate each statement (ignore trailing empties)
    statements = [s.strip() for s in cleaned.split(";") if s.strip()]
    if not statements:
        raise PermissionError("Empty SQL is not allowed.")
    for stmt in statements:
        # Quick blocklist check
        if _DISALLOWED_SQL_KEYWORDS.search(stmt):
            raise PermissionError("Only read-only SELECT, VIEW queries are allowed.")
        # Ensure starts with SELECT or WITH
        first_token = re.match(r"^\s*([a-zA-Z_]+)", stmt)
        token = first_token.group(1).lower() if first_token else ""
        if token not in ("select", "with"):
            raise PermissionError("Only read-only SELECT queries are allowed.")
        if token == "with" and "select" not in stmt.lower():
            raise PermissionError("WITH must be used with a read-only SELECT.")


class DuckDBCustomerDataLakeStore(CustomerDataLakeStore):
    """DuckDB-backed data lake store for local development."""

    def __init__(self, config: DuckDBConfig) -> None:
        self._config: DuckDBConfig = config
        self._conn: Any | None = (
            None  # duckdb.DuckDBPyConnection, but avoid hard import in types
        )

    def _ensure_conn(self) -> Any:
        if self._conn is None:
            import duckdb

            self._conn = duckdb.connect(self._config.database_path)
        return self._conn

    @staticmethod
    def _ensure_bytes(content: IO[bytes]) -> bytes:
        data = content.read()
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        raise TypeError("file_stream must be a binary file-like object (IO[bytes])")

    @staticmethod
    def _quote_ident(identifier: str) -> str:
        # Double-quote and escape embedded quotes for DuckDB identifiers
        return '"' + identifier.replace('"', '""') + '"'

    def execute_query(
        self, tenant_id: str, datalake_id: str, sql: str
    ) -> list[dict[str, Any]]:
        """Execute SQL using a shared DuckDB connection.

        Note: `tenant_id` and `datalake_id` parameters are included for interface
        symmetry. In development, these may be used to select schemas or paths
        in future versions.
        """
        assert_read_only_sql(sql)
        conn = self._ensure_conn()
        cursor = conn.execute(sql)
        description = getattr(cursor, "description", None)
        column_names = [d[0] for d in description] if description else []
        rows = cursor.fetchall()
        if not column_names:
            # For DDL / no-result queries, return an empty list
            return []
        return [dict(zip(column_names, row, strict=False)) for row in rows]

    def add_dataset(
        self,
        tenant_id: str,
        namespace: str,
        dataset_name: str,
        table_name: str,
        source_type: str,
        file_stream: IO[bytes],
        file_format: str = "parquet",
        schema: dict | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Write a dataset file to local FS, store schema JSON, and register a DuckDB view.

        The dataset file is stored under a directory rooted at the DuckDB database location:
            {duckdb_dir}/{tenant_id}/{namespace}/{dataset_name}/{table_name}.{file_format}

        The schema is saved alongside as:
            {duckdb_dir}/{tenant_id}/{namespace}/{dataset_name}/{table_name}.schema.json

        Then a DuckDB view is created (or replaced) that reads from the parquet file.

        Returns:
            The fully-qualified identifier for the created view:
                "{tenant_id}__{namespace}__{dataset_name}"."{table_name}"
        """
        fmt = (file_format or "").lower()
        if fmt != "parquet":
            raise ValueError(
                "Only 'parquet' file_format is supported for DuckDB registration."
            )

        # Resolve base directory from DuckDB database path
        duckdb_abs_path = os.path.abspath(self._config.database_path)
        duckdb_dir = os.path.dirname(duckdb_abs_path) or "."

        # Build local filesystem paths (for both fsspec and DuckDB)
        dir_local = os.path.join(duckdb_dir, tenant_id, namespace, dataset_name)
        file_local = os.path.join(dir_local, f"{table_name}.{fmt}")
        schema_local = os.path.join(dir_local, f"{table_name}.schema.json")

        # fsspec prefers explicit scheme; use file://
        dir_uri = f"file://{dir_local}"
        file_uri = f"file://{file_local}"
        schema_uri = f"file://{schema_local}"

        # Ensure directory exists via fsspec fs if supported
        fs, dir_path = fsspec.core.url_to_fs(dir_uri)
        if hasattr(fs, "makedirs"):
            with contextlib.suppress(Exception):
                fs.makedirs(dir_path, exist_ok=True)  # type: ignore[attr-defined]

        # Write the file bytes
        data = self._ensure_bytes(file_stream)
        with fsspec.open(file_uri, mode="wb", overwrite=True) as f:
            f.write(data)

        # Write the schema JSON (use provided or empty object)
        with fsspec.open(schema_uri, mode="w", overwrite=True) as f:
            json.dump(schema or {}, f, indent=2, sort_keys=True)

        # Register with DuckDB by creating a view over the parquet file
        conn = self._ensure_conn()
        schema_ident = f"{tenant_id}__{namespace}__{dataset_name}"
        q_schema = self._quote_ident(schema_ident)
        q_table = self._quote_ident(table_name)

        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {q_schema}")
        # DuckDB does not allow parameters in CREATE VIEW definitions; embed as a literal
        file_literal = file_local.replace("'", "''")
        conn.execute(
            f"CREATE OR REPLACE VIEW {q_schema}.{q_table} AS SELECT * FROM read_parquet('{file_literal}')"
        )

        return f"{schema_ident}.{table_name}"

    def close(self) -> None:
        if self._conn is not None:
            # DuckDB connections have a close method
            self._conn.close()
            self._conn = None


class ConnectorsCustomerDataLakeStore(CustomerDataLakeStore):
    """Connectors-backed data lake store for staging/production (Postgres, BigQuery, etc.)."""

    def __init__(
        self,
        registry: ConnectorsRegistryConfig | None,
    ) -> None:
        self._registry: ConnectorsRegistryConfig | None = registry
        # Real implementation would create a client for the external registry (e.g., Supabase)
        # and resolve per-tenant, per-datalake connector configurations dynamically.

    def execute_query(
        self, tenant_id: str, datalake_id: str, sql: str
    ) -> list[dict[str, Any]]:
        """Execute SQL using the configured connector(s).

        Not implemented yet; choose appropriate backend (e.g., Postgres or BigQuery)
        based on `datalake_id` or configuration routing.
        """
        assert_read_only_sql(sql)
        raise NotImplementedError(
            "ConnectorsCustomerDataLakeStore is not implemented yet."
        )

    def close(self) -> None:
        # HTTP or DB clients may not require explicit close; left as a placeholder.
        return None


def create_customer_data_lake_store(
    config: CustomerDataLakeStoreConfig,
) -> CustomerDataLakeStore:
    """Create a CustomerDataLakeStore instance based on a store-specific config.

    The caller is responsible for choosing the appropriate configuration for the
    active environment.
    """
    if config.backend == "duckdb":
        assert config.duckdb is not None, "duckdb config must be provided"
        return DuckDBCustomerDataLakeStore(config.duckdb)
    if config.backend == "connectors":
        # Registry config may be None for now; runtime resolution to be implemented later.
        return ConnectorsCustomerDataLakeStore(
            registry=config.connectors_registry,
        )
    raise ValueError(f"Unsupported backend: {config.backend}")
