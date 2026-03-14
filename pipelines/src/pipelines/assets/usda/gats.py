"""USDA FAS Global Agricultural Trade System (GATS) assets.

Bronze layer:
- Reference data: gats_regions, gats_countries, gats_commodities, gats_hs6_commodities,
                  gats_units, gats_customs_districts
- Census data: gats_census_imports, gats_census_exports, gats_census_reexports
               (US Census Bureau monthly trade data, rolling 12-month window)
- UN Trade data: gats_untrade_imports, gats_untrade_exports, gats_untrade_reexports
                 (UN ComTrade annual data, 140+ reporter countries)

GATS data is released monthly (Census) and annually (UN Trade).

Rate limit: All assets share 'usda_fas_api' concurrency key (1,000 req/hr).
"""

import datetime as dt

import dagster as dg
import polars as pl

from pipelines.assets.usda.common import ASSET_GROUP
from pipelines.partitions import gats_census_month_partitions
from pipelines.resources import UsdaFasResource

# Concurrency key to respect 1,000 req/hr rate limit across all USDA FAS APIs
USDA_API_CONCURRENCY = {"dagster/concurrency_key": "usda_fas_api"}


# =============================================================================
# BRONZE LAYER - Reference Data
# =============================================================================


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="gats_regions",
    group_name=ASSET_GROUP,
    op_tags=USDA_API_CONCURRENCY,
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "usda_fas",
        "description": "GATS region reference data",
    },
)
def bronze_gats_regions(
    context: dg.AssetExecutionContext,
    usda_fas: UsdaFasResource,
) -> pl.LazyFrame:
    """Fetch GATS region reference data."""
    context.log.info("Fetching GATS regions...")
    lf = usda_fas.get_gats_regions()

    count = lf.select(pl.len()).collect().item()
    context.add_output_metadata({"num_regions": count})

    return lf


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="gats_countries",
    group_name=ASSET_GROUP,
    op_tags=USDA_API_CONCURRENCY,
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "usda_fas",
        "description": "GATS country reference data",
    },
)
def bronze_gats_countries(
    context: dg.AssetExecutionContext,
    usda_fas: UsdaFasResource,
) -> pl.LazyFrame:
    """Fetch GATS country reference data with region codes."""
    context.log.info("Fetching GATS countries...")
    lf = usda_fas.get_gats_countries()

    count = lf.select(pl.len()).collect().item()
    context.add_output_metadata({"num_countries": count})

    return lf


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="gats_commodities",
    group_name=ASSET_GROUP,
    op_tags=USDA_API_CONCURRENCY,
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "usda_fas",
        "description": "GATS commodity reference data (HS10 level)",
    },
)
def bronze_gats_commodities(
    context: dg.AssetExecutionContext,
    usda_fas: UsdaFasResource,
) -> pl.LazyFrame:
    """Fetch GATS commodity reference data (HS10 level)."""
    context.log.info("Fetching GATS commodities (HS10)...")
    lf = usda_fas.get_gats_commodities()

    count = lf.select(pl.len()).collect().item()
    context.add_output_metadata({"num_commodities": count})

    return lf


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="gats_hs6_commodities",
    group_name=ASSET_GROUP,
    op_tags=USDA_API_CONCURRENCY,
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "usda_fas",
        "description": "GATS HS6-level commodity registry",
    },
)
def bronze_gats_hs6_commodities(
    context: dg.AssetExecutionContext,
    usda_fas: UsdaFasResource,
) -> pl.LazyFrame:
    """Fetch GATS HS6-level commodity registry (for UN Trade correlation)."""
    context.log.info("Fetching GATS HS6 commodities...")
    lf = usda_fas.get_gats_hs6_commodities()

    count = lf.select(pl.len()).collect().item()
    context.add_output_metadata({"num_hs6_commodities": count})

    return lf


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="gats_units",
    group_name=ASSET_GROUP,
    op_tags=USDA_API_CONCURRENCY,
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "usda_fas",
        "description": "GATS units of measure reference data",
    },
)
def bronze_gats_units(
    context: dg.AssetExecutionContext,
    usda_fas: UsdaFasResource,
) -> pl.LazyFrame:
    """Fetch GATS units of measure reference data."""
    context.log.info("Fetching GATS units of measure...")
    lf = usda_fas.get_gats_units_of_measure()

    count = lf.select(pl.len()).collect().item()
    context.add_output_metadata({"num_units": count})

    return lf


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="gats_customs_districts",
    group_name=ASSET_GROUP,
    op_tags=USDA_API_CONCURRENCY,
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "usda_fas",
        "description": "GATS US Customs Districts for entry/exit points",
    },
)
def bronze_gats_customs_districts(
    context: dg.AssetExecutionContext,
    usda_fas: UsdaFasResource,
) -> pl.LazyFrame:
    """Fetch GATS US Customs Districts for entry/exit points."""
    context.log.info("Fetching GATS customs districts...")
    lf = usda_fas.get_gats_customs_districts()

    count = lf.select(pl.len()).collect().item()
    context.add_output_metadata({"num_districts": count})

    return lf


