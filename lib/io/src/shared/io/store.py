"""Asset store for loading and saving data assets without Dagster dependencies.

This module provides a Dagster-free implementation for reading and writing
data assets using Hive-style partitioning.
"""

import pandas as pd
from upath import UPath

from shared.io.handlers import FileTypeHandler, JSONHandler, ParquetHandler
from shared.io.paths import resolve_asset_path


class AssetStore:
    """Dagster-free asset storage with Hive-style partitioning.

    Handles reading and writing data assets to the filesystem using
    Hive-style partition directories (partition=value/data.parquet).

    Example:
        store = AssetStore('_data/assets')

        # Save partitioned asset
        store.save('bronze/fred/timeseries', df, partition='GDP')

        # Load partitioned asset
        df = store.load('bronze/fred/timeseries', partition='GDP')

        # Save non-partitioned asset (saves to crosswalk/data.parquet)
        store.save('silver/reference/crosswalk', df)

        # S3 storage with credentials
        store = AssetStore('s3://bucket', storage_options={
            'key': 'access_key',
            'secret': 'secret_key',
            'endpoint_url': 'https://s3-compatible-endpoint',
        })
    """

    def __init__(self, base_path: str | UPath, storage_options: dict | None = None):
        """Initialize with base storage path and optional storage options."""
        if isinstance(base_path, str):
            if storage_options:
                base_path = UPath(base_path, **storage_options)
            else:
                base_path = UPath(base_path)
        self._base_path = base_path
        self._storage_options = storage_options
        self._handlers = self._initialize_handlers()

    @staticmethod
    def _initialize_handlers() -> list[FileTypeHandler]:
        """Initialize list of type handlers."""
        return [ParquetHandler(), JSONHandler()]

    def _get_handler_for_type(self, obj_type: type) -> FileTypeHandler:
        """Get the appropriate handler for the given type."""
        for handler in self._handlers:
            if handler.supported_type == obj_type:
                return handler
        raise TypeError(
            f"No handler for type: {obj_type}. "
            f"Supported types: {[h.supported_type for h in self._handlers]}"
        )

    def resolve_path(
        self, asset_path: str, partition_key: str | dict | None = None
    ) -> UPath:
        """Resolve asset path and partition to Hive-style file path.

        Uses shared path resolution for consistency with Dagster IO manager.

        Args:
            asset_path: Slash-separated asset path (e.g., 'bronze/fred/timeseries')
            partition_key: Optional partition key. Can be:
                - str: Single dimension partition (e.g., 'GDP')
                - dict: Multi-dimensional partition
                  (e.g., {'country': 'USA', 'indicator': 'GDP'})

        Returns:
            Hive-style path without file extension
        """
        return resolve_asset_path(self._base_path, asset_path, partition_key)

    def load(
        self, asset_path: str, partition_key: str | dict | None = None
    ) -> pd.DataFrame | dict:
        """Load asset from storage.

        Args:
            asset_path: Slash-separated asset path
            partition_key: Optional partition key (str for single-dim,
                dict for multi-dim)

        Returns:
            Loaded asset data (DataFrame or dict)

        Raises:
            FileNotFoundError: If asset doesn't exist at expected path
        """
        path = self.resolve_path(asset_path, partition_key)

        # Try all supported extensions
        for handler in self._handlers:
            full_path = path.with_suffix(handler.extension)
            if full_path.exists():
                return handler.load(full_path)

        supported_exts = [h.extension for h in self._handlers]
        raise FileNotFoundError(
            f"No asset found at {path} with extensions: {supported_exts}"
        )

    def save(
        self,
        asset_path: str,
        data: pd.DataFrame | dict,
        partition_key: str | dict | None = None,
    ) -> None:
        """Save asset to storage.

        Args:
            asset_path: Slash-separated asset path
            data: Data to save (DataFrame or dict)
            partition_key: Optional partition key (str for single-dim,
                dict for multi-dim)

        Raises:
            TypeError: If data type is not supported
        """
        path = self.resolve_path(asset_path, partition_key)
        path.parent.mkdir(parents=True, exist_ok=True)

        handler = self._get_handler_for_type(type(data))
        handler.dump(data, path.with_suffix(handler.extension))

    def exists(self, asset_path: str, partition_key: str | dict | None = None) -> bool:
        """Check if an asset exists in storage."""
        path = self.resolve_path(asset_path, partition_key)

        for handler in self._handlers:
            if path.with_suffix(handler.extension).exists():
                return True

        return False
