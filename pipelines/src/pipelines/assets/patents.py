"""PatentsView bulk download bronze assets.

This module contains bronze assets that fetch PatentsView bulk data files:
- Download checkpoints for each table (caches zip files)
- Parse assets that stream from zips and convert to parquet

PatentsView provides quarterly snapshots of USPTO patent data with
disambiguated assignee/inventor information under CC BY 4.0 license.

Tables included:
- g_patent: Core patent metadata (9.3M rows)
- g_assignee_disambiguated: Company/assignee data (8.6M rows)
- g_patent_abstract: Patent abstracts for RAG/LLM (9.3M rows)
- g_cpc_current: Current CPC classifications (57.9M rows)
- g_cpc_title: CPC code descriptions (269K rows)
- g_inventor_disambiguated: Inventor data (23.7M rows)
- g_us_patent_citation: Citation graph (151M rows) - sharded

The download/parse split provides checkpointing - downloads can succeed
independently, and parsing failures don't require re-downloading.
"""

import zipfile
from collections.abc import Iterator
from pathlib import Path

import dagster as dg
import pandas as pd
import pyarrow as pa

from pipelines.resources import PatentsViewResource
from shared.io.streaming import StreamingParquetSource

ASSET_GROUP = "patents"

# Write batch size for streaming (rows per write to ParquetWriter)
WRITE_BATCH_SIZE = 100_000


# --- Helper functions ---


def _parse_tsv_to_dataframe(zip_path: Path, tsv_name: str) -> pd.DataFrame:
    """Extract TSV from zip and return pandas DataFrame.

    For smaller tables that fit in memory.
    """
    with zipfile.ZipFile(zip_path, "r") as zf, zf.open(tsv_name) as f:
        return pd.read_csv(f, sep="\t", low_memory=False)


def _iter_tsv_batches(zip_path: Path, tsv_name: str) -> Iterator[pa.Table]:
    """Iterate over TSV data from zip file as PyArrow tables.

    Streams from zip without extracting. Yields batches of WRITE_BATCH_SIZE rows.
    All columns are read as strings to avoid schema mismatches between chunks.

    Args:
        zip_path: Path to zip file containing TSV
        tsv_name: Name of TSV file within zip

    Yields:
        PyArrow tables of parsed TSV data
    """
    schema = None

    with zipfile.ZipFile(zip_path, "r") as zf, zf.open(tsv_name) as f:
        # Read in chunks using pandas, forcing all columns to string
        # to avoid schema mismatches between chunks (common with null values)
        chunk_iter = pd.read_csv(f, sep="\t", chunksize=WRITE_BATCH_SIZE, dtype=str)

        for chunk_df in chunk_iter:
            # Convert chunk to Arrow table
            table = pa.Table.from_pandas(chunk_df, preserve_index=False)

            # Initialize schema on first chunk
            if schema is None:
                schema = table.schema

            # Cast table to match schema (handles type mismatches between chunks)
            # Use safe=False to allow lossy conversions (e.g., double -> string)
            if table.schema != schema:
                table = table.cast(schema, safe=False)

            yield table


# --- Download checkpoint assets ---


@dg.asset(
    key_prefix=["bronze", "patents"],
    name="patents_download",
    group_name=ASSET_GROUP,
    metadata={"layer": "bronze", "source": "patentsview", "visibility": "internal"},
)
def bronze_patents_download(
    context: dg.AssetExecutionContext,
    patentsview: PatentsViewResource,
) -> pd.DataFrame:
    """Download g_patent.tsv.zip (~219 MB) and return metadata."""
    zip_path = patentsview.download_table(
        "g_patent", progress_callback=context.log.info
    )

    context.add_output_metadata({
        "zip_path": str(zip_path),
        "size_mb": zip_path.stat().st_size / (1024 * 1024),
    })

    return pd.DataFrame({
        "zip_path": [str(zip_path)],
        "table_name": ["g_patent"],
        "downloaded_at": [pd.Timestamp.now()],
    })


