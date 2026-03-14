"""Shared utilities, schemas, and constants for BLS bulk assets.

This module contains helper functions and constants for parsing and
processing BLS flat files from bulk FTP downloads.

Uses Polars LazyFrames for memory-efficient streaming processing.
"""

import dagster as dg
import polars as pl

# =============================================================================
# CONSTANTS
# =============================================================================

ASSET_GROUP = "bls"

# Base metadata shared across all BLS bronze assets
BLS_BASE_METADATA = {
    "layer": "bronze",
    "visibility": "internal",
    "source": "bureau_of_labor_statistics",
    "country": "United States",
}

# Standard retry policy for BLS downloads
DEFAULT_RETRY_POLICY = dg.RetryPolicy(max_retries=3, delay=60)

# =============================================================================
# DATASET SCHEMAS - Output columns for denormalized data
# =============================================================================

# CPI-U columns (Consumer Price Index - Urban)
CPI_COLUMNS = [
    "series_id",
    "year",
    "period",
    "value",
    "footnote_codes",
    # Denormalized dimensions
    "area_code",
    "area_name",
    "item_code",
    "item_name",
    "seasonal",
    "periodicity",
    "base_code",
    "base_period",
]

# Labor Force columns
LABOR_FORCE_COLUMNS = [
    "series_id",
    "year",
    "period",
    "value",
    "footnote_codes",
    # Denormalized dimensions
    "lfst_code",
    "lfst_name",
    "area_code",
    "area_name",
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
]

# Employment (CES) columns
EMPLOYMENT_COLUMNS = [
    "series_id",
    "year",
    "period",
    "value",
    "footnote_codes",
    # Denormalized dimensions
    "supersector_code",
    "supersector_name",
    "industry_code",
    "industry_name",
    "data_type_code",
    "data_type_name",
    "seasonal",
]

# JOLTS columns
JOLTS_COLUMNS = [
    "series_id",
    "year",
    "period",
    "value",
    "footnote_codes",
    # Denormalized dimensions
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
]

# =============================================================================
# DATA FILE PATTERNS - Which file contains what
# =============================================================================

# Primary data files for each dataset (contain time series values)
DATA_FILES = {
    "cpi": "cu.data.1.AllItems",  # Full history
    "labor_force": "ln.data.1.AllData",
    "employment": "ce.data.0.AllCESSeries",
    "jolts": "jt.data.1.AllItems",
}


# =============================================================================
# HELPER FUNCTIONS - Parsing BLS flat files with Polars LazyFrames
# =============================================================================


def scan_bls_data_file(path: str) -> pl.LazyFrame:
    """Lazily scan a BLS data file (tab-delimited, fixed format).

    BLS data files have format:
    series_id       year    period  value   footnote_codes

    Note: BLS files have whitespace in column names that must be stripped.

    Args:
        path: Path to the data file

    Returns:
        LazyFrame with series_id, year, period, value, footnote_codes columns
    """
    # Scan with all strings first to handle whitespace in column names
    lf = pl.scan_csv(path, separator="\t", infer_schema_length=0)

    # Get column names and create rename mapping to strip whitespace
    schema = lf.collect_schema()
    stripped_names = {name: name.strip() for name in schema.names()}

    return lf.rename(stripped_names).with_columns([
        pl.col("series_id").str.strip_chars(),
        pl.col("year").str.strip_chars().cast(pl.Int32),
        pl.col("period").str.strip_chars(),
        # Handle "-" or other non-numeric values by replacing with null before cast
        pl.col("value").str.strip_chars().replace("-", None).cast(pl.Float64),
        pl.col("footnote_codes").fill_null("").str.strip_chars(),
    ])


def scan_bls_dimension_file(path: str) -> pl.LazyFrame:
    """Lazily scan a BLS dimension/lookup file (tab-delimited).

    Args:
        path: Path to the dimension file

    Returns:
        LazyFrame with dimension columns (all strings, stripped)
    """
    # Scan with all strings, then strip column names and values
    lf = pl.scan_csv(path, separator="\t", infer_schema_length=0)

    # Get column names and create rename mapping
    schema = lf.collect_schema()
    stripped_names = {name: name.strip() for name in schema.names()}

    return lf.rename(stripped_names).with_columns([
        pl.col(col).str.strip_chars() for col in stripped_names.values()
    ])


def scan_bls_series_file(path: str) -> pl.LazyFrame:
    """Lazily scan a BLS series metadata file (tab-delimited).

    Args:
        path: Path to the series file

    Returns:
        LazyFrame with series metadata (all strings, stripped)
    """
    # Scan with all strings, then strip column names and values
    lf = pl.scan_csv(path, separator="\t", infer_schema_length=0)

    # Get column names and create rename mapping
    schema = lf.collect_schema()
    stripped_names = {name: name.strip() for name in schema.names()}

    return lf.rename(stripped_names).with_columns([
        pl.col(col).str.strip_chars() for col in stripped_names.values()
    ])


