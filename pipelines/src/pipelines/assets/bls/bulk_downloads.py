"""BLS bulk download bronze assets.

This module contains unpartitioned bronze assets that download and parse
BLS flat files from FTP:
- cpi_download → cpi: Consumer Price Index (CPI-U)
- labor_force_download → labor_force: Labor Force Statistics
- employment_download → employment: Current Employment Statistics (CES)
- jolts_download → jolts: Job Openings and Labor Turnover Survey

The download/parse split provides checkpointing - downloads can succeed
independently, and parsing failures don't require re-downloading.

All datasets are denormalized by joining series metadata with dimension
lookups during parsing, providing self-contained output for queries.

Uses Polars LazyFrames for memory-efficient streaming processing.
"""

import dagster as dg
import pandas as pd
import polars as pl

from pipelines.assets.bls.common import (
    ASSET_GROUP,
    BLS_BASE_METADATA,
    DATA_FILES,
    DEFAULT_RETRY_POLICY,
    add_date_column,
    lazy_merge_dimension,
    scan_bls_data_file,
    scan_bls_dimension_file,
    scan_bls_series_file,
)
from pipelines.resources import BlsBulkResource


def _scan_dimension_file(file_paths: dict, filename: str) -> pl.LazyFrame | None:
    """Lazily scan a dimension file if it exists, returning None if not available."""
    path = file_paths.get(filename)
    if path is None:
        return None
    return scan_bls_dimension_file(path)


def _create_seasonal_lookup(seasonal_lf: pl.LazyFrame | None) -> pl.LazyFrame | None:
    """Create a seasonal adjustment lookup table.

    BLS seasonal files have columns like 'seasonal_code' and 'seasonal_text'.
    This creates a lookup from the code to a user-friendly name.
    """
    if seasonal_lf is None:
        return None

    schema = seasonal_lf.collect_schema()
    cols = list(schema.names())

    if len(cols) < 2:
        return None

    # First column is the code, second is the description
    code_col = cols[0]
    text_col = cols[1]

    return seasonal_lf.select([
        pl.col(code_col).alias("seasonal"),
        pl.col(text_col).alias("seasonal_name"),
    ]).unique(subset=["seasonal"])


# =============================================================================
# DOWNLOAD CHECKPOINT ASSETS
# =============================================================================


def _create_download_asset(dataset: str, description: str):
    """Factory to create download checkpoint assets for BLS datasets."""

    @dg.asset(
        key_prefix=["bronze", "bls"],
        name=f"{dataset}_download",
        group_name=ASSET_GROUP,
        metadata=BLS_BASE_METADATA
        | {
            "description": f"Download checkpoint for BLS {description}",
            "dataset": dataset,
        },
        retry_policy=DEFAULT_RETRY_POLICY,
    )
    def download_asset(
        context: dg.AssetExecutionContext,
        bls_bulk: BlsBulkResource,
    ) -> pd.DataFrame:
        """Download BLS dataset files to cache."""
        context.log.info(f"Downloading BLS {dataset} files...")

        def log_progress(msg: str):
            context.log.info(msg)

        file_paths = bls_bulk.download_dataset(
            dataset,
            force=False,
            progress_callback=log_progress,
        )

        context.log.info(f"Downloaded {len(file_paths)} files for {dataset}")

        context.add_output_metadata({
            "files_downloaded": len(file_paths),
            "file_names": list(file_paths.keys()),
            "cache_dir": str(bls_bulk._get_cache_dir(dataset)),
        })

        # Return metadata about downloaded files
        return pd.DataFrame({
            "filename": list(file_paths.keys()),
            "path": [str(p) for p in file_paths.values()],
            "downloaded_at": pd.Timestamp.now(),
        })

    # Set function name for Dagster
    download_asset.__name__ = f"{dataset}_download"
    download_asset.__qualname__ = f"{dataset}_download"

    return download_asset


# Create download assets for all datasets
bronze_cpi_download = _create_download_asset("cpi", "Consumer Price Index (CPI-U)")
bronze_labor_force_download = _create_download_asset(
    "labor_force", "Labor Force Statistics"
)
bronze_employment_download = _create_download_asset(
    "employment", "Current Employment Statistics"
)
bronze_jolts_download = _create_download_asset(
    "jolts", "Job Openings and Labor Turnover Survey"
)


# =============================================================================
# PARSE ASSETS - CPI
# =============================================================================