@dg.asset(
    key_prefix=["bronze", "patents"],
    name="assignees_download",
    group_name=ASSET_GROUP,
    metadata={"layer": "bronze", "source": "patentsview", "visibility": "internal"},
)
def bronze_assignees_download(
    context: dg.AssetExecutionContext,
    patentsview: PatentsViewResource,
) -> pd.DataFrame:
    """Download g_assignee_disambiguated.tsv.zip (~342 MB) and return metadata."""
    zip_path = patentsview.download_table(
        "g_assignee_disambiguated", progress_callback=context.log.info
    )

    context.add_output_metadata({
        "zip_path": str(zip_path),
        "size_mb": zip_path.stat().st_size / (1024 * 1024),
    })

    return pd.DataFrame({
        "zip_path": [str(zip_path)],
        "table_name": ["g_assignee_disambiguated"],
        "downloaded_at": [pd.Timestamp.now()],
    })


@dg.asset(
    key_prefix=["bronze", "patents"],
    name="abstracts_download",
    group_name=ASSET_GROUP,
    metadata={"layer": "bronze", "source": "patentsview", "visibility": "internal"},
)
def bronze_abstracts_download(
    context: dg.AssetExecutionContext,
    patentsview: PatentsViewResource,
) -> pd.DataFrame:
    """Download g_patent_abstract.tsv.zip (~1.6 GB) and return metadata."""
    zip_path = patentsview.download_table(
        "g_patent_abstract", progress_callback=context.log.info
    )

    context.add_output_metadata({
        "zip_path": str(zip_path),
        "size_mb": zip_path.stat().st_size / (1024 * 1024),
    })

    return pd.DataFrame({
        "zip_path": [str(zip_path)],
        "table_name": ["g_patent_abstract"],
        "downloaded_at": [pd.Timestamp.now()],
    })


@dg.asset(
    key_prefix=["bronze", "patents"],
    name="cpc_current_download",
    group_name=ASSET_GROUP,
    metadata={"layer": "bronze", "source": "patentsview", "visibility": "internal"},
)
def bronze_cpc_current_download(
    context: dg.AssetExecutionContext,
    patentsview: PatentsViewResource,
) -> pd.DataFrame:
    """Download g_cpc_current.tsv.zip (~472 MB) and return metadata."""
    zip_path = patentsview.download_table(
        "g_cpc_current", progress_callback=context.log.info
    )

    context.add_output_metadata({
        "zip_path": str(zip_path),
        "size_mb": zip_path.stat().st_size / (1024 * 1024),
    })

    return pd.DataFrame({
        "zip_path": [str(zip_path)],
        "table_name": ["g_cpc_current"],
        "downloaded_at": [pd.Timestamp.now()],
    })


@dg.asset(
    key_prefix=["bronze", "patents"],
    name="cpc_titles_download",
    group_name=ASSET_GROUP,
    metadata={"layer": "bronze", "source": "patentsview", "visibility": "internal"},
)
def bronze_cpc_titles_download(
    context: dg.AssetExecutionContext,
    patentsview: PatentsViewResource,
) -> pd.DataFrame:
    """Download g_cpc_title.tsv.zip (~6 MB) and return metadata."""
    zip_path = patentsview.download_table(
        "g_cpc_title", progress_callback=context.log.info
    )

    context.add_output_metadata({
        "zip_path": str(zip_path),
        "size_mb": zip_path.stat().st_size / (1024 * 1024),
    })

    return pd.DataFrame({
        "zip_path": [str(zip_path)],
        "table_name": ["g_cpc_title"],
        "downloaded_at": [pd.Timestamp.now()],
    })


@dg.asset(
    key_prefix=["bronze", "patents"],
    name="inventors_download",
    group_name=ASSET_GROUP,
    metadata={"layer": "bronze", "source": "patentsview", "visibility": "internal"},
)
def bronze_inventors_download(
    context: dg.AssetExecutionContext,
    patentsview: PatentsViewResource,
) -> pd.DataFrame:
    """Download g_inventor_disambiguated.tsv.zip (~666 MB) and return metadata."""
    zip_path = patentsview.download_table(
        "g_inventor_disambiguated", progress_callback=context.log.info
    )

    context.add_output_metadata({
        "zip_path": str(zip_path),
        "size_mb": zip_path.stat().st_size / (1024 * 1024),
    })

    return pd.DataFrame({
        "zip_path": [str(zip_path)],
        "table_name": ["g_inventor_disambiguated"],
        "downloaded_at": [pd.Timestamp.now()],
    })