# =============================================================================
# BRONZE LAYER - Census Trade Data (Monthly Partitions)
# =============================================================================


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="gats_census_imports",
    group_name=ASSET_GROUP,
    partitions_def=gats_census_month_partitions,
    op_tags=USDA_API_CONCURRENCY,
    deps=[dg.AssetKey(["bronze", "usda", "gats_countries"])],
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "usda_fas",
        "description": "US Census import data by month",
    },
)
def bronze_gats_census_imports(
    context: dg.AssetExecutionContext,
    usda_fas: UsdaFasResource,
) -> pl.LazyFrame:
    """Fetch US Census import data for a single month partition.

    Each partition represents one month (e.g., '2025-01'). Fetches data from
    all partner countries for that month, resulting in ~200 API calls per partition.

    Note: This asset uses gats_countries as a dependency to ensure country
    registry is available, but fetches country list directly via API to
    avoid circular dependency issues.
    """
    year, month = map(int, context.partition_key.split("-"))

    # Get partner countries list
    partners_lf = usda_fas.get_gats_countries()
    partners = partners_lf.collect()["country_code"].to_list()

    if not partners:
        context.log.warning("No GATS partners found")
        return pl.LazyFrame()

    context.log.info(
        f"Fetching Census imports for {context.partition_key} "
        f"({len(partners)} partners)..."
    )

    all_data: list[pl.LazyFrame] = []
    request_count = 0

    for partner_code in partners:
        request_count += 1
        if request_count % 50 == 0:
            context.log.info(f"Progress: {request_count}/{len(partners)} partners")

        lf = usda_fas.get_gats_census_imports(partner_code, year, month)
        schema = lf.collect_schema()
        if len(schema) > 0:
            all_data.append(lf)

    if not all_data:
        context.log.warning(
            f"No Census import data returned for {context.partition_key}"
        )
        return pl.LazyFrame()

    result = pl.concat(all_data, how="diagonal")

    # Collect stats for metadata
    stats = result.select([
        pl.len().alias("count"),
        pl.col("partner_code").n_unique().alias("n_partners"),
    ]).collect()

    context.add_output_metadata({
        "num_records": stats["count"][0],
        "partition": context.partition_key,
        "num_partners": stats["n_partners"][0],
        "api_requests": request_count,
    })

    return result


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="gats_census_exports",
    group_name=ASSET_GROUP,
    partitions_def=gats_census_month_partitions,
    op_tags=USDA_API_CONCURRENCY,
    deps=[dg.AssetKey(["bronze", "usda", "gats_countries"])],
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "usda_fas",
        "description": "US Census export data by month",
    },
)
def bronze_gats_census_exports(
    context: dg.AssetExecutionContext,
    usda_fas: UsdaFasResource,
) -> pl.LazyFrame:
    """Fetch US Census export data for a single month partition."""
    year, month = map(int, context.partition_key.split("-"))

    # Get partner countries list
    partners_lf = usda_fas.get_gats_countries()
    partners = partners_lf.collect()["country_code"].to_list()

    if not partners:
        context.log.warning("No GATS partners found")
        return pl.LazyFrame()

    context.log.info(
        f"Fetching Census exports for {context.partition_key} "
        f"({len(partners)} partners)..."
    )

    all_data: list[pl.LazyFrame] = []
    request_count = 0

    for partner_code in partners:
        request_count += 1
        if request_count % 50 == 0:
            context.log.info(f"Progress: {request_count}/{len(partners)} partners")

        lf = usda_fas.get_gats_census_exports(partner_code, year, month)
        schema = lf.collect_schema()
        if len(schema) > 0:
            all_data.append(lf)

    if not all_data:
        context.log.warning(
            f"No Census export data returned for {context.partition_key}"
        )
        return pl.LazyFrame()

    result = pl.concat(all_data, how="diagonal")

    stats = result.select([
        pl.len().alias("count"),
        pl.col("partner_code").n_unique().alias("n_partners"),
    ]).collect()

    context.add_output_metadata({
        "num_records": stats["count"][0],
        "partition": context.partition_key,
        "num_partners": stats["n_partners"][0],
        "api_requests": request_count,
    })

    return result


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="gats_census_reexports",
    group_name=ASSET_GROUP,
    partitions_def=gats_census_month_partitions,
    op_tags=USDA_API_CONCURRENCY,
    deps=[dg.AssetKey(["bronze", "usda", "gats_countries"])],
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "usda_fas",
        "description": "US Census re-export data by month",
    },
)
def bronze_gats_census_reexports(
    context: dg.AssetExecutionContext,
    usda_fas: UsdaFasResource,
) -> pl.LazyFrame:
    """Fetch US Census re-export data for a single month partition."""
    year, month = map(int, context.partition_key.split("-"))

    # Get partner countries list
    partners_lf = usda_fas.get_gats_countries()
    partners = partners_lf.collect()["country_code"].to_list()

    if not partners:
        context.log.warning("No GATS partners found")
        return pl.LazyFrame()

    context.log.info(
        f"Fetching Census re-exports for {context.partition_key} "
        f"({len(partners)} partners)..."
    )

    all_data: list[pl.LazyFrame] = []
    request_count = 0

    for partner_code in partners:
        request_count += 1
        if request_count % 50 == 0:
            context.log.info(f"Progress: {request_count}/{len(partners)} partners")

        lf = usda_fas.get_gats_census_reexports(partner_code, year, month)
        schema = lf.collect_schema()
        if len(schema) > 0:
            all_data.append(lf)

    if not all_data:
        context.log.warning(
            f"No Census re-export data returned for {context.partition_key}"
        )
        return pl.LazyFrame()

    result = pl.concat(all_data, how="diagonal")

    stats = result.select([
        pl.len().alias("count"),
        pl.col("partner_code").n_unique().alias("n_partners"),
    ]).collect()

    context.add_output_metadata({
        "num_records": stats["count"][0],
        "partition": context.partition_key,
        "num_partners": stats["n_partners"][0],
        "api_requests": request_count,
    })

    return result


