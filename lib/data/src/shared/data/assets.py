"""Core asset loading and environment management functionality.

This module provides a simple, programmatic interface for loading and saving
data assets without requiring a Dagster execution context. It handles
environment management, path resolution, and data persistence.

Quick Start
-----------
Load a single asset or partition:

    from shared.data import get

    # Non-partitioned asset
    crosswalk = get('silver/reference/indicator_id_crosswalk')

    # Specific partition
    us_gdp = get('gold/economic/growth/gdp', partition='US')

Environment Management
---------------------
Default environment is 'prod' (read-only). Switch to 'local' for development:

    from shared.data import use_env, env, get

    # Persistent switch
    use_env('local')
    gdp = get('gold/economic/growth/gdp', partition='US')

    # Temporary switch (context manager)
    with env('prod'):
        prod_data = get('gold/economic/growth/gdp', partition='US')
    # Back to previous environment

    # Or specify per-operation
    gdp = get('gold/economic/growth/gdp', partition='US', env='local')

Loading Operations
-----------------
Load single partition:

    from shared.data import get
    us_gdp = get('gold/economic/growth/gdp', partition='US')

Load all partitions:

    from shared.data import get_all
    all_gdp = get_all('gold/economic/growth/gdp')
    # Returns: {'US': DataFrame, 'CN': DataFrame, ...}

Load specific partitions:

    from shared.data import get_many
    gdp_data = get_many('gold/economic/growth/gdp', partitions=['US', 'CN', 'JP'])
    # Returns: {'US': DataFrame, 'CN': DataFrame, 'JP': DataFrame}

Saving Operations
----------------
Save to local environment (requires write permission):

    from shared.data import use_env, save

    use_env('local')  # 'local' allows writes, 'prod' is read-only

    # Non-partitioned asset
    save('silver/reference/new_crosswalk', crosswalk_df)

    # Partitioned asset
    save('gold/economic/growth/gdp', us_gdp_df, partition='US')

Discovery Operations
-------------------
Explore available assets and partitions:

    from shared.data import list_assets, list_partitions, describe, tree, search

    # List all assets
    assets = list_assets()
    # ['silver/reference/indicator_id_crosswalk', 'bronze/fred/timeseries', ...]

    # List partitions for an asset
    partitions = list_partitions('bronze/fred/timeseries')
    # ['GDP', 'UNRATE', 'CPIAUCSL', ...]

    # Get detailed metadata
    info = describe('bronze/fred/timeseries')
    print(info.partition_count)  # Number of partitions
    print(info.schema)           # Column types
    print(info.sample_data)      # Sample row

    # Hierarchical view
    asset_tree = tree()
    # {'bronze': {'fred': {'timeseries': ['GDP', 'UNRATE', ...]}}, ...}

    # Search by keyword
    gdp_assets = search('gdp')
    # ['bronze/fred/timeseries', 'gold/economic/growth/gdp', ...]
"""

import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from upath import UPath

from shared.data.exceptions import (
    AssetNotFoundError,
    EnvironmentNotFoundError,
    EnvironmentPermissionError,
)
from shared.io.store import AssetStore

# Default data path, can be overridden with ACTBI_DATA_PATH environment variable
_DEFAULT_DATA_PATH = "_data/assets"


def _get_data_path() -> str:
    """Get the data path from environment variable or default."""
    return os.environ.get("ACTBI_DATA_PATH", _DEFAULT_DATA_PATH)


@dataclass
class S3Config:
    """S3 storage configuration (not secrets)."""

    endpoint_url: str
    bucket: str
    region: str


@dataclass
class AssetMetadata:
    """Metadata about a data asset."""

    asset_path: str
    is_partitioned: bool
    partition_count: int | None = None
    partitions: list[str] = field(default_factory=list)
    schema: dict[str, str] | None = None  # column_name -> type
    sample_data: dict[str, Any] | None = None
    asset_type: str = "unknown"  # 'dataframe' or 'dict'


@dataclass
class EnvironmentConfig:
    """Configuration for a single environment."""

    name: str
    base_path: str | UPath
    can_write: bool
    description: str
    s3_config: S3Config | None = None  # Only for S3 environments


# Environment configurations - local and prod use filesystem, dev uses Supabase S3
# Credentials for S3 environments are bound at use time (not stored here)
_ENVIRONMENTS: dict[str, EnvironmentConfig] = {
    "local": EnvironmentConfig(
        name="local",
        base_path=_get_data_path(),
        can_write=True,
        description="Local development environment",
    ),
    "dev": EnvironmentConfig(
        name="dev",
        base_path="s3://actbi_pipelines_dev",
        can_write=True,
        description="Development environment (Supabase S3)",
        s3_config=S3Config(
            endpoint_url="https://gwvskyiechyfkqoksqjq.storage.supabase.co/storage/v1/s3",
            bucket="actbi_pipelines_dev",
            region="eu-north-1",
        ),
    ),
    "prod": EnvironmentConfig(
        name="prod",
        base_path=_get_data_path(),
        can_write=False,
        description="Production environment (read-only)",
    ),
}