@dg.asset(
    key_prefix=["bronze", "bls"],
    name="cpi",
    group_name=ASSET_GROUP,
    metadata=BLS_BASE_METADATA
    | {
        "description": "Consumer Price Index (CPI-U) - denormalized time series",
    },
    ins={
        "cpi_download": dg.AssetIn(key=["bronze", "bls", "cpi_download"]),
    },
    retry_policy=DEFAULT_RETRY_POLICY,
)
def bronze_cpi(
    context: dg.AssetExecutionContext,
    cpi_download: pd.DataFrame,
) -> pl.LazyFrame:
    """Parse CPI-U data with denormalized dimensions using Polars LazyFrames.

    Joins series data with area, item, and other dimension lookups
    to produce self-contained output. Streams directly to parquet for memory efficiency.
    """
    # Get file paths from download metadata
    file_paths = dict(zip(cpi_download["filename"], cpi_download["path"], strict=False))

    context.log.info("Building lazy processing pipeline...")

    # Lazily scan all files
    data_lf = scan_bls_data_file(file_paths[DATA_FILES["cpi"]])
    series_lf = scan_bls_series_file(file_paths["cu.series"])
    area_lf = _scan_dimension_file(file_paths, "cu.area")
    item_lf = _scan_dimension_file(file_paths, "cu.item")
    seasonal_lf = _scan_dimension_file(file_paths, "cu.seasonal")

    # Build lazy pipeline: join series metadata
    lf = data_lf.join(series_lf, on="series_id", how="left")

    # Join dimension lookups
    lf = lazy_merge_dimension(lf, area_lf, "area_code", "area_name")
    lf = lazy_merge_dimension(lf, item_lf, "item_code", "item_name")

    # Add seasonal adjustment name via join
    seasonal_lookup = _create_seasonal_lookup(seasonal_lf)
    if seasonal_lookup is not None:
        lf = lf.join(seasonal_lookup, on="seasonal", how="left")

    # Add date column using vectorized expression
    lf = add_date_column(lf)

    # Select output columns (only those that exist)
    output_cols = [
        "series_id",
        "date",
        "year",
        "period",
        "value",
        "footnote_codes",
        "area_code",
        "area_name",
        "item_code",
        "item_name",
        "seasonal",
        "seasonal_name",
    ]
    available_cols = [c for c in output_cols if c in lf.collect_schema().names()]
    lf = lf.select(available_cols)

    context.log.info("Returning LazyFrame for streaming write to parquet...")
    context.add_output_metadata({
        "processing_mode": "streaming",
        "output_columns": available_cols,
    })

    # Return LazyFrame - IO manager will sink_parquet for streaming write
    return lf


# =============================================================================
# PARSE ASSETS - LABOR FORCE
# =============================================================================