# =============================================================================
# SILVER LAYER - Aggregated Census Trade Data
# =============================================================================


@dg.asset(
    key_prefix=["silver", "usda"],
    name="gats_census_data",
    group_name=ASSET_GROUP,
    ins={
        "bronze_imports": dg.AssetIn(
            key=["bronze", "usda", "gats_census_imports"],
            partition_mapping=dg.AllPartitionMapping(),
        ),
        "bronze_exports": dg.AssetIn(
            key=["bronze", "usda", "gats_census_exports"],
            partition_mapping=dg.AllPartitionMapping(),
        ),
        "bronze_reexports": dg.AssetIn(
            key=["bronze", "usda", "gats_census_reexports"],
            partition_mapping=dg.AllPartitionMapping(),
        ),
    },
    metadata={
        "layer": "silver",
        "visibility": "internal",
        "source": "usda_fas",
        "description": "Aggregated Census trade data (imports, exports, re-exports)",
    },
)
def silver_gats_census_data(
    context: dg.AssetExecutionContext,
    bronze_imports: dict[str, pl.LazyFrame],
    bronze_exports: dict[str, pl.LazyFrame],
    bronze_reexports: dict[str, pl.LazyFrame],
) -> pl.LazyFrame:
    """Aggregate all Census trade data from monthly partitions.

    Combines imports, exports, and re-exports across all months into a single
    dataset with a trade_type column for analysis.
    """
    all_data: list[pl.LazyFrame] = []

    # Process imports
    for partition_key, lf in bronze_imports.items():
        schema = lf.collect_schema()
        if len(schema) > 0:
            all_data.append(
                lf.with_columns([
                    pl.lit("import").alias("trade_type"),
                    pl.lit(partition_key).alias("partition"),
                ])
            )

    # Process exports
    for partition_key, lf in bronze_exports.items():
        schema = lf.collect_schema()
        if len(schema) > 0:
            all_data.append(
                lf.with_columns([
                    pl.lit("export").alias("trade_type"),
                    pl.lit(partition_key).alias("partition"),
                ])
            )

    # Process re-exports
    for partition_key, lf in bronze_reexports.items():
        schema = lf.collect_schema()
        if len(schema) > 0:
            all_data.append(
                lf.with_columns([
                    pl.lit("reexport").alias("trade_type"),
                    pl.lit(partition_key).alias("partition"),
                ])
            )

    if not all_data:
        context.log.warning("No Census trade data available")
        return pl.LazyFrame()

    context.log.info(
        f"Aggregating Census data: {len(bronze_imports)} import partitions, "
        f"{len(bronze_exports)} export partitions, "
        f"{len(bronze_reexports)} re-export partitions"
    )

    result = pl.concat(all_data, how="diagonal")

    # Collect stats for metadata
    stats = result.select([
        pl.len().alias("count"),
        pl.col("partner_code").n_unique().alias("n_partners"),
        pl.col("trade_type").n_unique().alias("n_trade_types"),
        pl.col("partition").n_unique().alias("n_months"),
    ]).collect()

    context.add_output_metadata({
        "num_records": stats["count"][0],
        "num_partners": stats["n_partners"][0],
        "num_trade_types": stats["n_trade_types"][0],
        "num_months": stats["n_months"][0],
        "import_partitions": len(bronze_imports),
        "export_partitions": len(bronze_exports),
        "reexport_partitions": len(bronze_reexports),
    })

    return result


