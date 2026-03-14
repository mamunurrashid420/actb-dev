"""Tests for CoreExternalSourceStore."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from xlake.core import Permissions, Preferences, UserContext
from xlake.stores.config import (
    CoreExternalSourceStoreConfig,
    DuckDBConfig,
    FSSpecLocalDocConfig,
    QdrantLocalConfig,
    SchemaEmbedderConfig,
)
from xlake.stores.core_external_source_store import (
    create_core_external_source_store,
)


def _make_parquet_bytes(tmp_dir: Path) -> bytes:
    """Create a sample parquet file."""
    tmp_parquet = tmp_dir / "sample.parquet"
    con = duckdb.connect()
    try:
        con.execute(
            f"""
            COPY (
                SELECT
                    '2024-01-01' AS date,
                    'NYC' AS location,
                    72.5 AS temperature,
                    65.0 AS humidity
                UNION ALL
                SELECT
                    '2024-01-02' AS date,
                    'NYC' AS location,
                    68.0 AS temperature,
                    70.0 AS humidity
            ) TO '{str(tmp_parquet)}' (FORMAT 'parquet')
            """
        )
    finally:
        con.close()
    return tmp_parquet.read_bytes()


def _create_admin_user() -> UserContext:
    """Create an admin user context for testing."""
    return UserContext(
        user_id="admin_user",
        tenant_id="test_tenant",
        role="admin",
        permissions=Permissions(can_modify_schema=True),
        preferences=Preferences(),
    )


def _create_regular_user() -> UserContext:
    """Create a regular user context for testing."""
    return UserContext(
        user_id="regular_user",
        tenant_id="test_tenant",
        role="viewer",
        permissions=Permissions(can_modify_schema=False),
        preferences=Preferences(),
    )


def test_create_store(tmp_path: Path) -> None:
    """Test store creation."""
    db_path = tmp_path / "core_external.duckdb"
    cfg = CoreExternalSourceStoreConfig(
        backend="duckdb",
        duckdb=DuckDBConfig(database_path=str(db_path)),
        qdrant_local=QdrantLocalConfig(path=":memory:"),
        fsspec_local=FSSpecLocalDocConfig(base_dir=str(tmp_path / "data")),
        metadata_embedder=SchemaEmbedderConfig(),
    )
    store = create_core_external_source_store(cfg)
    assert store is not None
    store.close()


def test_register_dataset(tmp_path: Path) -> None:
    """Test registering a new dataset."""
    db_path = tmp_path / "core_external.duckdb"
    data_dir = tmp_path / "data"
    cfg = CoreExternalSourceStoreConfig(
        backend="duckdb",
        duckdb=DuckDBConfig(database_path=str(db_path)),
        qdrant_local=QdrantLocalConfig(path=":memory:"),
        fsspec_local=FSSpecLocalDocConfig(base_dir=str(data_dir)),
        metadata_embedder=SchemaEmbedderConfig(),
    )
    store = create_core_external_source_store(cfg)
    admin_user = _create_admin_user()

    # Create parquet file
    parquet_bytes = _make_parquet_bytes(tmp_path)
    parquet_path = tmp_path / "weather_data.parquet"
    parquet_path.write_bytes(parquet_bytes)

    # Register dataset
    metadata = {
        "name": "NYC Weather Data",
        "description": "Daily weather data for New York City",
        "category": "weather",
        "tags": ["weather", "nyc", "temperature"],
        "data_schema": {
            "date": "DATE",
            "location": "VARCHAR",
            "temperature": "DOUBLE",
            "humidity": "DOUBLE",
        },
        "source": "NOAA",
        "table_name": "nyc_weather",
    }
    dataset_id = store.register_dataset(
        metadata=metadata,
        parquet_uri=f"file://{parquet_path}",
        user=admin_user,
    )

    assert dataset_id is not None
    assert isinstance(dataset_id, str)

    # Verify dataset exists
    dataset = store.get_dataset(dataset_id)
    assert dataset.name == "NYC Weather Data"
    assert dataset.category == "weather"
    assert "weather" in dataset.tags

    store.close()


def test_get_dataset(tmp_path: Path) -> None:
    """Test retrieving a dataset."""
    db_path = tmp_path / "core_external.duckdb"
    data_dir = tmp_path / "data"
    cfg = CoreExternalSourceStoreConfig(
        backend="duckdb",
        duckdb=DuckDBConfig(database_path=str(db_path)),
        qdrant_local=QdrantLocalConfig(path=":memory:"),
        fsspec_local=FSSpecLocalDocConfig(base_dir=str(data_dir)),
        metadata_embedder=SchemaEmbedderConfig(),
    )
    store = create_core_external_source_store(cfg)
    admin_user = _create_admin_user()

    # Register a dataset
    parquet_bytes = _make_parquet_bytes(tmp_path)
    parquet_path = tmp_path / "test.parquet"
    parquet_path.write_bytes(parquet_bytes)

    metadata = {
        "name": "Test Dataset",
        "description": "Test description",
        "category": "test",
        "tags": ["test"],
        "data_schema": {},
        "source": "test",
        "table_name": "test_table",
    }
    dataset_id = store.register_dataset(
        metadata=metadata,
        parquet_uri=f"file://{parquet_path}",
        user=admin_user,
    )

    # Get dataset
    dataset = store.get_dataset(dataset_id)
    assert dataset.dataset_id == dataset_id
    assert dataset.name == "Test Dataset"
    assert dataset.description == "Test description"

    # Test non-existent dataset
    with pytest.raises(KeyError):
        store.get_dataset("non_existent_id")

    store.close()


def test_list_datasets(tmp_path: Path) -> None:
    """Test listing datasets."""
    db_path = tmp_path / "core_external.duckdb"
    data_dir = tmp_path / "data"
    cfg = CoreExternalSourceStoreConfig(
        backend="duckdb",
        duckdb=DuckDBConfig(database_path=str(db_path)),
        qdrant_local=QdrantLocalConfig(path=":memory:"),
        fsspec_local=FSSpecLocalDocConfig(base_dir=str(data_dir)),
        metadata_embedder=SchemaEmbedderConfig(),
    )
    store = create_core_external_source_store(cfg)
    admin_user = _create_admin_user()

    # Register multiple datasets
    parquet_bytes = _make_parquet_bytes(tmp_path)
    for i, category in enumerate(["weather", "market", "weather"]):
        parquet_path = tmp_path / f"dataset_{i}.parquet"
        parquet_path.write_bytes(parquet_bytes)
        metadata = {
            "name": f"Dataset {i}",
            "description": f"Description {i}",
            "category": category,
            "tags": [category, "tag1"],
            "data_schema": {},
            "source": "test",
            "table_name": f"table_{i}",
        }
        store.register_dataset(
            metadata=metadata,
            parquet_uri=f"file://{parquet_path}",
            user=admin_user,
        )

    # List all datasets
    all_datasets = store.list_datasets()
    assert len(all_datasets) == 3

    # Filter by category
    weather_datasets = store.list_datasets(category="weather")
    assert len(weather_datasets) == 2
    assert all(ds.category == "weather" for ds in weather_datasets)

    # Filter by tags
    tagged_datasets = store.list_datasets(tags=["tag1"])
    assert len(tagged_datasets) == 3

    store.close()


def test_search_datasets(tmp_path: Path) -> None:
    """Test semantic search for datasets."""
    db_path = tmp_path / "core_external.duckdb"
    data_dir = tmp_path / "data"
    cfg = CoreExternalSourceStoreConfig(
        backend="duckdb",
        duckdb=DuckDBConfig(database_path=str(db_path)),
        qdrant_local=QdrantLocalConfig(path=":memory:"),
        fsspec_local=FSSpecLocalDocConfig(base_dir=str(data_dir)),
        metadata_embedder=SchemaEmbedderConfig(),
    )
    store = create_core_external_source_store(cfg)
    admin_user = _create_admin_user()

    # Register datasets
    parquet_bytes = _make_parquet_bytes(tmp_path)
    datasets_meta = [
        {
            "name": "NYC Weather",
            "description": "Daily weather data for New York City",
            "category": "weather",
            "tags": ["weather", "nyc"],
            "data_schema": {},
            "source": "NOAA",
            "table_name": "nyc_weather",
        },
        {
            "name": "Stock Prices",
            "description": "Daily stock prices for major indices",
            "category": "market",
            "tags": ["stocks", "finance"],
            "data_schema": {},
            "source": "Yahoo Finance",
            "table_name": "stocks",
        },
    ]
    for meta in datasets_meta:
        parquet_path = tmp_path / f"{meta['table_name']}.parquet"
        parquet_path.write_bytes(parquet_bytes)
        store.register_dataset(
            metadata=meta,
            parquet_uri=f"file://{parquet_path}",
            user=admin_user,
        )

    # Search for weather datasets
    results = store.search_datasets("weather", top_k=5)
    assert len(results) > 0
    assert any(
        "weather" in ds.name.lower() or "weather" in ds.description.lower()
        for ds in results
    )

    # Search with filters
    filtered_results = store.search_datasets(
        "data", filters={"category": "weather"}, top_k=5
    )
    assert all(ds.category == "weather" for ds in filtered_results)

    store.close()


def test_query_dataset(tmp_path: Path) -> None:
    """Test querying a dataset."""
    db_path = tmp_path / "core_external.duckdb"
    data_dir = tmp_path / "data"
    cfg = CoreExternalSourceStoreConfig(
        backend="duckdb",
        duckdb=DuckDBConfig(database_path=str(db_path)),
        qdrant_local=QdrantLocalConfig(path=":memory:"),
        fsspec_local=FSSpecLocalDocConfig(base_dir=str(data_dir)),
        metadata_embedder=SchemaEmbedderConfig(),
    )
    store = create_core_external_source_store(cfg)
    admin_user = _create_admin_user()

    # Register dataset
    parquet_bytes = _make_parquet_bytes(tmp_path)
    parquet_path = tmp_path / "weather.parquet"
    parquet_path.write_bytes(parquet_bytes)

    metadata = {
        "name": "Weather Data",
        "description": "Weather data",
        "category": "weather",
        "tags": ["weather"],
        "data_schema": {},
        "source": "test",
        "table_name": "weather_table",
    }
    dataset_id = store.register_dataset(
        metadata=metadata,
        parquet_uri=f"file://{parquet_path}",
        user=admin_user,
    )

    # Query dataset
    result = store.query_dataset(
        dataset_id=dataset_id,
        sql="SELECT COUNT(*) as cnt FROM external_data.weather_table",
    )
    assert result.row_count == 1
    assert result.columns == ["cnt"]
    assert result.rows[0]["cnt"] == 2

    store.close()


def test_update_dataset_metadata(tmp_path: Path) -> None:
    """Test updating dataset metadata."""
    db_path = tmp_path / "core_external.duckdb"
    data_dir = tmp_path / "data"
    cfg = CoreExternalSourceStoreConfig(
        backend="duckdb",
        duckdb=DuckDBConfig(database_path=str(db_path)),
        qdrant_local=QdrantLocalConfig(path=":memory:"),
        fsspec_local=FSSpecLocalDocConfig(base_dir=str(data_dir)),
        metadata_embedder=SchemaEmbedderConfig(),
    )
    store = create_core_external_source_store(cfg)
    admin_user = _create_admin_user()

    # Register dataset
    parquet_bytes = _make_parquet_bytes(tmp_path)
    parquet_path = tmp_path / "test.parquet"
    parquet_path.write_bytes(parquet_bytes)

    metadata = {
        "name": "Original Name",
        "description": "Original description",
        "category": "test",
        "tags": ["tag1"],
        "data_schema": {},
        "source": "test",
        "table_name": "test_table",
    }
    dataset_id = store.register_dataset(
        metadata=metadata,
        parquet_uri=f"file://{parquet_path}",
        user=admin_user,
    )

    # Update metadata
    store.update_dataset_metadata(
        dataset_id=dataset_id,
        metadata={
            "name": "Updated Name",
            "description": "Updated description",
            "tags": ["tag1", "tag2"],
        },
        user=admin_user,
    )

    # Verify update
    dataset = store.get_dataset(dataset_id)
    assert dataset.name == "Updated Name"
    assert dataset.description == "Updated description"
    assert "tag2" in dataset.tags

    # Test permission check
    regular_user = _create_regular_user()
    with pytest.raises(PermissionError):
        store.update_dataset_metadata(
            dataset_id=dataset_id,
            metadata={"name": "Should Fail"},
            user=regular_user,
        )

    store.close()


def test_delete_dataset(tmp_path: Path) -> None:
    """Test deleting a dataset."""
    db_path = tmp_path / "core_external.duckdb"
    data_dir = tmp_path / "data"
    cfg = CoreExternalSourceStoreConfig(
        backend="duckdb",
        duckdb=DuckDBConfig(database_path=str(db_path)),
        qdrant_local=QdrantLocalConfig(path=":memory:"),
        fsspec_local=FSSpecLocalDocConfig(base_dir=str(data_dir)),
        metadata_embedder=SchemaEmbedderConfig(),
    )
    store = create_core_external_source_store(cfg)
    admin_user = _create_admin_user()

    # Register dataset
    parquet_bytes = _make_parquet_bytes(tmp_path)
    parquet_path = tmp_path / "test.parquet"
    parquet_path.write_bytes(parquet_bytes)

    metadata = {
        "name": "Test Dataset",
        "description": "Test",
        "category": "test",
        "tags": [],
        "data_schema": {},
        "source": "test",
        "table_name": "test_table",
    }
    dataset_id = store.register_dataset(
        metadata=metadata,
        parquet_uri=f"file://{parquet_path}",
        user=admin_user,
    )

    # Delete dataset
    store.delete_dataset(dataset_id, user=admin_user)

    # Verify deletion
    with pytest.raises(KeyError):
        store.get_dataset(dataset_id)

    # Test permission check
    regular_user = _create_regular_user()
    with pytest.raises(PermissionError):
        store.delete_dataset(dataset_id, user=regular_user)

    store.close()


def test_get_dataset_schema(tmp_path: Path) -> None:
    """Test getting dataset schema."""
    db_path = tmp_path / "core_external.duckdb"
    data_dir = tmp_path / "data"
    cfg = CoreExternalSourceStoreConfig(
        backend="duckdb",
        duckdb=DuckDBConfig(database_path=str(db_path)),
        qdrant_local=QdrantLocalConfig(path=":memory:"),
        fsspec_local=FSSpecLocalDocConfig(base_dir=str(data_dir)),
        metadata_embedder=SchemaEmbedderConfig(),
    )
    store = create_core_external_source_store(cfg)
    admin_user = _create_admin_user()

    # Register dataset with schema
    parquet_bytes = _make_parquet_bytes(tmp_path)
    parquet_path = tmp_path / "test.parquet"
    parquet_path.write_bytes(parquet_bytes)

    schema = {
        "date": "DATE",
        "location": "VARCHAR",
        "temperature": "DOUBLE",
    }
    metadata = {
        "name": "Test Dataset",
        "description": "Test",
        "category": "test",
        "tags": [],
        "data_schema": schema,
        "source": "test",
        "table_name": "test_table",
    }
    dataset_id = store.register_dataset(
        metadata=metadata,
        parquet_uri=f"file://{parquet_path}",
        user=admin_user,
    )

    # Get schema
    retrieved_data_schema = store.get_dataset_schema(dataset_id)
    assert retrieved_data_schema == schema

    store.close()


def test_search_metadata(tmp_path: Path) -> None:
    """Test semantic search in metadata."""
    db_path = tmp_path / "core_external.duckdb"
    data_dir = tmp_path / "data"
    cfg = CoreExternalSourceStoreConfig(
        backend="duckdb",
        duckdb=DuckDBConfig(database_path=str(db_path)),
        qdrant_local=QdrantLocalConfig(path=":memory:"),
        fsspec_local=FSSpecLocalDocConfig(base_dir=str(data_dir)),
        metadata_embedder=SchemaEmbedderConfig(),
    )
    store = create_core_external_source_store(cfg)
    admin_user = _create_admin_user()

    # Register dataset
    parquet_bytes = _make_parquet_bytes(tmp_path)
    parquet_path = tmp_path / "weather.parquet"
    parquet_path.write_bytes(parquet_bytes)

    metadata = {
        "name": "Weather Dataset",
        "description": "Daily weather measurements including temperature and humidity",
        "category": "weather",
        "tags": ["weather", "temperature"],
        "data_schema": {},
        "source": "NOAA",
        "table_name": "weather",
    }
    dataset_id = store.register_dataset(
        metadata=metadata,
        parquet_uri=f"file://{parquet_path}",
        user=admin_user,
    )

    # Search metadata
    results = store.search_metadata("temperature", top_k=5)
    assert len(results) > 0
    assert any(r.dataset_id == dataset_id for r in results)

    # Search with dataset filter
    filtered_results = store.search_metadata(
        "temperature", dataset_id=dataset_id, top_k=5
    )
    assert all(r.dataset_id == dataset_id for r in filtered_results)

    store.close()


def test_permission_checks(tmp_path: Path) -> None:
    """Test that only admins can modify datasets."""
    db_path = tmp_path / "core_external.duckdb"
    data_dir = tmp_path / "data"
    cfg = CoreExternalSourceStoreConfig(
        backend="duckdb",
        duckdb=DuckDBConfig(database_path=str(db_path)),
        qdrant_local=QdrantLocalConfig(path=":memory:"),
        fsspec_local=FSSpecLocalDocConfig(base_dir=str(data_dir)),
        metadata_embedder=SchemaEmbedderConfig(),
    )
    store = create_core_external_source_store(cfg)
    regular_user = _create_regular_user()

    parquet_bytes = _make_parquet_bytes(tmp_path)
    parquet_path = tmp_path / "test.parquet"
    parquet_path.write_bytes(parquet_bytes)

    metadata = {
        "name": "Test",
        "description": "Test",
        "category": "test",
        "tags": [],
        "data_schema": {},
        "source": "test",
        "table_name": "test",
    }

    # Regular user cannot register
    with pytest.raises(PermissionError):
        store.register_dataset(
            metadata=metadata,
            parquet_uri=f"file://{parquet_path}",
            user=regular_user,
        )

    store.close()