# Current environment (default to prod for safety)
_current_env: str = "prod"


def get_environment(name: str) -> EnvironmentConfig:
    """Get environment configuration by name."""
    if name not in _ENVIRONMENTS:
        available = list(_ENVIRONMENTS.keys())
        raise EnvironmentNotFoundError(name, available)
    return _ENVIRONMENTS[name]


def list_environments() -> list[str]:
    """List all available environment names."""
    return list(_ENVIRONMENTS.keys())


def current_env() -> str:
    """Get the name of the current environment."""
    return _current_env


def use_env(name: str) -> None:
    """Set the current environment for all subsequent operations."""
    global _current_env

    # Validate environment exists
    get_environment(name)

    _current_env = name


@contextmanager
def env(env_name: str):
    """Temporarily switch to a different environment."""
    old_env = current_env()
    use_env(env_name)
    try:
        yield
    finally:
        use_env(old_env)


class AssetLoader:
    """High-level interface for loading and saving data assets.

    Combines path resolution, environment management, and IO operations
    into a simple API for end users.
    """

    def __init__(self):
        """Initialize the asset loader."""
        # Cache of AssetStore instances per environment
        self._stores: dict[str, AssetStore] = {}

    def _get_store(self, env_name: str | None = None) -> AssetStore:
        """Get or create AssetStore for the specified environment."""
        if env_name is None:
            env_name = current_env()

        # Create store if not cached
        if env_name not in self._stores:
            env_config = get_environment(env_name)
            storage_options = None

            # Build storage_options for S3 environments
            if env_config.s3_config:
                storage_options = {
                    "key": os.environ.get("SUPABASE_S3_ACCESS_KEY"),
                    "secret": os.environ.get("SUPABASE_S3_SECRET_KEY"),
                    "endpoint_url": env_config.s3_config.endpoint_url,
                }

            self._stores[env_name] = AssetStore(env_config.base_path, storage_options)

        return self._stores[env_name]

    def get(
        self, asset_path: str, partition: str | None = None, env: str | None = None
    ) -> pd.DataFrame | dict:
        """Load a single asset or partition."""
        store = self._get_store(env)

        try:
            return store.load(asset_path, partition_key=partition)
        except FileNotFoundError as err:
            raise AssetNotFoundError(
                f"{asset_path}" + (f"[{partition}]" if partition else "")
            ) from err

    def get_all(
        self, asset_path: str, env: str | None = None
    ) -> dict[str, pd.DataFrame | dict]:
        """Load all partitions of a partitioned asset."""
        # Use list_partitions to discover all partitions
        partitions = list_partitions(asset_path, env=env)

        if not partitions:
            raise AssetNotFoundError(f"{asset_path} has no partitions")

        store = self._get_store(env)

        # Load all partitions
        results = {}
        for partition_key in partitions:
            try:
                data = store.load(asset_path, partition_key=partition_key)
                results[partition_key] = data
            except Exception:
                # Skip partitions that can't be loaded
                continue

        if not results:
            raise AssetNotFoundError(asset_path)

        return results

    def get_many(
        self, asset_path: str, partitions: list[str], env: str | None = None
    ) -> dict[str, pd.DataFrame | dict]:
        """Load multiple specific partitions of an asset."""
        store = self._get_store(env)

        # Load each partition
        results = {}
        for partition_key in partitions:
            data = store.load(asset_path, partition_key=partition_key)
            results[partition_key] = data

        return results

    def save(
        self,
        asset_path: str,
        data: pd.DataFrame | dict,
        partition: str | None = None,
        env: str | None = None,
    ) -> None:
        """Save an asset or partition."""
        # Determine target environment
        env_name = env if env is not None else current_env()
        env_config = get_environment(env_name)

        # Check write permissions
        if not env_config.can_write:
            raise EnvironmentPermissionError(
                env_name, f"write operation from {current_env()} environment"
            )

        store = self._get_store(env)
        store.save(asset_path, data, partition_key=partition)


# Global asset loader instance
_asset_loader = AssetLoader()


# Public convenience functions
def get(
    asset_path: str, partition: str | None = None, env: str | None = None
) -> pd.DataFrame | dict:
    """Load a single asset or partition."""
    return _asset_loader.get(asset_path, partition=partition, env=env)


def get_all(asset_path: str, env: str | None = None) -> dict[str, pd.DataFrame | dict]:
    """Load all partitions of a partitioned asset."""
    return _asset_loader.get_all(asset_path, env=env)


def get_many(
    asset_path: str, partitions: list[str], env: str | None = None
) -> dict[str, pd.DataFrame | dict]:
    """Load multiple specific partitions of an asset."""
    return _asset_loader.get_many(asset_path, partitions=partitions, env=env)


def save(
    asset_path: str,
    data: pd.DataFrame | dict,
    partition: str | None = None,
    env: str | None = None,
) -> None:
    """Save an asset or partition."""
    return _asset_loader.save(asset_path, data, partition=partition, env=env)


# Discovery functions