@dg.asset(
    key_prefix=["bronze", "bls"],
    name="labor_force",
    group_name=ASSET_GROUP,
    metadata=BLS_BASE_METADATA
    | {
        "description": "Labor Force Statistics - denormalized time series",
    },
    ins={
        "labor_force_download": dg.AssetIn(
            key=["bronze", "bls", "labor_force_download"]
        ),
    },
    retry_policy=DEFAULT_RETRY_POLICY,
)
def bronze_labor_force(
    context: dg.AssetExecutionContext,
    labor_force_download: pd.DataFrame,
) -> pl.LazyFrame:
    """Parse Labor Force data with denormalized dimensions using Polars LazyFrames."""
    file_paths = dict(
        zip(
            labor_force_download["filename"], labor_force_download["path"], strict=False
        )
    )

    context.log.info("Building lazy processing pipeline...")

    # Lazily scan all files
    data_lf = scan_bls_data_file(file_paths[DATA_FILES["labor_force"]])
    series_lf = scan_bls_series_file(file_paths["ln.series"])

    # Dimension lookups (some may not exist, e.g., ln.area)
    lfst_lf = _scan_dimension_file(file_paths, "ln.lfst")
    ages_lf = _scan_dimension_file(file_paths, "ln.ages")
    sexs_lf = _scan_dimension_file(file_paths, "ln.sexs")
    race_lf = _scan_dimension_file(file_paths, "ln.race")
    orig_lf = _scan_dimension_file(file_paths, "ln.orig")
    pcts_lf = _scan_dimension_file(file_paths, "ln.pcts")
    seasonal_lf = _scan_dimension_file(file_paths, "ln.seasonal")

    # Build lazy pipeline: join series metadata
    lf = data_lf.join(series_lf, on="series_id", how="left")

    # Join dimension lookups
    lf = lazy_merge_dimension(lf, lfst_lf, "lfst_code", "lfst_name")
    lf = lazy_merge_dimension(lf, ages_lf, "ages_code", "ages_name")
    lf = lazy_merge_dimension(lf, sexs_lf, "sexs_code", "sexs_name")
    lf = lazy_merge_dimension(lf, race_lf, "race_code", "race_name")
    lf = lazy_merge_dimension(lf, orig_lf, "orig_code", "orig_name")
    lf = lazy_merge_dimension(lf, pcts_lf, "pcts_code", "pcts_name")

    # Add seasonal adjustment name via join
    seasonal_lookup = _create_seasonal_lookup(seasonal_lf)
    if seasonal_lookup is not None:
        lf = lf.join(seasonal_lookup, on="seasonal", how="left")

    # Add date column using vectorized expression
    lf = add_date_column(lf)

    # Select output columns (only those that exist)
    output_cols = [
        "series_id",
        "date",
        "year",
        "period",
        "value",
        "footnote_codes",
        "lfst_code",
        "lfst_name",
        "ages_code",
        "ages_name",
        "sexs_code",
        "sexs_name",
        "race_code",
        "race_name",
        "orig_code",
        "orig_name",
        "pcts_code",
        "pcts_name",
        "seasonal",
        "seasonal_name",
    ]
    available_cols = [c for c in output_cols if c in lf.collect_schema().names()]
    lf = lf.select(available_cols)

    context.log.info("Returning LazyFrame for streaming write to parquet...")
    context.add_output_metadata({
        "processing_mode": "streaming",
        "output_columns": available_cols,
    })

    # Return LazyFrame - IO manager will sink_parquet for streaming write
    return lf


# =============================================================================
# PARSE ASSETS - EMPLOYMENT
# =============================================================================


@dg.asset(
    key_prefix=["bronze", "bls"],
    name="employment",
    group_name=ASSET_GROUP,
    metadata=BLS_BASE_METADATA
    | {
        "description": "Current Employment Statistics (CES) - denormalized time series",
    },
    ins={
        "employment_download": dg.AssetIn(key=["bronze", "bls", "employment_download"]),
    },
    retry_policy=DEFAULT_RETRY_POLICY,
)
def bronze_employment(
    context: dg.AssetExecutionContext,
    employment_download: pd.DataFrame,
) -> pl.LazyFrame:
    """Parse Employment (CES) data with denormalized dimensions using Polars LazyFrames."""
    file_paths = dict(
        zip(employment_download["filename"], employment_download["path"], strict=False)
    )

    context.log.info("Building lazy processing pipeline...")

    # Lazily scan all files
    data_lf = scan_bls_data_file(file_paths[DATA_FILES["employment"]])
    series_lf = scan_bls_series_file(file_paths["ce.series"])

    # Dimension lookups
    supersector_lf = _scan_dimension_file(file_paths, "ce.supersector")
    industry_lf = _scan_dimension_file(file_paths, "ce.industry")
    datatype_lf = _scan_dimension_file(file_paths, "ce.datatype")
    seasonal_lf = _scan_dimension_file(file_paths, "ce.seasonal")

    # Build lazy pipeline: join series metadata
    lf = data_lf.join(series_lf, on="series_id", how="left")

    # Join dimension lookups
    lf = lazy_merge_dimension(
        lf, supersector_lf, "supersector_code", "supersector_name"
    )
    lf = lazy_merge_dimension(lf, industry_lf, "industry_code", "industry_name")
    lf = lazy_merge_dimension(lf, datatype_lf, "data_type_code", "data_type_name")

    # Add seasonal adjustment name via join
    seasonal_lookup = _create_seasonal_lookup(seasonal_lf)
    if seasonal_lookup is not None:
        lf = lf.join(seasonal_lookup, on="seasonal", how="left")

    # Add date column using vectorized expression
    lf = add_date_column(lf)

    # Select output columns (only those that exist)
    output_cols = [
        "series_id",
        "date",
        "year",
        "period",
        "value",
        "footnote_codes",
        "supersector_code",
        "supersector_name",
        "industry_code",
        "industry_name",
        "data_type_code",
        "data_type_name",
        "seasonal",
        "seasonal_name",
    ]
    available_cols = [c for c in output_cols if c in lf.collect_schema().names()]
    lf = lf.select(available_cols)

    context.log.info("Returning LazyFrame for streaming write to parquet...")
    context.add_output_metadata({
        "processing_mode": "streaming",
        "output_columns": available_cols,
    })

    # Return LazyFrame - IO manager will sink_parquet for streaming write
    return lf


