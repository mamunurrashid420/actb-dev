import dagster as dg
import pandas as pd
import polars as pl
from upath import UPath

from shared.io.handlers import (
    FileTypeHandler,
    JSONHandler,
    PandasJSONEncoder,
    ParquetDatasetHandler,
    ParquetHandler,
    StreamingParquetHandler,
)
from shared.io.paths import SHARD_GLOB_PATTERN, resolve_asset_path
from shared.io.streaming import StreamingParquetSource

# Re-export handlers for backward compatibility
__all__ = [
    "FileSystemIOManager",
    "FileTypeHandler",
    "JSONHandler",
    "PandasJSONEncoder",
    "ParquetDatasetHandler",
    "ParquetHandler",
]


class FileSystemIOManager(dg.UPathIOManager):
    """IO manager that stores assets to the filesystem.

    Automatically handles different data types:
    - pandas DataFrames → Parquet files (.parquet)
    - polars LazyFrames → Parquet datasets (directories of sharded .parquet files)
    - Dicts → JSON files (.json)

    Extends UPathIOManager for easy cloud storage support (GCS, S3) in the future.

    Args:
        base_path: Base directory for asset storage. Default: '_data/assets'
        rows_per_shard: Max rows per parquet shard for LazyFrame writes. Default: 8,192,000 (~128 MB)
    """

    def __init__(
        self,
        base_path: UPath | str | None = None,
        rows_per_shard: int = 8_192_000,
    ):
        """Initialize with base path and type handlers."""
        if base_path is None:
            base_path = "_data/assets"
        if isinstance(base_path, str):
            base_path = UPath(base_path)
        self.rows_per_shard = rows_per_shard
        super().__init__(base_path=base_path)

    def _initialize_handlers(self) -> list[FileTypeHandler]:
        """Initialize list of type handlers."""
        return [
            ParquetHandler(),
            ParquetDatasetHandler(rows_per_shard=self.rows_per_shard),
            StreamingParquetHandler(),
            JSONHandler(),
        ]

    @property
    def _handlers(self) -> list[FileTypeHandler]:
        """Get type handlers (cached as instance attribute)."""
        if not hasattr(self, "_cached_handlers"):
            self._cached_handlers = self._initialize_handlers()
        return self._cached_handlers

    def _get_handler_for_type(self, obj_type: type) -> FileTypeHandler:
        """Get the appropriate handler for the given type."""
        for handler in self._handlers:
            if handler.supported_type == obj_type:
                return handler
        raise TypeError(
            f"No handler for type: {obj_type}. "
            f"Supported types: {[h.supported_type for h in self._handlers]}"
        )

    def _get_path_without_extension(
        self, context: dg.InputContext | dg.OutputContext
    ) -> UPath:
        """Generate Hive-style hierarchical file path for assets.

        Uses shared path resolution for consistency with AssetStore.
        Hive-standard patterns:
        - Partitioned: {asset}/partition=value/data
        - Unpartitioned: {asset}/data
        """
        asset_path_parts = context.asset_key.path
        partition_key = self._normalize_partition_key(self._get_partition_key(context))
        return resolve_asset_path(self._base_path, asset_path_parts, partition_key)

    def _normalize_partition_key(self, partition_key) -> str | dict | None:
        """Convert Dagster partition key to string or dict for shared path resolution.

        Dagster's MultiPartitionKey has a keys_by_dimension attribute that needs
        to be converted to a plain dict for the shared path resolution function.
        """
        if partition_key is None:
            return None
        # Check if multi-dimensional (Dagster MultiPartitionKey)
        if hasattr(partition_key, "keys_by_dimension"):
            return dict(partition_key.keys_by_dimension)
        return partition_key

    def get_path_for_partition(
        self,
        context: dg.InputContext | dg.OutputContext,
        path: UPath,
        partition: str,
    ) -> UPath:
        """Override to prevent double-partitioning.

        Our _get_path_without_extension already builds Hive-style paths with
        partition info (e.g., partition=USA/data). The parent class would add
        the partition key again. We return the path unchanged.
        """
        return path

    def _get_partition_key(
        self, context: dg.InputContext | dg.OutputContext
    ) -> str | None:
        """Extract appropriate partition key from context.

        For both Input and Output contexts, use has_asset_partitions to check if
        the ASSET ITSELF is partitioned (not just if the run has a partition key).
        This correctly handles unpartitioned assets in partitioned job runs.
        """
        if isinstance(context, dg.InputContext):
            # Check if the INPUT ASSET has partitions (not the consuming asset)
            if context.has_asset_partitions:
                return context.asset_partition_key
            return None
        elif isinstance(context, dg.OutputContext) and context.has_asset_partitions:
            # Use has_asset_partitions, NOT has_partition_key
            # has_partition_key can be True for unpartitioned assets in partitioned jobs
            return context.partition_key
        return None

    def dump_to_path(
        self,
        context: dg.OutputContext,
        obj: pd.DataFrame | pl.LazyFrame | StreamingParquetSource | dict,
        path: UPath,
    ) -> None:
        """Save object using appropriate type handler."""
        path.parent.mkdir(parents=True, exist_ok=True)
        asset_dir = path.parent

        # Warn if persisting empty DataFrame (defense-in-depth validation)
        if isinstance(obj, pd.DataFrame) and len(obj) == 0:
            context.log.warning(
                f"Persisting empty DataFrame for asset {context.asset_key}. "
                f"This may indicate a data quality issue or validation gap."
            )

        handler = self._get_handler_for_type(type(obj))
        if isinstance(obj, pl.LazyFrame | StreamingParquetSource):
            # Clean up old single-file format before writing sharded
            old_single_file = asset_dir / "data.parquet"
            if old_single_file.exists():
                old_single_file.unlink()
                context.log.info(f"Removed old single-file format: {old_single_file}")

            # For LazyFrame and StreamingParquetSource, dump to parent directory (dataset pattern)
            handler.dump(obj, asset_dir)
            context.log.info(
                f"Saved {type(obj).__name__} to parquet dataset at {asset_dir}"
            )
        else:
            # Clean up old sharded format before writing single file
            old_shards = list(asset_dir.glob(SHARD_GLOB_PATTERN))
            for shard in old_shards:
                shard.unlink()
            if old_shards:
                context.log.info(f"Removed {len(old_shards)} old shard files")

            handler.dump(obj, path.with_suffix(handler.extension))
            context.log.info(f"Saved {type(obj).__name__} to {path}{handler.extension}")

    def load_from_path(
        self, context: dg.InputContext, path: UPath
    ) -> pd.DataFrame | pl.LazyFrame | dict:
        """Load object using appropriate type handler.

        Note: context.asset_key.path is a tuple like ('fred', 'raw', 'timeseries'),
        not a file path. We check all supported extensions to find the asset.

        For parquet datasets (directories with shard files),
        returns a Polars LazyFrame for efficient lazy evaluation and predicate pushdown.
        Single data.parquet files are loaded as pandas DataFrames.
        """
        # Check for sharded parquet dataset
        # The path from resolve_asset_path ends with 'data', so parent is asset dir
        asset_dir = path.parent
        if asset_dir.is_dir():
            # Only use dataset handler for sharded files (part-NNNN.parquet pattern)
            shard_files = list(asset_dir.glob(SHARD_GLOB_PATTERN))
            if shard_files:
                dataset_handler = ParquetDatasetHandler()
                data = dataset_handler.load(asset_dir)
                context.log.info(
                    f"Loaded LazyFrame from parquet dataset at {asset_dir} "
                    f"({len(shard_files)} shards)"
                )
                return data

        # Fall back to single-file handlers
        for handler in self._handlers:
            full_path = path.with_suffix(handler.extension)
            if full_path.exists():
                data = handler.load(full_path)
                context.log.info(f"Loaded {type(data).__name__} from {full_path}")
                return data

        supported_exts = [h.extension for h in self._handlers]
        raise FileNotFoundError(
            f"No asset found at {path} with extensions: {supported_exts}"
        )

    def load_partitions(
        self, context: dg.InputContext
    ) -> dict[str, pd.DataFrame | pl.LazyFrame | dict]:
        """Load multiple partitions for AllPartitionMapping inputs.

        When an asset uses AllPartitionMapping() to consume all partitions from
        an upstream partitioned asset, this method is called instead of load_input.

        Returns:
            Dict mapping partition_key -> loaded_data
        """
        result = {}
        asset_key = context.asset_key

        for partition_key in context.asset_partition_keys:
            path = self.resolve_asset_path_for_key(asset_key, partition_key)

            # Check for sharded parquet dataset
            asset_dir = path.parent
            if asset_dir.is_dir():
                shard_files = list(asset_dir.glob(SHARD_GLOB_PATTERN))
                if shard_files:
                    dataset_handler = ParquetDatasetHandler()
                    result[partition_key] = dataset_handler.load(asset_dir)
                    continue

            # Try all supported extensions
            loaded = False
            for handler in self._handlers:
                full_path = path.with_suffix(handler.extension)
                if full_path.exists():
                    result[partition_key] = handler.load(full_path)
                    loaded = True
                    break

            if not loaded:
                context.log.warning(
                    f"No data found for partition {partition_key} at {path}"
                )
                # Return empty LazyFrame for missing partitions
                result[partition_key] = pl.LazyFrame()

        context.log.info(f"Loaded {len(result)} partitions for {asset_key}")
        return result

    # Context-free methods for programmatic access (used by data library)

    def resolve_asset_path_for_key(
        self, asset_key: dg.AssetKey, partition_key: str | dict | None = None
    ) -> UPath:
        """Resolve asset key and partition to Hive-style file path (without context).

        Uses shared path resolution for consistency with AssetStore.

        Args:
            asset_key: Dagster AssetKey
            partition_key: Optional partition key (str for single-dim, dict for multi-dim)

        Returns:
            Hive-style path without file extension
        """
        return resolve_asset_path(self._base_path, asset_key.path, partition_key)

    def load_asset(
        self, asset_key: dg.AssetKey, partition_key: str | dict | None = None
    ) -> pd.DataFrame | pl.LazyFrame | dict:
        """Load asset without Dagster context.

        For programmatic access outside Dagster execution.

        Args:
            asset_key: Dagster AssetKey for the asset
            partition_key: Optional partition key (str for single-dim, dict for multi-dim)

        Returns:
            Loaded asset data (DataFrame, LazyFrame, or dict)

        Raises:
            FileNotFoundError: If asset doesn't exist at expected path
        """
        path = self.resolve_asset_path_for_key(asset_key, partition_key)

        # Check for sharded parquet dataset
        asset_dir = path.parent
        if asset_dir.is_dir():
            shard_files = list(asset_dir.glob(SHARD_GLOB_PATTERN))
            if shard_files:
                dataset_handler = ParquetDatasetHandler()
                return dataset_handler.load(asset_dir)

        # Try all supported extensions
        for handler in self._handlers:
            full_path = path.with_suffix(handler.extension)
            if full_path.exists():
                return handler.load(full_path)

        supported_exts = [h.extension for h in self._handlers]
        raise FileNotFoundError(
            f"No asset found at {path} with extensions: {supported_exts}"
        )

    def save_asset(
        self,
        asset_key: dg.AssetKey,
        obj: pd.DataFrame | pl.LazyFrame | dict,
        partition_key: str | dict | None = None,
    ) -> None:
        """Save asset without Dagster context.

        For programmatic access outside Dagster execution.

        Args:
            asset_key: Dagster AssetKey for the asset
            obj: Data to save (DataFrame, LazyFrame, or dict)
            partition_key: Optional partition key (str for single-dim, dict for multi-dim)

        Raises:
            TypeError: If data type is not supported
        """
        path = self.resolve_asset_path_for_key(asset_key, partition_key)
        path.parent.mkdir(parents=True, exist_ok=True)

        handler = self._get_handler_for_type(type(obj))
        handler.dump(obj, path.with_suffix(handler.extension))
