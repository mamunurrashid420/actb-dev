"""Streaming data source types for IO manager.

This module provides types for streaming batch writes to parquet,
enabling memory-efficient processing of large datasets.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass

import polars as pl
import pyarrow as pa


@dataclass
class StreamingParquetSource:
    """Wrapper for streaming batch writes to parquet.

    Assets return this type when they generate data in batches
    (e.g., parsing JSON/TSV from zip files). The IO manager
    streams batches to sharded parquet files.

    Args:
        batch_iterator: Factory function that returns an iterator of batches.
                       Each batch is a pl.DataFrame or pa.Table.
        rows_per_shard: Max rows per shard file. Default 8,192,000 (~128 MB).
    """

    batch_iterator: Callable[[], Iterator[pl.DataFrame | pa.Table]]
    rows_per_shard: int = 8_192_000


__all__ = ["StreamingParquetSource"]
