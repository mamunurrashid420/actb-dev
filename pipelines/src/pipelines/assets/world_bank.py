"""World Bank API assets - Multi-country economic indicators.

Architecture:
- Bronze layer: Single-dimension country partitions (3-letter ISO codes)
- Each partition contains ALL indicators for that country
- Semantic layer: Gold assets filter by indicator at runtime (in economic.py)

The World Bank API uses:
- 3-letter ISO country codes (USA, CHN, JPN, etc.)
- Indicator codes (NY.GDP.MKTP.CD, SL.UEM.TOTL.ZS, etc.)

Configuration driven by config/world_bank_indicators.yaml.
"""

import dagster as dg
import pandas as pd
import requests

from pipelines.partitions import (
    worldbank_country_partitions,
)
from pipelines.resources import WorldBankApiResource

# =============================================================================
# CONSTANTS
# =============================================================================

# Metadata for World Bank indicators
INDICATOR_INFO = {
    "NY.GDP.MKTP.CD": {
        "name": "GDP Current USD",
        "description": "Gross Domestic Product in current US dollars",
    },
    "NY.GDP.PCAP.CD": {
        "name": "GDP Per Capita",
        "description": "GDP per capita in current US dollars",
    },
    "GC.DOD.TOTL.GD.ZS": {
        "name": "Government Debt",
        "description": "Central government debt, total (% of GDP)",
    },
    "SL.UEM.TOTL.ZS": {
        "name": "Unemployment Rate",
        "description": "Unemployment, total (% of total labor force)",
    },
    "FP.CPI.TOTL.ZG": {
        "name": "Inflation CPI",
        "description": "Inflation, consumer prices (annual %)",
    },
    "EN.ATM.CO2E.PC": {
        "name": "CO2 Per Capita",
        "description": "CO2 emissions (metric tons per capita)",
    },
    "BN.CAB.XOKA.GD.ZS": {
        "name": "Current Account Balance",
        "description": "Current account balance (% of GDP)",
    },
    "FR.INR.RINR": {
        "name": "Real Interest Rate",
        "description": "Real interest rate (%)",
    },
}


# =============================================================================
# BRONZE ASSETS - Fetch data from World Bank API
# =============================================================================


@dg.asset(
    name="timeseries",
    key_prefix=["bronze", "world_bank"],
    partitions_def=worldbank_country_partitions,
    code_version="2",
    group_name="world_bank",
    pool="world_bank_api",
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "world_bank",
        "description": "World Bank timeseries data partitioned by country (all indicators)",
    },
    retry_policy=dg.RetryPolicy(max_retries=3, delay=60),
)
def worldbank_timeseries(
    context: dg.AssetExecutionContext,
    world_bank_api: WorldBankApiResource,
) -> pd.DataFrame:
    """Fetch all World Bank indicators for a single country.

    This asset is partitioned by country (3-letter ISO code).
    Each partition contains the full timeseries for ALL indicators for that country.

    Returns:
        DataFrame with columns: country_code, country_name, date, value, indicator_code
    """
    country_code = context.partition_key  # Simple string: 'USA', 'CHN', etc.

    context.log.info(f"Fetching all World Bank indicators for {country_code}...")

    all_data = []
    indicators_fetched = []
    indicators_failed = []

    for indicator_code in INDICATOR_INFO:
        indicator_info = INDICATOR_INFO.get(indicator_code, {})
        indicator_name = indicator_info.get("name", indicator_code)

        context.log.info(f"  Fetching {indicator_code} ({indicator_name})...")

        try:
            df = world_bank_api.get_indicator(indicator_code, [country_code])

            if len(df) == 0:
                context.log.warning(
                    f"  No data returned for {indicator_code} ({indicator_name})"
                )
                indicators_failed.append(indicator_code)
                continue

            if "country_code" not in df.columns:
                context.log.warning(
                    f"  Missing country_code column for {indicator_code}"
                )
                indicators_failed.append(indicator_code)
                continue

            df = (
                df[df["country_code"] == country_code]
                .assign(
                    date=lambda x: pd.to_datetime(x["date"], format="%Y"),
                    indicator_code=indicator_code,
                )
                .sort_values("date")
                .reset_index(drop=True)
            )

            all_data.append(df)
            indicators_fetched.append(indicator_code)

        except (requests.exceptions.RequestException, ValueError, KeyError) as e:
            context.log.warning(f"  Failed to fetch {indicator_code}: {e}")
            indicators_failed.append(indicator_code)

    if not all_data:
        raise ValueError(
            f"World Bank API returned no data for any indicator for {country_code}. "
            f"Verify country code is valid and data is available."
        )

    result = pd.concat(all_data, ignore_index=True)

    context.add_output_metadata({
        "country": country_code,
        "num_records": len(result),
        "indicators_fetched": len(indicators_fetched),
        "indicators_failed": len(indicators_failed),
        "indicators_list": ", ".join(indicators_fetched),
        "date_range_start": str(result["date"].min()) if len(result) > 0 else None,
        "date_range_end": str(result["date"].max()) if len(result) > 0 else None,
    })

    context.log.info(
        f"World Bank fetch complete for {country_code}: "
        f"{len(indicators_fetched)} indicators, {len(result)} records"
    )
    return result


# NOTE: Published assets moved to economic.py
# This consolidates all published economic indicators in one module


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # Constants (module-specific)
    "INDICATOR_INFO",
    # Assets
    "worldbank_timeseries",  # Function name (asset key: bronze/world_bank/timeseries)
]
