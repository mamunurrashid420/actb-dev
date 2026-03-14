"""FRED (Federal Reserve Economic Data) assets - US economic indicators.

Architecture:
- Bronze layer: series_registry (metadata) and series (timeseries data)
- Semantic layer: Routed via indicator crosswalk (in economic.py)

The series asset fetches top N series by popularity from FRED.
Default: top 1000 most popular series (~8-10 min materialization).
"""

import time

import dagster as dg
import pandas as pd

from pipelines.resources import FredApiResource

# =============================================================================
# CONSTANTS
# =============================================================================

# Default number of series to fetch (configurable)
DEFAULT_SERIES_LIMIT = 1000

# Core series that must always be included (for backward compatibility)
CORE_SERIES_IDS = ["GDP", "UNRATE", "CPIAUCSL", "PCE", "FEDFUNDS"]


# =============================================================================
# BRONZE LAYER - FRED API data ingestion
# =============================================================================


@dg.asset(
    name="series_registry",
    key_prefix=["bronze", "fred"],
    group_name="fred",
    code_version="1",
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "federal_reserve",
        "country": "United States",
        "description": "FRED series metadata ordered by popularity",
    },
    retry_policy=dg.RetryPolicy(max_retries=3, delay=60),
)
def series_registry(
    context: dg.AssetExecutionContext,
    fred_api: FredApiResource,
) -> pd.DataFrame:
    """Fetch FRED series metadata ordered by popularity.

    Returns DataFrame with columns: id (index), title, popularity, frequency,
    units, seasonal_adjustment, observation_start, observation_end, etc.
    """
    context.log.info("Fetching FRED series registry...")

    results = fred_api.search_series(
        text="economic",
        limit=DEFAULT_SERIES_LIMIT,
        order_by="popularity",
        sort_order="desc",
    )

    # Reset index and rename 'id' column to 'series_id' for consistency
    # Note: fredapi returns 'id' column plus 'series id' as index name
    results = results.reset_index(drop=True).rename(columns={"id": "series_id"})

    context.add_output_metadata({
        "num_series": len(results),
        "popularity_min": int(results["popularity"].min()),
        "popularity_max": int(results["popularity"].max()),
        "top_10_series": results["series_id"].head(10).tolist(),
    })
    context.log.info(f"Registry complete: {len(results)} series")

    return results


@dg.asset(
    name="series",
    key_prefix=["bronze", "fred"],
    group_name="fred",
    code_version="2",  # Version bump for new architecture
    pool="fred_api",
    ins={
        "registry": dg.AssetIn(
            key=dg.AssetKey(["bronze", "fred", "series_registry"]),
        ),
    },
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "federal_reserve",
        "country": "United States",
        "description": "FRED timeseries data for top N series by popularity",
    },
    retry_policy=dg.RetryPolicy(max_retries=3, delay=60),
)
def series(
    context: dg.AssetExecutionContext,
    fred_api: FredApiResource,
    registry: pd.DataFrame,
) -> pd.DataFrame:
    """Fetch timeseries data for top N series by popularity.

    Materialization time: ~8-10 min for 1000 series (120 req/min rate limit).

    Returns:
        DataFrame with columns: date, value, series_id
    """
    # Get series IDs from registry
    series_ids = registry["series_id"].head(DEFAULT_SERIES_LIMIT).tolist()

    # Ensure core series are included (for backward compatibility)
    for core_id in CORE_SERIES_IDS:
        if core_id not in series_ids:
            series_ids.append(core_id)

    total = len(series_ids)
    context.log.info(f"Fetching {total} series (est. {total * 0.5 / 60:.1f} min)...")

    all_data = []
    failed_series = []
    start_time = time.time()

    for i, series_id in enumerate(series_ids):
        if i % 50 == 0 and i > 0:
            elapsed = time.time() - start_time
            rate = i / elapsed  # series per second
            remaining = (total - i) / rate if rate > 0 else 0
            context.log.info(
                f"Progress: {i}/{total} ({i / total * 100:.0f}%) - "
                f"{len(failed_series)} failed - "
                f"{remaining / 60:.1f} min remaining"
            )

        try:
            data = fred_api.get_series(series_id)

            if data is None or len(data) == 0:
                context.log.warning(f"No data for series {series_id}")
                failed_series.append(series_id)
                continue

            df = pd.DataFrame({
                "date": data.index,
                "value": data.values,
                "series_id": series_id,
            })
            all_data.append(df)

        except Exception as e:
            context.log.warning(f"Failed to fetch {series_id}: {e}")
            failed_series.append(series_id)
            continue

    if not all_data:
        raise ValueError("No series data fetched successfully")

    result = pd.concat(all_data, ignore_index=True)

    context.add_output_metadata({
        "num_records": len(result),
        "series_fetched": len(all_data),
        "series_failed": len(failed_series),
        "failed_series": failed_series[:20] if failed_series else [],
        "date_range_start": str(result["date"].min()),
        "date_range_end": str(result["date"].max()),
    })
    context.log.info(
        f"Complete: {len(all_data)} series fetched, {len(failed_series)} failed"
    )

    return result


# =============================================================================
# NOTE: Published assets moved to economic.py
# This allows unified routing between FRED (US) and World Bank (other countries)
# =============================================================================


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    "series_registry",  # Asset key: bronze/fred/series_registry
    "series",  # Asset key: bronze/fred/series
]
