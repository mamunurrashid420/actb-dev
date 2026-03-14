"""BLS (Bureau of Labor Statistics) API-based assets - curated series.

This module provides a curated set of key BLS series via the API:
- Job Openings and Labor Turnover Survey (JOLTS)
- Employment Cost Index (ECI)
- Producer Price Index (PPI)
- Labor Force Statistics
- Average Hourly Earnings

For comprehensive dataset coverage, see bulk_downloads.py which fetches
complete datasets from BLS FTP.

Architecture:
- Bronze layer: Unpartitioned (all series in one asset)
- Semantic layer: Routed via indicator crosswalk (in economic.py)
"""

import dagster as dg
import pandas as pd

from pipelines.assets.bls.common import (
    ASSET_GROUP,
    BLS_BASE_METADATA,
    DEFAULT_RETRY_POLICY,
)
from pipelines.resources import BlsApiResource

# Metadata for each BLS series (for documentation only)
BLS_SERIES_INFO = {
    "JTS000000000000000JOL": {
        "name": "JOLTS Job Openings",
        "frequency": "monthly",
        "description": "Job openings in thousands",
    },
    "JTS000000000000000QUR": {
        "name": "JOLTS Quit Rate",
        "frequency": "monthly",
        "description": "Quits rate per 100 employed",
    },
    "CIU1010000000000A": {
        "name": "Employment Cost Index",
        "frequency": "quarterly",
        "description": "Employment Cost Index - total compensation",
    },
    "WPUFD4": {
        "name": "Producer Price Index",
        "frequency": "monthly",
        "description": "Producer Price Index - final demand",
    },
    "LNS11300000": {
        "name": "Labor Force Participation",
        "frequency": "monthly",
        "description": "Labor force participation rate",
    },
    "CES0500000003": {
        "name": "Average Hourly Earnings",
        "frequency": "monthly",
        "description": "Average hourly earnings - private sector",
    },
}


# =============================================================================
# BRONZE ASSETS - BLS API data ingestion
# =============================================================================


@dg.asset(
    name="all_series",
    key_prefix=["bronze", "bls"],
    group_name=ASSET_GROUP,
    code_version="1",
    pool="bls_api",
    metadata=BLS_BASE_METADATA
    | {
        "description": "All BLS timeseries data in a single asset (API-based)",
    },
    retry_policy=DEFAULT_RETRY_POLICY,
)
def all_series(
    context: dg.AssetExecutionContext, bls_api: BlsApiResource
) -> pd.DataFrame:
    """Fetch all BLS time series data.

    Returns:
        DataFrame with columns: date, value, series_id
    """
    all_data = []

    for series_id in BLS_SERIES_INFO:
        series_info = BLS_SERIES_INFO.get(series_id, {})
        context.log.info(
            f"Fetching BLS series {series_id} ({series_info.get('name', 'Unknown')})..."
        )
        df = bls_api.get_series(series_id)

        if df.empty:
            raise ValueError(
                f"BLS API returned no data for series {series_id}. "
                f"Verify series ID is valid and data is available."
            )

        df["series_id"] = series_id
        all_data.append(df)

    result = pd.concat(all_data, ignore_index=True)

    context.add_output_metadata({
        "num_records": len(result),
        "series_count": len(BLS_SERIES_INFO),
        "series_ids": list(BLS_SERIES_INFO),
        "date_range_start": str(result["date"].min()) if len(result) > 0 else None,
        "date_range_end": str(result["date"].max()) if len(result) > 0 else None,
    })
    context.log.info("All BLS series fetch complete")

    return result


# =============================================================================
# PUBLISHED ASSETS - LLM-ready economic indicators
# =============================================================================
# NOTE: Published assets moved to economic.py to consolidate
# all published economic data in one module


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # API-based asset
    "all_series",
    # Series metadata (for documentation/reference)
    "BLS_SERIES_INFO",
]