def lazy_merge_dimension(
    lf: pl.LazyFrame,
    dim_lf: pl.LazyFrame | None,
    code_col: str,
    name_col: str,
) -> pl.LazyFrame:
    """Lazily join a dimension lookup table to data.

    Handles various BLS dimension file formats by finding the appropriate
    name column automatically.

    Args:
        lf: Main LazyFrame to join into
        dim_lf: Dimension lookup LazyFrame (or None if not available)
        code_col: Column name for the code (e.g., 'industry_code')
        name_col: Target column name for the name (e.g., 'industry_name')

    Returns:
        LazyFrame with name column joined (or unchanged if join not possible)
    """
    if dim_lf is None:
        return lf

    # Collect schema to check columns (lazy operation, just reads metadata)
    dim_schema = dim_lf.collect_schema()
    dim_cols = list(dim_schema.names())

    if len(dim_cols) == 0:
        return lf

    # Find the source name column in dimension table
    prefix = code_col.replace("_code", "")
    source_name_col = None

    # Look for standard naming patterns
    for candidate in [f"{prefix}_name", f"{prefix}_text", name_col]:
        if candidate in dim_cols:
            source_name_col = candidate
            break

    # Fall back to second column if it's not the code column
    if source_name_col is None and len(dim_cols) >= 2 and dim_cols[1] != code_col:
        source_name_col = dim_cols[1]

    if source_name_col is None:
        return lf

    # Find the source code column
    source_code_col = dim_cols[0]
    if code_col in dim_cols:
        source_code_col = code_col

    # Create clean lookup with just code and name, then join
    lookup = (
        dim_lf
        .select([pl.col(source_code_col), pl.col(source_name_col)])
        .unique(subset=[source_code_col])
        .rename({source_code_col: code_col, source_name_col: name_col})
    )

    return lf.join(lookup, on=code_col, how="left")


def add_date_column(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Add a date column from year/period using vectorized operations.

    BLS periods:
    - M01-M12: Monthly (first day of month)
    - M13: Annual average (Jan 1)
    - Q01-Q04: Quarterly (first day of quarter)
    - A01: Annual (Jan 1)
    - S01-S02: Semi-annual (Jan 1, Jul 1)

    Args:
        lf: LazyFrame with 'year' and 'period' columns

    Returns:
        LazyFrame with 'date' column added
    """
    period_upper = pl.col("period").str.to_uppercase().str.strip_chars()
    period_prefix = period_upper.str.slice(0, 1)
    period_num = period_upper.str.slice(1).cast(pl.Int32, strict=False)

    # Calculate month based on period type
    month_expr = (
        pl
        .when(period_prefix == "M")
        .then(
            pl
            .when(period_num == 13)
            .then(pl.lit(1))  # Annual average -> Jan
            .otherwise(period_num)
        )
        .when(period_prefix == "Q")
        .then((period_num - 1) * 3 + 1)  # Q1->1, Q2->4, Q3->7, Q4->10
        .when(period_upper.is_in(["A01", "S01"]))
        .then(pl.lit(1))
        .when(period_upper == "S02")
        .then(pl.lit(7))
        .otherwise(pl.lit(None))
    )

    # Build date from year and month
    date_expr = pl.date(pl.col("year"), month_expr, 1)

    return lf.with_columns(date_expr.alias("date"))


# Legacy pandas functions for backwards compatibility
def convert_bls_period_to_date(year: int, period: str) -> str | None:
    """Convert BLS year/period to ISO date string.

    BLS periods:
    - M01-M12: Monthly (first day of month)
    - M13: Annual average (Jan 1)
    - Q01-Q04: Quarterly (first day of quarter)
    - A01: Annual (Jan 1)
    - S01-S02: Semi-annual (Jan 1, Jul 1)

    Args:
        year: 4-digit year
        period: BLS period code (M01, Q01, A01, etc.)

    Returns:
        ISO date string (YYYY-MM-DD) or None if invalid
    """
    period = period.strip().upper()

    if period.startswith("M"):
        month_str = period[1:]
        if month_str.isdigit():
            month = int(month_str)
            if 1 <= month <= 12:
                return f"{year}-{month:02d}-01"
            elif month == 13:  # Annual average
                return f"{year}-01-01"

    elif period.startswith("Q"):
        quarter_str = period[1:]
        if quarter_str.isdigit():
            quarter = int(quarter_str)
            month = (quarter - 1) * 3 + 1
            if 1 <= month <= 10:
                return f"{year}-{month:02d}-01"

    elif period in ("A01", "S01"):
        return f"{year}-01-01"

    elif period == "S02":
        return f"{year}-07-01"

    return None


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # Constants
    "ASSET_GROUP",
    "BLS_BASE_METADATA",
    "DEFAULT_RETRY_POLICY",
    # Schema columns
    "CPI_COLUMNS",
    "LABOR_FORCE_COLUMNS",
    "EMPLOYMENT_COLUMNS",
    "JOLTS_COLUMNS",
    # Data file patterns
    "DATA_FILES",
    # Polars LazyFrame helpers (preferred)
    "scan_bls_data_file",
    "scan_bls_dimension_file",
    "scan_bls_series_file",
    "lazy_merge_dimension",
    "add_date_column",
    # Legacy pandas helpers (backwards compatibility)
    "convert_bls_period_to_date",
]
