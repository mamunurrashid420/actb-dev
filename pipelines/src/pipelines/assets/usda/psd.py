"""USDA FAS PSD data assets - bronze and silver layers.

Bronze layer:
- psd_bulk: Historical data from bulk CSV download (quarterly refresh)
- psd_current: Current year data from API (weekly refresh, rolling window)

Silver layer:
- psd_data: Merged bulk + current with computed metrics
"""

import datetime as dt
from datetime import date, timedelta

import dagster as dg
import polars as pl

from pipelines.assets.usda.common import ASSET_GROUP
from pipelines.resources import UsdaFasResource

# Concurrency key to respect 1,000 req/hr rate limit across all USDA FAS APIs
USDA_API_CONCURRENCY = {"dagster/concurrency_key": "usda_fas_api"}


# =============================================================================
# BRONZE LAYER
# =============================================================================


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="psd_bulk",
    group_name=ASSET_GROUP,
    op_tags=USDA_API_CONCURRENCY,
)
def bronze_psd_bulk(
    context: dg.AssetExecutionContext,
    usda_fas: UsdaFasResource,
) -> pl.LazyFrame:
    """Download complete PSD bulk data (all years except current).

    Source: Bulk CSV from PSD Online (https://apps.fas.usda.gov/psdonline/)
    Coverage: 1960 through (current_year - 1)
    Refresh: Quarterly (catches historical revisions, methodology updates)

    USDA revises historical data:
    - Monthly review cycle by interagency committee
    - Methodology updates applied retroactively
    """
    current_year = dt.datetime.now().year

    context.log.info("Downloading PSD bulk CSV...")
    lf = usda_fas.download_bulk_csv()

    # Filter to historical years only (lazy operation)
    schema = lf.collect_schema()
    if "market_year" in schema.names():
        lf = lf.filter(pl.col("market_year") < current_year)

    # Normalize schema - CSV may infer codes as integers, but they're identifiers
    lf = lf.with_columns([
        pl.col("commodity_code").cast(pl.Utf8),
        pl.col("country_code").cast(pl.Utf8),
    ])

    # Collect stats for metadata (small aggregation)
    stats = lf.select([
        pl.len().alias("count"),
        pl.col("market_year").min().alias("min_year"),
        pl.col("market_year").max().alias("max_year"),
        pl.col("commodity_code").n_unique().alias("n_commodities"),
        pl.col("country_code").n_unique().alias("n_countries"),
    ]).collect()

    context.add_output_metadata({
        "num_records": stats["count"][0],
        "year_range": f"{stats['min_year'][0]}-{stats['max_year'][0]}",
        "num_commodities": stats["n_commodities"][0],
        "num_countries": stats["n_countries"][0],
        "columns": list(schema.names()),
    })

    return lf


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="psd_current",
    group_name=ASSET_GROUP,
    op_tags=USDA_API_CONCURRENCY,
)
def bronze_psd_current(
    context: dg.AssetExecutionContext,
    usda_fas: UsdaFasResource,
) -> pl.LazyFrame:
    """Fetch recent PSD data via API (rolling window).

    Source: USDA FAS API (rate limit: 1,000 req/hr)
    Coverage: Full current year OR last 6 months (whichever is larger)
    Refresh: Weekly (catches monthly WASDE updates)

    Rolling window logic:
    - Oct 2025: Fetches Jan 2025 - Oct 2025 (full current year)
    - Jan 2026: Fetches Jul 2025 - Jan 2026 (6-month minimum)
    - Jul 2026: Fetches Jan 2026 - Jul 2026 (full current year)

    This ensures no data gaps during the January transition when bulk
    hasn't been refreshed yet.
    """
    today = dt.datetime.now()
    current_year_start = date(today.year, 1, 1)
    six_months_ago = (today - timedelta(days=180)).date()

    # Full current year OR last 6 months (whichever goes further back)
    start_date = min(current_year_start, six_months_ago)
    end_date = today.date()
    years = list(range(start_date.year, end_date.year + 1))

    context.log.info(f"Fetching PSD data for years {years}...")

    # Get commodity list as [(code, name), ...]
    commodities = (
        usda_fas
        .get_commodities()
        .collect()
        .select(["commodity_code", "commodity_name"])
        .rows()
    )

    if not commodities:
        context.log.warning("No commodities returned from API")
        return pl.LazyFrame()

    context.log.info(
        f"Fetching data for {len(commodities)} commodities across {len(years)} years..."
    )

    # Enumerate by commodity first, then by year (for better progress visibility)
    all_data: list[pl.LazyFrame] = []
    for i, (code, name) in enumerate(commodities):
        context.log.info(f"[{i + 1}/{len(commodities)}] Fetching {name or code}...")
        for year in years:
            lf = usda_fas.get_psd_by_commodity_year(code, year)
            schema = lf.collect_schema()
            if len(schema) > 0:
                all_data.append(lf)

    if not all_data:
        context.log.warning("No PSD data returned from API")
        return pl.LazyFrame()

    # Combine all results
    result = pl.concat(all_data, how="diagonal")

    # Normalize schema - API returns strings for numeric columns
    result = result.with_columns([
        pl.col("market_year").cast(pl.Int64),
        pl.col("calendar_year").cast(pl.Int64),
        pl.col("month").cast(pl.Int64),
    ])

    # Collect stats for metadata
    stats = result.select([
        pl.len().alias("count"),
        pl.col("commodity_code").n_unique().alias("n_commodities"),
    ]).collect()

    # Get unique market years separately
    market_years = (
        result
        .select(pl.col("market_year").unique().sort())
        .collect()["market_year"]
        .to_list()
    )

    context.add_output_metadata({
        "num_records": stats["count"][0],
        "years_fetched": years,
        "num_commodities": stats["n_commodities"][0],
        "commodities": [name or code for code, name in commodities],
        "market_years": market_years,
    })

    return result