@dg.asset(
    key_prefix=["bronze", "patents"],
    name="citations_download",
    group_name=ASSET_GROUP,
    metadata={"layer": "bronze", "source": "patentsview", "visibility": "internal"},
)
def bronze_citations_download(
    context: dg.AssetExecutionContext,
    patentsview: PatentsViewResource,
) -> pd.DataFrame:
    """Download g_us_patent_citation.tsv.zip (~2.1 GB) and return metadata."""
    zip_path = patentsview.download_table(
        "g_us_patent_citation", progress_callback=context.log.info
    )

    context.add_output_metadata({
        "zip_path": str(zip_path),
        "size_mb": zip_path.stat().st_size / (1024 * 1024),
    })

    return pd.DataFrame({
        "zip_path": [str(zip_path)],
        "table_name": ["g_us_patent_citation"],
        "downloaded_at": [pd.Timestamp.now()],
    })


# --- Parse assets (depend on downloads) ---


@dg.asset(
    key_prefix=["bronze", "patents"],
    name="patents",
    group_name=ASSET_GROUP,
    metadata={"layer": "bronze", "source": "patentsview", "visibility": "internal"},
    ins={"patents_download": dg.AssetIn(key=["bronze", "patents", "patents_download"])},
)
def bronze_patents(
    context: dg.AssetExecutionContext,
    patents_download: pd.DataFrame,
) -> pd.DataFrame:
    """Parse g_patent table (9.3M rows) from downloaded zip."""
    zip_path = Path(patents_download["zip_path"].iloc[0])

    context.log.info("Parsing g_patent.tsv...")
    df = _parse_tsv_to_dataframe(zip_path, "g_patent.tsv")

    context.add_output_metadata({
        "num_records": len(df),
        "columns": list(df.columns),
    })

    return df


@dg.asset(
    key_prefix=["bronze", "patents"],
    name="assignees",
    group_name=ASSET_GROUP,
    metadata={"layer": "bronze", "source": "patentsview", "visibility": "internal"},
    ins={
        "assignees_download": dg.AssetIn(
            key=["bronze", "patents", "assignees_download"]
        )
    },
)
def bronze_assignees(
    context: dg.AssetExecutionContext,
    assignees_download: pd.DataFrame,
) -> pd.DataFrame:
    """Parse g_assignee_disambiguated table (8.6M rows) from downloaded zip."""
    zip_path = Path(assignees_download["zip_path"].iloc[0])

    context.log.info("Parsing g_assignee_disambiguated.tsv...")
    df = _parse_tsv_to_dataframe(zip_path, "g_assignee_disambiguated.tsv")

    context.add_output_metadata({
        "num_records": len(df),
        "columns": list(df.columns),
    })

    return df


@dg.asset(
    key_prefix=["bronze", "patents"],
    name="abstracts",
    group_name=ASSET_GROUP,
    metadata={"layer": "bronze", "source": "patentsview", "visibility": "internal"},
    ins={
        "abstracts_download": dg.AssetIn(
            key=["bronze", "patents", "abstracts_download"]
        )
    },
)
def bronze_abstracts(
    context: dg.AssetExecutionContext,
    abstracts_download: pd.DataFrame,
) -> pd.DataFrame:
    """Parse g_patent_abstract table (9.3M rows) from downloaded zip."""
    zip_path = Path(abstracts_download["zip_path"].iloc[0])

    context.log.info("Parsing g_patent_abstract.tsv...")
    df = _parse_tsv_to_dataframe(zip_path, "g_patent_abstract.tsv")

    context.add_output_metadata({
        "num_records": len(df),
        "columns": list(df.columns),
    })

    return df