# =============================================================================
# BRONZE LAYER - UN Trade Data (Annual, All Reporters)
# =============================================================================


# Top 50 agricultural trading countries (reduces API calls from 140+ to 50)
# Includes major coffee importers/exporters relevant to Illy use case
UN_TRADE_REPORTERS = [
    # Americas
    "842",  # USA
    "124",  # Canada
    "484",  # Mexico
    "076",  # Brazil
    "032",  # Argentina
    "170",  # Colombia
    "604",  # Peru
    "152",  # Chile
    # Europe
    "276",  # Germany
    "826",  # United Kingdom
    "250",  # France
    "380",  # Italy
    "528",  # Netherlands
    "056",  # Belgium
    "724",  # Spain
    "616",  # Poland
    "040",  # Austria
    "756",  # Switzerland
    # Asia-Pacific
    "156",  # China
    "392",  # Japan
    "410",  # South Korea
    "356",  # India
    "360",  # Indonesia
    "704",  # Vietnam
    "764",  # Thailand
    "458",  # Malaysia
    "608",  # Philippines
    "036",  # Australia
    "554",  # New Zealand
    # Middle East & Africa
    "682",  # Saudi Arabia
    "784",  # UAE
    "792",  # Turkey
    "818",  # Egypt
    "710",  # South Africa
    "566",  # Nigeria
    "404",  # Kenya
    "231",  # Ethiopia
    # Coffee-specific exporters
    "320",  # Guatemala
    "340",  # Honduras
    "188",  # Costa Rica
    "862",  # Venezuela
    "800",  # Uganda
]


