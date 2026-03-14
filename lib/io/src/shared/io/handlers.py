"""File type handlers for serializing/deserializing data assets.

This module provides handlers for different data types:
- ParquetHandler: pandas DataFrames → Parquet files
- ParquetDatasetHandler: Polars LazyFrames → Parquet datasets (directories)
- StreamingParquetHandler: StreamingParquetSource → Parquet datasets (directories)
- JSONHandler: dicts → JSON files
"""

import datetime as dt
import json
from abc import ABC, abstractmethod

import pandas as pd
import polars as pl
import pyarrow.parquet as pq
from upath import UPath

from shared.io.paths import SHARD_GLOB_PATTERN, build_shard_filename
from shared.io.streaming import StreamingParquetSource


class PandasJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles pandas and datetime types."""

    def default(self, obj):
        """Convert pandas Timestamp and datetime objects to ISO format strings."""
        if isinstance(obj, pd.Timestamp | dt.datetime):
            return obj.isoformat()
        return super().default(obj)


class FileTypeHandler(ABC):
    """Handler for serializing/deserializing a specific Python type."""

    @property
    @abstractmethod
    def supported_type(self) -> type:
        """The Python type this handler supports."""

    @property
    @abstractmethod
    def extension(self) -> str:
        """File extension for this type."""

    @abstractmethod
    def dump(self, obj, path: UPath) -> None:
        """Serialize object to path."""

    @abstractmethod
    def load(self, path: UPath):
        """Deserialize object from path."""


class ParquetHandler(FileTypeHandler):
    """Handler for pandas DataFrames → Parquet files."""

    @property
    def supported_type(self) -> type:
        return pd.DataFrame

    @property
    def extension(self) -> str:
        return ".parquet"

    def dump(self, obj: pd.DataFrame, path: UPath) -> None:
        with path.open("wb") as f:
            obj.to_parquet(f, index=False)

    def load(self, path: UPath) -> pd.DataFrame:
        with path.open("rb") as f:
            return pd.read_parquet(f)


class ParquetDatasetHandler(FileTypeHandler):
    """Handler for Polars LazyFrames → Parquet datasets (directories of .parquet files).

    Reads parquet datasets using Polars lazy scanning with glob patterns.
    Supports Hive-style partitioning for efficient predicate pushdown.

    Read pattern:
        pl.scan_parquet("path/*.parquet", hive_partitioning=True)

    Write pattern (streaming sharded):
        LazyFrame.sink_parquet(
            PartitionMaxSize(
                "path/",
                file_path=lambda ctx: f'part-{ctx.file_idx:04d}.parquet',
                max_size=...
            )
        )

    Args:
        rows_per_shard: Maximum rows per parquet shard file.
            Default 8,192,000 (~128 MB for S3).
    """

    def __init__(self, rows_per_shard: int = 8_192_000):
        self.rows_per_shard = rows_per_shard

    @property
    def supported_type(self) -> type:
        return pl.LazyFrame

    @property
    def extension(self) -> str:
        return ""  # Directory, not a single file

    def dump(self, obj: pl.LazyFrame, path: UPath) -> None:
        """Sink LazyFrame to sharded parquet files using streaming."""
        path.mkdir(parents=True, exist_ok=True)
        obj.sink_parquet(
            pl.PartitionMaxSize(
                str(path),
                file_path=lambda ctx: build_shard_filename(ctx.file_idx),
                max_size=self.rows_per_shard,
            )
        )

    def load(self, path: UPath) -> pl.LazyFrame:
        """Scan all parquet files in directory as LazyFrame."""
        glob_pattern = str(path / "*.parquet")
        return pl.scan_parquet(glob_pattern, hive_partitioning=True)

    def can_load(self, path: UPath) -> bool:
        """Check if path is a directory containing shard files."""
        if not path.is_dir():
            return False
        shard_files = list(path.glob(SHARD_GLOB_PATTERN))
        return len(shard_files) > 0


class StreamingParquetHandler(FileTypeHandler):
    """Handler for StreamingParquetSource → sharded parquet datasets.

    Streams batches from a batch iterator to sharded parquet files.
    Used for assets that parse data in chunks (e.g., from zipped JSON/TSV).
    Loading returns a LazyFrame over the sharded files.
    """

    @property
    def supported_type(self) -> type:
        return StreamingParquetSource

    @property
    def extension(self) -> str:
        return ""  # Directory, not single file

    def dump(self, obj: StreamingParquetSource, path: UPath) -> None:
        """Stream batches to sharded parquet files."""
        path.mkdir(parents=True, exist_ok=True)

        # Clear existing shards
        for old_shard in path.glob(SHARD_GLOB_PATTERN):
            old_shard.unlink()

        shard_num = 0
        shard_rows = 0
        writer = None
        schema = None

        try:
            for batch in obj.batch_iterator():
                # Convert to PyArrow table if needed
                table = batch.to_arrow() if isinstance(batch, pl.DataFrame) else batch

                # Initialize schema on first batch
                if schema is None:
                    schema = table.schema
                    shard_path = path / build_shard_filename(shard_num)
                    writer = pq.ParquetWriter(str(shard_path), schema)

                writer.write_table(table)
                shard_rows += len(table)

                # Start new shard when target reached
                if shard_rows >= obj.rows_per_shard:
                    writer.close()
                    shard_num += 1
                    shard_rows = 0
                    shard_path = path / build_shard_filename(shard_num)
                    writer = pq.ParquetWriter(str(shard_path), schema)
        finally:
            if writer is not None:
                writer.close()

    def load(self, path: UPath) -> pl.LazyFrame:
        """Scan sharded parquet as LazyFrame."""
        return pl.scan_parquet(str(path / "*.parquet"), hive_partitioning=True)


class JSONHandler(FileTypeHandler):
    """Handler for dicts → JSON files."""

    @property
    def supported_type(self) -> type:
        return dict

    @property
    def extension(self) -> str:
        return ".json"

    def dump(self, obj: dict, path: UPath) -> None:
        with path.open("w") as f:
            json.dump(obj, f, indent=2, cls=PandasJSONEncoder)

    def load(self, path: UPath) -> dict:
        with path.open("r") as f:
            return json.load(f)
