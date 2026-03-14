"""USDA FAS Export Sales Reports (ESR) assets.

Bronze layer:
- esr_regions: Region reference data
- esr_countries: Country reference data with region codes
- esr_commodities: Commodity reference data
- esr_units: Units of measure reference data
- esr_exports: Weekly US export sales data (partitioned by market year)

Silver layer:
- esr_data: Aggregated export data with computed metrics (all market years)

ESR data is published weekly on Thursdays at 8:30 AM ET.
Historical data available from 1990-present via API.
"""

import dagster as dg
import polars as pl

from pipelines.assets.usda.common import ASSET_GROUP
from pipelines.partitions import esr_market_year_partitions
from pipelines.resources import UsdaFasResource

# Concurrency key to respect 1,000 req/hr rate limit across all USDA FAS APIs
USDA_API_CONCURRENCY = {"dagster/concurrency_key": "usda_fas_api"}


# =============================================================================
# BRONZE LAYER - Reference Data
# =============================================================================


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="esr_regions",
    group_name=ASSET_GROUP,
    op_tags=USDA_API_CONCURRENCY,
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "usda_fas",
        "description": "ESR region reference data",
    },
)
def bronze_esr_regions(
    context: dg.AssetExecutionContext,
    usda_fas: UsdaFasResource,
) -> pl.LazyFrame:
    """Fetch ESR region reference data."""
    context.log.info("Fetching ESR regions...")
    lf = usda_fas.get_esr_regions()

    count = lf.select(pl.len()).collect().item()
    context.add_output_metadata({"num_regions": count})

    return lf


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="esr_countries",
    group_name=ASSET_GROUP,
    op_tags=USDA_API_CONCURRENCY,
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "usda_fas",
        "description": "ESR country reference data with region codes",
    },
)
def bronze_esr_countries(
    context: dg.AssetExecutionContext,
    usda_fas: UsdaFasResource,
) -> pl.LazyFrame:
    """Fetch ESR country reference data with region codes."""
    context.log.info("Fetching ESR countries...")
    lf = usda_fas.get_esr_countries()

    count = lf.select(pl.len()).collect().item()
    context.add_output_metadata({"num_countries": count})

    return lf


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="esr_commodities",
    group_name=ASSET_GROUP,
    op_tags=USDA_API_CONCURRENCY,
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "usda_fas",
        "description": "ESR commodity reference data",
    },
)
def bronze_esr_commodities(
    context: dg.AssetExecutionContext,
    usda_fas: UsdaFasResource,
) -> pl.LazyFrame:
    """Fetch ESR commodity reference data."""
    context.log.info("Fetching ESR commodities...")
    lf = usda_fas.get_esr_commodities()

    count = lf.select(pl.len()).collect().item()
    context.add_output_metadata({"num_commodities": count})

    return lf


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="esr_units",
    group_name=ASSET_GROUP,
    op_tags=USDA_API_CONCURRENCY,
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "usda_fas",
        "description": "ESR units of measure reference data",
    },
)
def bronze_esr_units(
    context: dg.AssetExecutionContext,
    usda_fas: UsdaFasResource,
) -> pl.LazyFrame:
    """Fetch ESR units of measure reference data."""
    context.log.info("Fetching ESR units of measure...")
    lf = usda_fas.get_esr_units_of_measure()

    count = lf.select(pl.len()).collect().item()
    context.add_output_metadata({"num_units": count})

    return lf