@dg.asset(
    key_prefix=["bronze", "patents"],
    name="cpc_current",
    group_name=ASSET_GROUP,
    metadata={"layer": "bronze", "source": "patentsview", "visibility": "internal"},
    ins={
        "cpc_current_download": dg.AssetIn(
            key=["bronze", "patents", "cpc_current_download"]
        )
    },
)
def bronze_cpc_current(
    context: dg.AssetExecutionContext,
    cpc_current_download: pd.DataFrame,
) -> StreamingParquetSource:
    """Parse g_cpc_current table (57.9M rows) with streaming sharded writes."""
    zip_path = Path(cpc_current_download["zip_path"].iloc[0])

    context.log.info("Returning StreamingParquetSource for g_cpc_current.tsv")
    context.add_output_metadata({"batch_size": WRITE_BATCH_SIZE})

    return StreamingParquetSource(
        batch_iterator=lambda: _iter_tsv_batches(zip_path, "g_cpc_current.tsv")
    )


@dg.asset(
    key_prefix=["bronze", "patents"],
    name="cpc_titles",
    group_name=ASSET_GROUP,
    metadata={"layer": "bronze", "source": "patentsview", "visibility": "internal"},
    ins={
        "cpc_titles_download": dg.AssetIn(
            key=["bronze", "patents", "cpc_titles_download"]
        )
    },
)
def bronze_cpc_titles(
    context: dg.AssetExecutionContext,
    cpc_titles_download: pd.DataFrame,
) -> pd.DataFrame:
    """Parse g_cpc_title table (269K rows) from downloaded zip."""
    zip_path = Path(cpc_titles_download["zip_path"].iloc[0])

    context.log.info("Parsing g_cpc_title.tsv...")
    df = _parse_tsv_to_dataframe(zip_path, "g_cpc_title.tsv")

    context.add_output_metadata({
        "num_records": len(df),
        "columns": list(df.columns),
    })

    return df


@dg.asset(
    key_prefix=["bronze", "patents"],
    name="inventors",
    group_name=ASSET_GROUP,
    metadata={"layer": "bronze", "source": "patentsview", "visibility": "internal"},
    ins={
        "inventors_download": dg.AssetIn(
            key=["bronze", "patents", "inventors_download"]
        )
    },
)
def bronze_inventors(
    context: dg.AssetExecutionContext,
    inventors_download: pd.DataFrame,
) -> pd.DataFrame:
    """Parse g_inventor_disambiguated table (23.7M rows) from downloaded zip."""
    zip_path = Path(inventors_download["zip_path"].iloc[0])

    context.log.info("Parsing g_inventor_disambiguated.tsv...")
    df = _parse_tsv_to_dataframe(zip_path, "g_inventor_disambiguated.tsv")

    context.add_output_metadata({
        "num_records": len(df),
        "columns": list(df.columns),
    })

    return df


@dg.asset(
    key_prefix=["bronze", "patents"],
    name="citations",
    group_name=ASSET_GROUP,
    metadata={"layer": "bronze", "source": "patentsview", "visibility": "internal"},
    ins={
        "citations_download": dg.AssetIn(
            key=["bronze", "patents", "citations_download"]
        )
    },
)
def bronze_citations(
    context: dg.AssetExecutionContext,
    citations_download: pd.DataFrame,
) -> StreamingParquetSource:
    """Parse g_us_patent_citation table (151M rows) with streaming sharded writes.

    Returns StreamingParquetSource - IO manager handles streaming to sharded parquet.
    """
    zip_path = Path(citations_download["zip_path"].iloc[0])

    context.log.info("Returning StreamingParquetSource for g_us_patent_citation.tsv")
    context.add_output_metadata({"batch_size": WRITE_BATCH_SIZE})

    return StreamingParquetSource(
        batch_iterator=lambda: _iter_tsv_batches(zip_path, "g_us_patent_citation.tsv")
    )


__all__ = [
    # Download checkpoints
    "bronze_patents_download",
    "bronze_assignees_download",
    "bronze_abstracts_download",
    "bronze_cpc_current_download",
    "bronze_cpc_titles_download",
    "bronze_inventors_download",
    "bronze_citations_download",
    # Parse assets
    "bronze_patents",
    "bronze_assignees",
    "bronze_abstracts",
    "bronze_cpc_current",
    "bronze_cpc_titles",
    "bronze_inventors",
    "bronze_citations",
]