def _get_recent_years(num_years: int = 3) -> list[int]:
    """Get recent calendar years for UN Trade data."""
    current_year = dt.datetime.now().year
    # UN Trade data typically lags 1-2 years
    return list(range(current_year - num_years - 1, current_year - 1))


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="gats_untrade_imports",
    group_name=ASSET_GROUP,
    op_tags=USDA_API_CONCURRENCY,
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "usda_fas",
        "description": "UN Trade import data for major trading countries",
    },
)
def bronze_gats_untrade_imports(
    context: dg.AssetExecutionContext,
    usda_fas: UsdaFasResource,
) -> pl.LazyFrame:
    """Fetch UN Trade import data for major trading countries.

    This fetches import data from top 50 reporter countries for recent years.
    Uses GATS UN Trade API which provides annual trade data at HS6 commodity level.
    """
    reporters = UN_TRADE_REPORTERS
    years = _get_recent_years(3)
    total_requests = len(reporters) * len(years)

    context.log.info(
        f"Fetching UN Trade imports for {len(reporters)} reporters "
        f"across {len(years)} years (~{total_requests} requests)..."
    )

    all_data: list[pl.LazyFrame] = []
    request_count = 0

    for reporter_code in reporters:
        for year in years:
            request_count += 1
            if request_count % 20 == 0:
                context.log.info(f"Progress: {request_count}/{total_requests} requests")

            lf = usda_fas.get_gats_untrade_imports(reporter_code, year)
            schema = lf.collect_schema()
            if len(schema) > 0:
                all_data.append(lf)

    if not all_data:
        context.log.warning("No UN Trade import data returned")
        return pl.LazyFrame()

    result = pl.concat(all_data, how="diagonal")

    stats = result.select([
        pl.len().alias("count"),
        pl.col("reporter_code").n_unique().alias("n_reporters"),
    ]).collect()

    context.add_output_metadata({
        "num_records": stats["count"][0],
        "num_reporters": stats["n_reporters"][0],
        "years_fetched": years,
        "api_requests": request_count,
    })

    return result


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="gats_untrade_exports",
    group_name=ASSET_GROUP,
    op_tags=USDA_API_CONCURRENCY,
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "usda_fas",
        "description": "UN Trade export data for major trading countries",
    },
)
def bronze_gats_untrade_exports(
    context: dg.AssetExecutionContext,
    usda_fas: UsdaFasResource,
) -> pl.LazyFrame:
    """Fetch UN Trade export data for major trading countries."""
    reporters = UN_TRADE_REPORTERS
    years = _get_recent_years(3)
    total_requests = len(reporters) * len(years)

    context.log.info(
        f"Fetching UN Trade exports for {len(reporters)} reporters "
        f"across {len(years)} years (~{total_requests} requests)..."
    )

    all_data: list[pl.LazyFrame] = []
    request_count = 0

    for reporter_code in reporters:
        for year in years:
            request_count += 1
            if request_count % 20 == 0:
                context.log.info(f"Progress: {request_count}/{total_requests} requests")

            lf = usda_fas.get_gats_untrade_exports(reporter_code, year)
            schema = lf.collect_schema()
            if len(schema) > 0:
                all_data.append(lf)

    if not all_data:
        context.log.warning("No UN Trade export data returned")
        return pl.LazyFrame()

    result = pl.concat(all_data, how="diagonal")

    stats = result.select([
        pl.len().alias("count"),
        pl.col("reporter_code").n_unique().alias("n_reporters"),
    ]).collect()

    context.add_output_metadata({
        "num_records": stats["count"][0],
        "num_reporters": stats["n_reporters"][0],
        "years_fetched": years,
        "api_requests": request_count,
    })

    return result


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="gats_untrade_reexports",
    group_name=ASSET_GROUP,
    op_tags=USDA_API_CONCURRENCY,
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "usda_fas",
        "description": "UN Trade re-export data for major trading countries",
    },
)
def bronze_gats_untrade_reexports(
    context: dg.AssetExecutionContext,
    usda_fas: UsdaFasResource,
) -> pl.LazyFrame:
    """Fetch UN Trade re-export data for major trading countries."""
    reporters = UN_TRADE_REPORTERS
    years = _get_recent_years(3)
    total_requests = len(reporters) * len(years)

    context.log.info(
        f"Fetching UN Trade re-exports for {len(reporters)} reporters "
        f"across {len(years)} years (~{total_requests} requests)..."
    )

    all_data: list[pl.LazyFrame] = []
    request_count = 0

    for reporter_code in reporters:
        for year in years:
            request_count += 1
            if request_count % 20 == 0:
                context.log.info(f"Progress: {request_count}/{total_requests} requests")

            lf = usda_fas.get_gats_untrade_reexports(reporter_code, year)
            schema = lf.collect_schema()
            if len(schema) > 0:
                all_data.append(lf)

    if not all_data:
        context.log.warning("No UN Trade re-export data returned")
        return pl.LazyFrame()

    result = pl.concat(all_data, how="diagonal")

    stats = result.select([
        pl.len().alias("count"),
        pl.col("reporter_code").n_unique().alias("n_reporters"),
    ]).collect()

    context.add_output_metadata({
        "num_records": stats["count"][0],
        "num_reporters": stats["n_reporters"][0],
        "years_fetched": years,
        "api_requests": request_count,
    })

    return result


__all__ = [
    # Reference assets
    "bronze_gats_regions",
    "bronze_gats_countries",
    "bronze_gats_commodities",
    "bronze_gats_hs6_commodities",
    "bronze_gats_units",
    "bronze_gats_customs_districts",
    # Census trade data (bronze)
    "bronze_gats_census_imports",
    "bronze_gats_census_exports",
    "bronze_gats_census_reexports",
    # Census trade data (silver)
    "silver_gats_census_data",
    # UN Trade data
    "bronze_gats_untrade_imports",
    "bronze_gats_untrade_exports",
    "bronze_gats_untrade_reexports",
]