# =============================================================================
# BRONZE LAYER - Export Data
# =============================================================================


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="esr_exports",
    group_name=ASSET_GROUP,
    partitions_def=esr_market_year_partitions,
    op_tags=USDA_API_CONCURRENCY,
    deps=[dg.AssetKey(["bronze", "usda", "esr_commodities"])],
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "usda_fas",
        "description": "Weekly US export sales data by market year",
    },
)
def bronze_esr_exports(
    context: dg.AssetExecutionContext,
    usda_fas: UsdaFasResource,
) -> pl.LazyFrame:
    """Fetch weekly US export sales data for a single market year.

    Each partition represents one market year (1990-2025). All commodities
    are fetched for that year, resulting in ~44 API calls per partition.

    Note: This asset uses esr_commodities as a dependency to ensure commodity
    registry is available, but fetches commodity list directly via API to
    avoid circular dependency issues.
    """
    market_year = int(context.partition_key)

    # Get commodity list from API
    commodities_lf = usda_fas.get_esr_commodities()
    commodities = commodities_lf.collect()["commodity_code"].to_list()

    if not commodities:
        context.log.warning("No ESR commodities found")
        return pl.LazyFrame()

    context.log.info(
        f"Fetching ESR exports for market year {market_year} "
        f"({len(commodities)} commodities)..."
    )

    all_data: list[pl.LazyFrame] = []
    request_count = 0

    for commodity_code in commodities:
        request_count += 1
        if request_count % 10 == 0:
            context.log.info(
                f"Progress: {request_count}/{len(commodities)} commodities"
            )

        lf = usda_fas.get_esr_exports(commodity_code, market_year)
        schema = lf.collect_schema()
        if len(schema) > 0:
            all_data.append(lf)

    if not all_data:
        context.log.warning(
            f"No ESR export data returned for market year {market_year}"
        )
        return pl.LazyFrame()

    result = pl.concat(all_data, how="diagonal")

    # Collect stats for metadata
    stats = result.select([
        pl.len().alias("count"),
        pl.col("commodity_code").n_unique().alias("n_commodities"),
        pl.col("country_code").n_unique().alias("n_countries"),
    ]).collect()

    context.add_output_metadata({
        "num_records": stats["count"][0],
        "market_year": market_year,
        "num_commodities": stats["n_commodities"][0],
        "num_countries": stats["n_countries"][0],
        "api_requests": request_count,
    })

    return result


# =============================================================================
# SILVER LAYER - Aggregated Data
# =============================================================================


@dg.asset(
    key_prefix=["silver", "usda"],
    name="esr_data",
    group_name=ASSET_GROUP,
    ins={
        "bronze_exports": dg.AssetIn(
            key=["bronze", "usda", "esr_exports"],
            partition_mapping=dg.AllPartitionMapping(),
        ),
    },
    metadata={
        "layer": "silver",
        "visibility": "internal",
        "source": "usda_fas",
        "description": "Aggregated export data with computed metrics",
    },
)
def silver_esr_data(
    context: dg.AssetExecutionContext,
    bronze_exports: dict[str, pl.LazyFrame],
) -> pl.LazyFrame:
    """Aggregate all market years into single dataset with computed metrics.

    Combines partitioned bronze data (1990-present) into a single comprehensive
    export sales dataset. Adds year-over-year growth and market share metrics.
    """
    if not bronze_exports:
        context.log.warning("No ESR export data available")
        return pl.LazyFrame()

    context.log.info(f"Aggregating {len(bronze_exports)} market years...")

    # Concatenate all partitions
    all_data = pl.concat(
        list(bronze_exports.values()),
        how="diagonal",
    )

    # Calculate year-over-year growth by commodity/country
    result = all_data.sort([
        "commodity_code",
        "country_code",
        "week_ending_date",
    ]).with_columns([
        # Week-over-week change
        (pl.col("weekly_exports") - pl.col("weekly_exports").shift(1))
        .over(["commodity_code", "country_code"])
        .alias("weekly_exports_change"),
        # Cumulative exports for market share calculation
        pl
        .col("weekly_exports")
        .cum_sum()
        .over(["commodity_code", "market_year"])
        .alias("cumulative_exports"),
    ])

    # Collect stats for metadata
    stats = result.select([
        pl.len().alias("count"),
        pl.col("commodity_code").n_unique().alias("n_commodities"),
        pl.col("country_code").n_unique().alias("n_countries"),
        pl.col("market_year").n_unique().alias("n_years"),
        pl.col("market_year").min().alias("min_year"),
        pl.col("market_year").max().alias("max_year"),
    ]).collect()

    context.add_output_metadata({
        "num_records": stats["count"][0],
        "num_commodities": stats["n_commodities"][0],
        "num_countries": stats["n_countries"][0],
        "num_market_years": stats["n_years"][0],
        "date_range": f"{stats['min_year'][0]}-{stats['max_year'][0]}",
    })

    return result


__all__ = [
    "bronze_esr_regions",
    "bronze_esr_countries",
    "bronze_esr_commodities",
    "bronze_esr_units",
    "bronze_esr_exports",
    "silver_esr_data",
]