def list_assets(env: str | None = None) -> list[str]:
    """List all available assets in the environment.

    Supports Hive-style partitioned assets (partition=value/data.parquet)
    and non-partitioned assets (asset_name/data.parquet).
    """
    from shared.io.paths import parse_data_file_path

    env_name = env if env is not None else current_env()
    # Use AssetStore to get properly configured base_path (with S3 credentials)
    store = _asset_loader._get_store(env_name)
    base_path = store._base_path

    if not base_path.exists():
        return []

    assets = set()

    # Find all data files and parse their paths
    for path in base_path.rglob("data.*"):
        if path.suffix in [".parquet", ".json"]:
            asset_path, _ = parse_data_file_path(path, base_path)
            if asset_path:
                assets.add(asset_path)

    return sorted(assets)


def list_partitions(asset_path: str, env: str | None = None) -> list[str]:
    """List all partitions for a partitioned asset.

    For Hive-style partitions, returns partition values (e.g., 'GDP', 'US').
    For multi-dimensional partitions, returns combined keys
    (e.g., 'country=USA/indicator=NY.GDP').
    """
    from shared.io.paths import parse_data_file_path

    env_name = env if env is not None else current_env()
    store = _asset_loader._get_store(env_name)
    base_path = store._base_path

    # Parse asset path
    asset_path_clean = asset_path.strip("/")
    parts = [p for p in asset_path_clean.split("/") if p]

    # Build directory path for this asset
    asset_dir = base_path / "/".join(parts)

    # Check for unpartitioned asset (data file directly in asset dir)
    for ext in [".parquet", ".json"]:
        if (asset_dir / f"data{ext}").exists():
            return []

    if not asset_dir.exists():
        raise AssetNotFoundError(asset_path)

    # Find all data files and extract partition keys
    partitions = set()

    for data_file in asset_dir.rglob("data.*"):
        if data_file.suffix not in [".parquet", ".json"]:
            continue

        # Parse the file path to get asset and partition
        parsed_asset, partition_key = parse_data_file_path(data_file, base_path)

        # Only include if it matches our asset and has a partition
        if parsed_asset == asset_path_clean and partition_key is not None:
            # Convert partition key to string for list
            if isinstance(partition_key, dict):
                # Multi-dimensional: rebuild Hive-style path
                sorted_dims = sorted(partition_key.items())
                partition_str = "/".join(f"{k}={v}" for k, v in sorted_dims)
                partitions.add(partition_str)
            else:
                partitions.add(partition_key)

    return sorted(partitions)


def describe(asset_path: str, env: str | None = None) -> AssetMetadata:
    """Get detailed metadata about an asset."""
    # Get partitions
    try:
        partitions = list_partitions(asset_path, env=env)
        is_partitioned = len(partitions) > 0
    except AssetNotFoundError:
        # Try as non-partitioned
        is_partitioned = False
        partitions = []

    metadata = AssetMetadata(
        asset_path=asset_path,
        is_partitioned=is_partitioned,
        partition_count=len(partitions) if is_partitioned else None,
        partitions=partitions[:10] if is_partitioned else [],  # Limit to first 10
    )

    # Try to load sample data to infer schema and type
    try:
        if is_partitioned and partitions:
            # Load first partition as sample
            sample = get(asset_path, partition=partitions[0], env=env)
        else:
            # Load non-partitioned asset
            sample = get(asset_path, env=env)

        # Determine type and extract schema
        if isinstance(sample, pd.DataFrame):
            metadata.asset_type = "dataframe"
            metadata.schema = {col: str(dtype) for col, dtype in sample.dtypes.items()}
            # Sample data (first row as dict)
            if len(sample) > 0:
                metadata.sample_data = sample.iloc[0].to_dict()
        elif isinstance(sample, dict):
            metadata.asset_type = "dict"
            # For dicts, just show keys and types
            metadata.schema = {
                key: type(value).__name__ for key, value in sample.items()
            }
            metadata.sample_data = {
                key: str(value)[:100] for key, value in list(sample.items())[:5]
            }
    except Exception:
        # Couldn't load sample - that's okay
        pass

    return metadata


def tree(env: str | None = None) -> dict[str, Any]:
    """Get hierarchical tree view of all assets."""
    assets = list_assets(env=env)

    tree_dict: dict[str, Any] = {}

    for asset_path in assets:
        parts = asset_path.split("/")
        current = tree_dict

        # Navigate/create nested structure
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                # Last part - check if it has partitions
                try:
                    partitions = list_partitions(asset_path, env=env)
                    current[part] = partitions if partitions else []
                except Exception:
                    current[part] = []
            else:
                # Intermediate part - create dict if needed
                if part not in current:
                    current[part] = {}
                current = current[part]

    return tree_dict


def search(query: str, env: str | None = None) -> list[str]:
    """Search for assets by keyword."""
    all_assets = list_assets(env=env)
    query_lower = query.lower()

    matches = []
    for asset_path in all_assets:
        # Search in path components
        if query_lower in asset_path.lower():
            matches.append(asset_path)
            continue

        # Search in partition names
        try:
            partitions = list_partitions(asset_path, env=env)
            if any(query_lower in p.lower() for p in partitions):
                matches.append(asset_path)
        except Exception:
            pass

    return matches
