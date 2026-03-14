"""USDA FAS registry assets - commodity and country lookup tables.

Extracted from bulk CSV data since API requires special authentication.
"""

import dagster as dg
import polars as pl

from pipelines.assets.usda.common import ASSET_GROUP


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="commodities",
    group_name=ASSET_GROUP,
    ins={
        "bronze_usda_psd_bulk": dg.AssetIn(
            key=dg.AssetKey(["bronze", "usda", "psd_bulk"]),
        ),
    },
)
def bronze_commodities(
    context: dg.AssetExecutionContext,
    bronze_usda_psd_bulk: pl.LazyFrame,
) -> pl.LazyFrame:
    """Extract USDA commodity registry from bulk data.

    Source: Derived from bronze/usda/psd_bulk
    Refresh: After bulk refresh (quarterly)
    """
    context.log.info("Extracting commodity registry from bulk data...")

    lf = (
        bronze_usda_psd_bulk
        .select(["commodity_code", "commodity_description"])
        .unique()
        .rename({"commodity_description": "commodity_name"})
        .sort("commodity_code")
    )

    # Collect stats for metadata (small aggregation)
    stats = lf.select(pl.len().alias("count")).collect()

    context.add_output_metadata({
        "num_commodities": stats["count"][0],
    })

    return lf


@dg.asset(
    key_prefix=["bronze", "usda"],
    name="countries",
    group_name=ASSET_GROUP,
    ins={
        "bronze_usda_psd_bulk": dg.AssetIn(
            key=dg.AssetKey(["bronze", "usda", "psd_bulk"]),
        ),
    },
)
def bronze_countries(
    context: dg.AssetExecutionContext,
    bronze_usda_psd_bulk: pl.LazyFrame,
) -> pl.LazyFrame:
    """Extract USDA country registry from bulk data.

    Source: Derived from bronze/usda/psd_bulk
    Refresh: After bulk refresh (quarterly)
    """
    context.log.info("Extracting country registry from bulk data...")

    lf = (
        bronze_usda_psd_bulk
        .select(["country_code", "country_name"])
        .unique()
        .sort("country_code")
    )

    # Collect stats for metadata (small aggregation)
    stats = lf.select(pl.len().alias("count")).collect()

    context.add_output_metadata({
        "num_countries": stats["count"][0],
    })

    return lf


__all__ = [
    "bronze_commodities",
    "bronze_countries",
]
