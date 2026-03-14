"""SEC filer registry assets - CIK↔ticker mapping and filtering.

This module contains the registry assets that provide CIK↔ticker mappings
and filter to config-enabled companies and institutions.

Architecture:
- Bronze: sec_filer_registry - Complete SEC CIK↔ticker mapping
- Silver: company_registry - Filtered to config-enabled tickers
- Silver: institution_registry - Filtered to config-enabled institutions
"""

import dagster as dg
import pandas as pd

from pipelines.assets.sec.common import ASSET_GROUP
from pipelines.config import get_sec_enabled_companies, get_sec_enabled_institutions
from pipelines.resources import SecEdgarResource

# =============================================================================
# BRONZE LAYER - Complete SEC Registry
# =============================================================================


@dg.asset(
    key_prefix=["bronze", "sec"],
    name="sec_filer_registry",
    group_name=ASSET_GROUP,
    metadata={
        "layer": "bronze",
        "source": "sec_edgar",
        "component": "company_tickers",
        "visibility": "internal",
    },
)
def sec_filer_registry(
    context: dg.AssetExecutionContext,
    sec_edgar: SecEdgarResource,
) -> pd.DataFrame:
    """Fetch SEC's complete CIK↔ticker mapping from company_tickers.json.

    Source: https://www.sec.gov/files/company_tickers.json

    Returns:
        DataFrame with columns: cik, ticker, company_name
    """
    context.log.info("Fetching SEC company tickers from company_tickers.json...")

    df = sec_edgar.fetch_company_tickers()

    context.add_output_metadata({
        "num_companies": len(df),
        "num_tickers": df["ticker"].nunique(),
    })

    context.log.info(f"Fetched {len(df)} companies from SEC registry")
    return df


# =============================================================================
# SILVER LAYER - Filtered Registries
# =============================================================================


@dg.asset(
    key_prefix=["silver", "sec"],
    name="company_registry",
    group_name=ASSET_GROUP,
    ins={
        "filer_registry": dg.AssetIn(key=["bronze", "sec", "sec_filer_registry"]),
    },
    metadata={
        "layer": "silver",
        "data_quality": "validated",
        "visibility": "internal",
    },
)
def company_registry(
    context: dg.AssetExecutionContext,
    filer_registry: pd.DataFrame,
) -> pd.DataFrame:
    """Filter SEC registry to config-enabled tickers.

    Filters the complete SEC registry to only include companies
    that are enabled in the config.
    """
    context.log.info("Filtering SEC registry to config-enabled companies...")

    # Get enabled tickers from config
    enabled_companies = get_sec_enabled_companies()
    enabled_tickers = {c["ticker"] for c in enabled_companies}  # noqa: F841

    # Filter registry
    df = filer_registry.query("ticker in @enabled_tickers")

    context.add_output_metadata({
        "num_companies": len(df),
        "enabled_tickers": sorted(df["ticker"].tolist()),
    })

    context.log.info(f"Filtered to {len(df)} enabled companies")
    return df


@dg.asset(
    key_prefix=["silver", "sec"],
    name="institution_registry",
    group_name=ASSET_GROUP,
    ins={
        "filer_registry": dg.AssetIn(key=["bronze", "sec", "sec_filer_registry"]),
    },
    metadata={
        "layer": "silver",
        "data_quality": "validated",
        "visibility": "internal",
    },
)
def institution_registry(
    context: dg.AssetExecutionContext,
    filer_registry: pd.DataFrame,
) -> pd.DataFrame:
    """Filter SEC registry to config-enabled institutions.

    Filters the complete SEC registry to only include institutions
    that are enabled in the config (for 13-F filings).
    """
    context.log.info("Filtering SEC registry to config-enabled institutions...")

    # Get enabled institutions from config
    enabled_institutions = get_sec_enabled_institutions()
    enabled_ciks = {i["cik"] for i in enabled_institutions}  # noqa: F841

    # Filter registry
    df = filer_registry.query("cik in @enabled_ciks")

    context.add_output_metadata({
        "num_institutions": len(df),
        "enabled_ciks": sorted(df["cik"].tolist()),
    })

    context.log.info(f"Filtered to {len(df)} enabled institutions")
    return df


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    "sec_filer_registry",
    "company_registry",
    "institution_registry",
]