# =============================================================================
# PARSE ASSETS - JOLTS
# =============================================================================


@dg.asset(
    key_prefix=["bronze", "bls"],
    name="jolts",
    group_name=ASSET_GROUP,
    metadata=BLS_BASE_METADATA
    | {
        "description": "Job Openings and Labor Turnover Survey (JOLTS) - denormalized time series",
    },
    ins={
        "jolts_download": dg.AssetIn(key=["bronze", "bls", "jolts_download"]),
    },
    retry_policy=DEFAULT_RETRY_POLICY,
)
def bronze_jolts(
    context: dg.AssetExecutionContext,
    jolts_download: pd.DataFrame,
) -> pl.LazyFrame:
    """Parse JOLTS data with denormalized dimensions using Polars LazyFrames."""
    file_paths = dict(
        zip(jolts_download["filename"], jolts_download["path"], strict=False)
    )

    context.log.info("Building lazy processing pipeline...")

    # Lazily scan all files
    data_lf = scan_bls_data_file(file_paths[DATA_FILES["jolts"]])
    series_lf = scan_bls_series_file(file_paths["jt.series"])

    # Dimension lookups
    industry_lf = _scan_dimension_file(file_paths, "jt.industry")
    area_lf = _scan_dimension_file(file_paths, "jt.area")
    state_lf = _scan_dimension_file(file_paths, "jt.state")
    sizeclass_lf = _scan_dimension_file(file_paths, "jt.sizeclass")
    dataelement_lf = _scan_dimension_file(file_paths, "jt.dataelement")
    ratelevel_lf = _scan_dimension_file(file_paths, "jt.ratelevel")
    seasonal_lf = _scan_dimension_file(file_paths, "jt.seasonal")

    # Build lazy pipeline: join series metadata
    lf = data_lf.join(series_lf, on="series_id", how="left")

    # Join dimension lookups
    lf = lazy_merge_dimension(lf, industry_lf, "industry_code", "industry_name")
    lf = lazy_merge_dimension(lf, area_lf, "area_code", "area_name")
    lf = lazy_merge_dimension(lf, state_lf, "state_code", "state_name")
    lf = lazy_merge_dimension(lf, sizeclass_lf, "sizeclass_code", "sizeclass_name")
    lf = lazy_merge_dimension(
        lf, dataelement_lf, "dataelement_code", "dataelement_name"
    )
    lf = lazy_merge_dimension(lf, ratelevel_lf, "ratelevel_code", "ratelevel_name")

    # Add seasonal adjustment name via join
    seasonal_lookup = _create_seasonal_lookup(seasonal_lf)
    if seasonal_lookup is not None:
        lf = lf.join(seasonal_lookup, on="seasonal", how="left")

    # Add date column using vectorized expression
    lf = add_date_column(lf)

    # Select output columns (only those that exist)
    output_cols = [
        "series_id",
        "date",
        "year",
        "period",
        "value",
        "footnote_codes",
        "industry_code",
        "industry_name",
        "area_code",
        "area_name",
        "state_code",
        "state_name",
        "sizeclass_code",
        "sizeclass_name",
        "dataelement_code",
        "dataelement_name",
        "ratelevel_code",
        "ratelevel_name",
        "seasonal",
        "seasonal_name",
    ]
    available_cols = [c for c in output_cols if c in lf.collect_schema().names()]
    lf = lf.select(available_cols)

    context.log.info("Returning LazyFrame for streaming write to parquet...")
    context.add_output_metadata({
        "processing_mode": "streaming",
        "output_columns": available_cols,
    })

    # Return LazyFrame - IO manager will sink_parquet for streaming write
    return lf


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # Download checkpoint assets
    "bronze_cpi_download",
    "bronze_labor_force_download",
    "bronze_employment_download",
    "bronze_jolts_download",
    # Parse assets
    "bronze_cpi",
    "bronze_labor_force",
    "bronze_employment",
    "bronze_jolts",
]
