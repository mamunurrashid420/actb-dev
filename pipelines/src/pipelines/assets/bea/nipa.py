"""BEA NIPA data assets - bronze and silver layers.

Bronze layer:
- nipa_bulk: Historical NIPA data from bulk flat files (quarterly refresh)
- nipa_current: Current year data from API (weekly refresh)

Silver layer:
- nipa_data: Merged bulk + current with computed metrics
"""

import datetime as dt

import dagster as dg
import polars as pl

from pipelines.assets.bea.common import ASSET_GROUP
from pipelines.resources import BeaApiResource

# =============================================================================
# BRONZE LAYER
# =============================================================================


@dg.asset(
    key_prefix=["bronze", "bea"],
    name="nipa_bulk",
    group_name=ASSET_GROUP,
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "bea",
        "description": "Complete NIPA bulk data from flat files",
    },
)
def bronze_nipa_bulk(
    context: dg.AssetExecutionContext,
    bea_api: BeaApiResource,
) -> pl.LazyFrame:
    """Download complete NIPA bulk data from flat files.

    Source: https://apps.bea.gov/national/Release/TXT/
    - NipaDataA.txt (annual ~12MB), NipaDataQ.txt (quarterly ~35MB), NipaDataM.txt (monthly ~36MB)
    - SeriesRegister.txt (metadata ~1MB)

    Coverage: ALL NIPA series since 1929
    Refresh: Quarterly (catches annual revisions in late September)

    BEA revises historical data:
    - Advance estimate: ~30 days after quarter end
    - Second estimate: ~60 days after quarter end
    - Third estimate: ~90 days after quarter end
    - Annual revision: Late September (covers prior 5 years)
    """
    context.log.info("Downloading NIPA bulk flat files (~83MB)...")
    lf = bea_api.download_nipa_bulk()

    # Collect to get metadata (LazyFrame doesn't have len() directly)
    schema = lf.collect_schema()

    context.add_output_metadata({
        "columns": list(schema.names()),
        "num_columns": len(schema),
        "frequencies": ["A", "Q", "M"],
        "description": "ALL NIPA series since 1929 (~10K+ unique series)",
    })

    return lf


@dg.asset(
    key_prefix=["bronze", "bea"],
    name="nipa_current",
    group_name=ASSET_GROUP,
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "bea",
        "description": "Current year NIPA data via API",
    },
)
def bronze_nipa_current(
    context: dg.AssetExecutionContext,
    bea_api: BeaApiResource,
) -> pl.LazyFrame:
    """Fetch current year NIPA data via API.

    Source: BEA API (rate limit: 100 req/min)
    Coverage: Full current year, all tables
    Refresh: Weekly (catches advance/second/third GDP estimates)

    Fetches only highest resolution per table (M > Q > A) to minimize API calls.
    """
    current_year = dt.datetime.now().year

    context.log.info(f"Fetching NIPA data for {current_year} via API...")

    lf = bea_api.get_current_year_data()

    # Collect schema for metadata
    schema = lf.collect_schema()

    context.add_output_metadata({
        "year": current_year,
        "columns": list(schema.names()),
        "description": "Current year NIPA data (highest resolution per table)",
    })

    return lf


# =============================================================================
# SILVER LAYER - MERGED DATA
# =============================================================================


def normalize_columns(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Normalize column names between bulk and API data formats."""
    # BEA bulk and API return slightly different column names
    column_mapping = {
        "tablename": "table_name",
        "seriescode": "series_code",
        "linenumber": "line_number",
        "linedescription": "line_description",
        "timeperiod": "time_period",
        "datavalue": "data_value",
        "cl_unit": "unit",
    }

    # Get current columns
    schema = lf.collect_schema()
    current_cols = schema.names()

    # Only rename columns that exist
    rename_cols = {k: v for k, v in column_mapping.items() if k in current_cols}
    if rename_cols:
        lf = lf.rename(rename_cols)

    return lf


@dg.asset(
    key_prefix=["silver", "bea"],
    name="nipa_data",
    group_name=ASSET_GROUP,
    metadata={
        "layer": "silver",
        "visibility": "internal",
        "source": "bea",
        "description": "Merged NIPA data (historical + current year)",
    },
    automation_condition=dg.AutomationCondition.all_deps_updated_since_cron(
        "0 * * * *"  # Hourly check, runs when bronze deps complete
    ),
    ins={
        "bronze_bea_nipa_bulk": dg.AssetIn(
            key=dg.AssetKey(["bronze", "bea", "nipa_bulk"]),
        ),
        "bronze_bea_nipa_current": dg.AssetIn(
            key=dg.AssetKey(["bronze", "bea", "nipa_current"]),
        ),
    },
)
def silver_nipa_data(
    context: dg.AssetExecutionContext,
    bronze_bea_nipa_bulk: pl.LazyFrame,
    bronze_bea_nipa_current: pl.LazyFrame,
) -> pl.LazyFrame:
    """Merge bulk + current NIPA data with normalized columns.

    Merge logic:
    - nipa_current is fresher (weekly refresh) - use for overlapping periods
    - nipa_bulk fills in historical data not covered by current
    """
    current_year = dt.datetime.now().year

    # Get schemas to check for empty frames
    bulk_schema = bronze_bea_nipa_bulk.collect_schema()
    current_schema = bronze_bea_nipa_current.collect_schema()

    # Handle empty LazyFrames
    if len(bulk_schema) == 0 and len(current_schema) == 0:
        context.log.warning("Both bulk and current NIPA data are empty")
        return pl.LazyFrame()

    if len(current_schema) == 0:
        context.log.info("Current NIPA data is empty, using only bulk data")
        lf = bronze_bea_nipa_bulk
    elif len(bulk_schema) == 0:
        context.log.info("Bulk NIPA data is empty, using only current data")
        lf = bronze_bea_nipa_current
    else:
        # Filter bulk to historical years only (before current year)
        # Bulk uses 'period' column with format like '2024Q1' or '2024'
        bulk_cols = bulk_schema.names()
        period_col = "period" if "period" in bulk_cols else "timeperiod"

        if period_col in bulk_cols:
            # Filter bulk to years before current year
            historical = bronze_bea_nipa_bulk.filter(
                pl.col(period_col).str.slice(0, 4).cast(pl.Int32) < current_year
            )

            context.log.info(
                f"Merging historical (< {current_year}) from bulk + current year data"
            )

            # Use diagonal concat which handles different schemas
            lf = pl.concat([historical, bronze_bea_nipa_current], how="diagonal")
        else:
            # Can't filter, just use bulk
            lf = bronze_bea_nipa_bulk

    # Normalize column names
    lf = normalize_columns(lf)

    # Collect schema for metadata
    schema = lf.collect_schema()

    context.add_output_metadata({
        "columns": list(schema.names()),
        "num_columns": len(schema),
        "description": "Merged NIPA data (historical + current year)",
    })

    return lf


__all__ = [
    "bronze_nipa_bulk",
    "bronze_nipa_current",
    "silver_nipa_data",
]
