from __future__ import annotations

import io
import json
import os
from pathlib import Path

import duckdb
import pytest

from xlake.stores.config import CustomerDataLakeStoreConfig, DuckDBConfig
from xlake.stores.customer_data_lake_store import create_customer_data_lake_store


def _make_parquet_bytes(tmp_dir: Path) -> bytes:
    tmp_parquet = tmp_dir / "sample.parquet"
    con = duckdb.connect()
    try:
        con.execute(
            f"""
            COPY (
                SELECT 1 AS id, 'a' AS val
                UNION ALL
                SELECT 2 AS id, 'b' AS val
            ) TO '{str(tmp_parquet)}' (FORMAT 'parquet')
            """
        )
    finally:
        con.close()
    data = tmp_parquet.read_bytes()
    return data


def test_add_parquet_dataset_duckdb(tmp_path: Path) -> None:
    # Arrange: create a DuckDB-backed store with a temporary database file
    db_path = tmp_path / "datalake.duckdb"
    cfg = CustomerDataLakeStoreConfig(
        backend="duckdb",
        duckdb=DuckDBConfig(database_path=str(db_path)),
    )
    store = create_customer_data_lake_store(cfg)

    tenant = "tenant1"
    namespace = "sales"
    dataset = "monthly"
    table = "transactions"

    # Prepare parquet bytes using DuckDB
    parquet_bytes = _make_parquet_bytes(tmp_path)

    # Provide a simple schema object for persistence check
    provided_schema = {
        "fields": [
            {"name": "id", "type": "INTEGER"},
            {"name": "val", "type": "VARCHAR"},
        ]
    }

    # Act: add dataset
    fq_ident = store.add_dataset(
        tenant_id=tenant,
        namespace=namespace,
        dataset_name=dataset,
        table_name=table,
        source_type="test",
        file_stream=io.BytesIO(parquet_bytes),
        file_format="parquet",
        schema=provided_schema,
        metadata=None,
    )

    # Assert: view identifier and query results
    assert fq_ident == f"{tenant}__{namespace}__{dataset}.{table}"
    rows = store.execute_query(
        tenant_id=tenant,
        datalake_id="default",
        sql=f'SELECT COUNT(*) AS cnt FROM "{tenant}__{namespace}__{dataset}"."{table}"',
    )
    assert rows and rows[0]["cnt"] == 2

    # Assert: file paths exist relative to the DuckDB database location
    duckdb_dir = Path(os.path.dirname(os.path.abspath(str(db_path))))
    base_dir = duckdb_dir / tenant / namespace / dataset
    data_path = base_dir / f"{table}.parquet"
    schema_path = base_dir / f"{table}.schema.json"

    assert data_path.exists(), f"Expected data file at {data_path}"
    assert schema_path.exists(), f"Expected schema file at {schema_path}"

    # Validate schema contents
    saved_schema = json.loads(schema_path.read_text())
    assert saved_schema == provided_schema

    # Cleanup
    store.close()


def test_execute_query_select_and_ddl() -> None:
    cfg = CustomerDataLakeStoreConfig(
        backend="duckdb",
        duckdb=DuckDBConfig(database_path=":memory:"),
    )
    store = create_customer_data_lake_store(cfg)
    try:
        # SELECT should return rows and columns
        rows = store.execute_query("tenant-x", "dl-1", "select 1 as x, 2 as y")
        assert rows == [{"x": 1, "y": 2}]

        # DDL should be blocked by guardrails
        with pytest.raises(PermissionError):
            _ = store.execute_query("tenant-x", "dl-1", "create table t (x int)")
    finally:
        store.close()


def test_execute_query_blocks_dml() -> None:
    cfg = CustomerDataLakeStoreConfig(
        backend="duckdb",
        duckdb=DuckDBConfig(database_path=":memory:"),
    )
    store = create_customer_data_lake_store(cfg)
    try:
        # DML INSERT should be blocked
        with pytest.raises(PermissionError):
            _ = store.execute_query("tenant-x", "dl-1", "insert into t values (1)")
    finally:
        store.close()


def test_execute_query_allows_with_cte_select() -> None:
    cfg = CustomerDataLakeStoreConfig(
        backend="duckdb",
        duckdb=DuckDBConfig(database_path=":memory:"),
    )
    store = create_customer_data_lake_store(cfg)
    try:
        rows = store.execute_query(
            "tenant-x",
            "dl-1",
            "with c as (select 1 as x) select x, x+1 as y from c",
        )
        assert rows == [{"x": 1, "y": 2}]
    finally:
        store.close()