# =============================================================================
# SILVER LAYER - COMPUTED METRICS
# =============================================================================


def compute_stocks_to_use(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Compute stocks-to-use ratio (critical supply indicator).

    stocks_to_use = ending_stocks / total_consumption * 100

    Interpretation:
    - < 15%: Tight market, upward price pressure
    - 15-25%: Normal/balanced market
    - > 25%: Ample supplies, downward price pressure
    """
    schema = lf.collect_schema()
    if (
        "ending_stocks" not in schema.names()
        or "domestic_consumption" not in schema.names()
    ):
        return lf

    return lf.with_columns(
        (pl.col("ending_stocks") / pl.col("domestic_consumption") * 100)
        .round(2)
        .alias("stocks_to_use")
    )


def compute_self_sufficiency(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Compute self-sufficiency ratio.

    self_sufficiency = production / domestic_consumption * 100

    Interpretation:
    - > 100%: Net exporter
    - < 100%: Net importer
    """
    schema = lf.collect_schema()
    if (
        "production" not in schema.names()
        or "domestic_consumption" not in schema.names()
    ):
        return lf

    return lf.with_columns(
        (pl.col("production") / pl.col("domestic_consumption") * 100)
        .round(2)
        .alias("self_sufficiency")
    )


def compute_yoy_changes(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Compute year-over-year changes for key metrics."""
    schema = lf.collect_schema()
    if "market_year" not in schema.names() or "production" not in schema.names():
        return lf

    group_cols = [c for c in ["commodity_code", "country_code"] if c in schema.names()]
    if not group_cols:
        return lf

    return lf.sort(group_cols + ["market_year"]).with_columns(
        (pl.col("production").pct_change().over(group_cols) * 100).alias(
            "production_yoy"
        )
    )


def compute_moving_averages(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Compute 3-year and 5-year moving averages for production."""
    schema = lf.collect_schema()
    if "market_year" not in schema.names() or "production" not in schema.names():
        return lf

    group_cols = [c for c in ["commodity_code", "country_code"] if c in schema.names()]
    if not group_cols:
        return lf

    return lf.sort(group_cols + ["market_year"]).with_columns([
        pl
        .col("production")
        .rolling_mean(3, min_periods=1)
        .over(group_cols)
        .alias("production_ma_3yr"),
        pl
        .col("production")
        .rolling_mean(5, min_periods=1)
        .over(group_cols)
        .alias("production_ma_5yr"),
    ])


@dg.asset(
    key_prefix=["silver", "usda"],
    name="psd_data",
    group_name=ASSET_GROUP,
    automation_condition=dg.AutomationCondition.all_deps_updated_since_cron(
        "0 * * * *"  # Hourly check, runs when bronze deps complete
    ),
    ins={
        "bronze_usda_psd_bulk": dg.AssetIn(
            key=dg.AssetKey(["bronze", "usda", "psd_bulk"]),
        ),
        "bronze_usda_psd_current": dg.AssetIn(
            key=dg.AssetKey(["bronze", "usda", "psd_current"]),
        ),
    },
)
def silver_psd_data(
    context: dg.AssetExecutionContext,
    bronze_usda_psd_bulk: pl.LazyFrame,
    bronze_usda_psd_current: pl.LazyFrame,
) -> pl.LazyFrame:
    """Merge bulk + current PSD data, compute derived metrics.

    Merge logic:
    - psd_current is fresher (weekly refresh) - use for overlapping periods
    - psd_bulk fills in historical data not covered by current

    Computed metrics:
    - stocks_to_use: Ending stocks / consumption ratio
    - self_sufficiency: Production / consumption ratio
    - production_yoy: Year-over-year production change %
    - production_ma_3yr, production_ma_5yr: Moving averages
    """
    bulk_schema = bronze_usda_psd_bulk.collect_schema()
    current_schema = bronze_usda_psd_current.collect_schema()

    # Handle empty and edge cases with flat if/elif/else
    if len(bulk_schema) == 0 and len(current_schema) == 0:
        context.log.warning("Both bulk and current PSD data are empty")
        return pl.LazyFrame()
    elif len(current_schema) == 0:
        context.log.info("Current PSD data is empty, using only bulk data")
        lf = bronze_usda_psd_bulk
    elif len(bulk_schema) == 0:
        context.log.info("Bulk PSD data is empty, using only current data")
        lf = bronze_usda_psd_current
    elif "market_year" not in current_schema.names():
        # Can't determine overlap without market_year, use current only
        context.log.info("No market_year column, using only current data")
        lf = bronze_usda_psd_current
    else:
        # Full merge: historical from bulk + fresh from current
        current_min_year = (
            bronze_usda_psd_current.select(pl.col("market_year").min()).collect().item()
        )

        historical = bronze_usda_psd_bulk.filter(
            pl.col("market_year") < current_min_year
        )

        context.log.info(f"Merging: historical (< {current_min_year}) + current data")
        lf = pl.concat([historical, bronze_usda_psd_current], how="diagonal")

    # Apply computed metrics (all lazy)
    lf = (
        lf
        .pipe(compute_stocks_to_use)
        .pipe(compute_self_sufficiency)
        .pipe(compute_yoy_changes)
        .pipe(compute_moving_averages)
    )

    # Metadata (schema only, no full collect)
    schema = lf.collect_schema()
    computed_columns = [
        c
        for c in schema.names()
        if c
        in [
            "stocks_to_use",
            "self_sufficiency",
            "production_yoy",
            "production_ma_3yr",
            "production_ma_5yr",
        ]
    ]

    context.add_output_metadata({
        "processing_mode": "streaming",
        "num_columns": len(schema),
        "columns": list(schema.names()),
        "computed_columns": computed_columns,
    })

    return lf


__all__ = [
    "bronze_psd_bulk",
    "bronze_psd_current",
    "silver_psd_data",
]
