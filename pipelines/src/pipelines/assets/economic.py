"""Economic indicators - gold layer with direct dependencies.

This module creates gold layer economic indicators that directly depend on
bronze layer data sources. Gold assets use the same 3-letter country partitions
as the World Bank bronze layer, filtering by indicator at runtime.

Architecture:
- Gold partitions: 3-letter country codes (USA, CHN, JPN) - same as World Bank bronze
- Bronze partitions: Single-dimension country partitions (World Bank), series IDs (FRED, BLS)
- Routing: FRED for US, World Bank for all countries

Implementation:
- Direct dependency on bronze/world_bank/timeseries (same partition definition)
- Filter by indicator_code column at runtime
- FRED assets still use AllPartitionMapping for US-specific data
"""

import dagster as dg
import pandas as pd

from pipelines.partitions import (
    COUNTRY_CODE_MAP,
    government_debt_partitions,
    interest_rate_partitions,
    worldbank_country_partitions,
)
from pipelines.utils.metadata import get_date_range_metadata

# DEPRECATED: semantic_countries (2-letter codes) no longer used
# Gold assets now use worldbank_country_partitions (3-letter codes)

# Reverse mapping: 3-letter → 2-letter for compatibility with existing code
COUNTRY_CODE_MAP_3_TO_2 = {v: k for k, v in COUNTRY_CODE_MAP.items()}

# =============================================================================
# INDICATOR CODE MAPPING
# =============================================================================

# Maps canonical indicator slugs to World Bank indicator codes
INDICATOR_CODE_MAP = {
    "unemployment": "SL.UEM.TOTL.ZS",
    "gdp": "NY.GDP.MKTP.CD",
    "inflation": "FP.CPI.TOTL.ZG",
    "interest_rate": "FR.INR.RINR",
    "trade_balance": "BN.CAB.XOKA.GD.ZS",
    "government_debt": "GC.DOD.TOTL.GD.ZS",
}

# Maps canonical indicator slugs to FRED series IDs (US-only, higher quality)
FRED_SERIES_MAP = {
    "unemployment": "UNRATE",
    "gdp": "GDP",
    "inflation": "CPIAUCSL",
    "interest_rate": "FEDFUNDS",
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def filter_crosswalk_by_slug(
    crosswalk: pd.DataFrame, canonical_slug: str
) -> pd.DataFrame:
    """Filter indicator crosswalk by canonical slug.

    DEPRECATED: This function is maintained for backward compatibility with
    assets that still use the crosswalk. New assets should use direct filtering.
    """
    return crosswalk[crosswalk["canonical_slug"] == canonical_slug]


def filter_worldbank_by_indicator(
    df: pd.DataFrame,
    indicator_code: str,
    metric_name: str,
) -> pd.DataFrame:
    """Filter World Bank data by indicator code and rename value column.

    Args:
        df: World Bank DataFrame with indicator_code column
        indicator_code: World Bank indicator code (e.g., 'SL.UEM.TOTL.ZS')
        metric_name: Name for the value column in output DataFrame

    Returns:
        Filtered DataFrame with renamed value column
    """
    return (
        df[df["indicator_code"] == indicator_code]
        .rename(columns={"value": metric_name})
        .drop(columns=["indicator_code"])
    )


def load_fred_indicator(
    context: dg.AssetExecutionContext,
    bronze_fred_series: pd.DataFrame,
    sources: pd.DataFrame,
    country_code: str,
    metric_name: str,
) -> tuple[pd.DataFrame | None, str | None]:
    """Load FRED timeseries indicator (US only).

    Args:
        context: Dagster execution context
        bronze_fred_series: Unpartitioned FRED DataFrame with all series
        sources: Filtered indicator sources DataFrame
        country_code: 2-letter country code (must be 'US')
        metric_name: Name for the value column in output DataFrame

    Returns:
        Tuple of (DataFrame with renamed columns, source identifier string)
        Returns (None, None) if data unavailable or country is not US
    """
    if country_code != "US":
        return None, None

    fred_series = sources[sources["source"] == "fred"]
    if fred_series.empty:
        return None, None

    series_id = fred_series.iloc[0]["source_series_id"]
    context.log.info(f"Loading from FRED series: {series_id}")

    # Filter the unpartitioned DataFrame by series_id
    df = bronze_fred_series[bronze_fred_series["series_id"] == series_id]
    if df.empty:
        context.log.warning(f"No data found for FRED series {series_id}")
        return None, None

    source_used = f"fred:{series_id}"
    df = df.rename(columns={"value": metric_name}).assign(
        country_code=country_code, source=source_used
    )
    return df, source_used


def load_bls_indicator(
    context: dg.AssetExecutionContext,
    bronze_bls_all_series: pd.DataFrame,
    sources: pd.DataFrame,
    country_code: str,
    metric_name: str,
) -> tuple[pd.DataFrame | None, str | None]:
    """Load BLS timeseries indicator (US only).

    Args:
        context: Dagster execution context
        bronze_bls_all_series: Unpartitioned BLS DataFrame with all series
        sources: Filtered indicator sources DataFrame
        country_code: 2-letter country code (must be 'US')
        metric_name: Name for the value column in output DataFrame

    Returns:
        Tuple of (DataFrame with renamed columns, source identifier string)
        Returns (None, None) if data unavailable or country is not US
    """
    if country_code != "US":
        return None, None

    bls_series = sources[sources["source"] == "bls"]
    if bls_series.empty:
        return None, None

    series_id = bls_series.iloc[0]["source_series_id"]
    context.log.info(f"Loading from BLS series: {series_id}")

    # Filter the unpartitioned DataFrame by series_id
    df = bronze_bls_all_series[bronze_bls_all_series["series_id"] == series_id]
    if df.empty:
        context.log.warning(f"No data found for BLS series {series_id}")
        return None, None

    source_used = f"bls:{series_id}"
    df = df.rename(columns={"value": metric_name}).assign(
        country_code=country_code, source=source_used
    )
    return df, source_used


def add_indicator_metadata(
    context: dg.AssetExecutionContext,
    df: pd.DataFrame,
    country_code: str,
    source_used: str | None,
) -> None:
    """Add standardized output metadata for indicator assets."""
    context.add_output_metadata({
        "country": country_code,
        "source": source_used or "none",
        "num_records": len(df),
        **get_date_range_metadata(df),
    })


# =============================================================================
# GOLD LAYER ASSETS - LLM-ACCESSIBLE
# =============================================================================


@dg.asset(
    name="unemployment",
    key_prefix=["gold", "economic", "labor_market"],
    partitions_def=worldbank_country_partitions,
    code_version="3",
    group_name="country_indicators",
    ins={
        "world_bank_data": dg.AssetIn(
            key=dg.AssetKey(["bronze", "world_bank", "timeseries"]),
        ),
        "fred_data": dg.AssetIn(
            key=dg.AssetKey(["bronze", "fred", "series"]),
            partition_mapping=dg.AllPartitionMapping(),
        ),
    },
    metadata={
        "layer": "gold",
        "visibility": "llm_accessible",
        "description": "Unemployment rate from FRED (USA) or World Bank (other countries)",
        "questions_answered": [
            "What is the unemployment rate in {country}?",
            "Is unemployment increasing or decreasing in {country}?",
            "How is the {country} job market?",
        ],
    },
)
def unemployment(
    context: dg.AssetExecutionContext,
    world_bank_data: pd.DataFrame,
    fred_data: pd.DataFrame,
) -> pd.DataFrame:
    """Unemployment rate from FRED (USA) or World Bank (other countries)."""
    country_code = context.partition_key  # 3-letter: 'USA', 'CHN', etc.
    context.log.info(f"Creating unemployment indicator for {country_code}...")

    if country_code == "USA":
        # Use FRED for US (higher quality, more frequent updates)
        series_id = FRED_SERIES_MAP["unemployment"]
        source_used = f"fred:{series_id}"
        df = (
            fred_data[fred_data["series_id"] == series_id]
            .rename(columns={"value": "unemployment_rate"})
            .drop(columns=["series_id"])
        )
    else:
        # Use World Bank for other countries
        indicator_code = INDICATOR_CODE_MAP["unemployment"]
        source_used = f"worldbank:{country_code}/{indicator_code}"
        df = filter_worldbank_by_indicator(
            world_bank_data, indicator_code, "unemployment_rate"
        )

    if df is None or df.empty:
        raise ValueError(
            f"No unemployment data available for {country_code}. "
            f"Verify that upstream assets are materialized."
        )

    df = df.assign(country_code=country_code, source=source_used)

    add_indicator_metadata(context, df, country_code, source_used)
    context.log.info(
        f"Unemployment indicator created for {country_code}: {len(df)} records from {source_used}"
    )
    return df


@dg.asset(
    name="gdp",
    key_prefix=["gold", "economic", "growth"],
    partitions_def=worldbank_country_partitions,
    code_version="3",
    group_name="country_indicators",
    ins={
        "world_bank_data": dg.AssetIn(
            key=dg.AssetKey(["bronze", "world_bank", "timeseries"]),
        ),
        "fred_data": dg.AssetIn(
            key=dg.AssetKey(["bronze", "fred", "series"]),
            partition_mapping=dg.AllPartitionMapping(),
        ),
    },
    metadata={
        "layer": "gold",
        "visibility": "llm_accessible",
        "description": "GDP from FRED (USA) or World Bank (other countries)",
        "questions_answered": [
            "What is the GDP of {country}?",
            "How large is the {country} economy?",
        ],
    },
)
def gdp(
    context: dg.AssetExecutionContext,
    world_bank_data: pd.DataFrame,
    fred_data: pd.DataFrame,
) -> pd.DataFrame:
    """GDP from FRED (USA) or World Bank (other countries)."""
    country_code = context.partition_key  # 3-letter: 'USA', 'CHN', etc.
    context.log.info(f"Creating GDP indicator for {country_code}...")

    if country_code == "USA":
        # Use FRED for US (higher quality, more frequent updates)
        series_id = FRED_SERIES_MAP["gdp"]
        source_used = f"fred:{series_id}"
        df = (
            fred_data[fred_data["series_id"] == series_id]
            .rename(columns={"value": "gdp"})
            .drop(columns=["series_id"])
        )
    else:
        # Use World Bank for other countries
        indicator_code = INDICATOR_CODE_MAP["gdp"]
        source_used = f"worldbank:{country_code}/{indicator_code}"
        df = filter_worldbank_by_indicator(world_bank_data, indicator_code, "gdp")

    if df is None or df.empty:
        raise ValueError(
            f"No GDP data available for {country_code}. "
            f"Verify that upstream assets are materialized."
        )

    df = df.assign(country_code=country_code, source=source_used)

    add_indicator_metadata(context, df, country_code, source_used)
    context.log.info(
        f"GDP indicator created for {country_code}: {len(df)} records from {source_used}"
    )
    return df


# =============================================================================
# US-ONLY BLS INDICATORS (require direct partition mapping to BLS series)
# =============================================================================


@dg.asset(
    name="job_openings",
    key_prefix=["gold", "economic", "labor_market"],
    partitions_def=worldbank_country_partitions,
    code_version="3",
    group_name="country_indicators",
    ins={
        "indicator_id_crosswalk": dg.AssetIn(
            key=dg.AssetKey(["silver", "reference", "indicator_id_crosswalk"]),
            partition_mapping=dg.AllPartitionMapping(),
        ),
        "bronze_bls_all_series": dg.AssetIn(
            key=dg.AssetKey(["bronze", "bls", "all_series"]),
            partition_mapping=dg.AllPartitionMapping(),
        ),
    },
    metadata={
        "layer": "gold",
        "visibility": "llm_accessible",
        "description": "JOLTS job openings (US only)",
        "questions_answered": [
            "How many job openings are there in {country}?",
            "What is the JOLTS job openings data for {country}?",
        ],
    },
)
def job_openings(
    context: dg.AssetExecutionContext,
    indicator_id_crosswalk: pd.DataFrame,
    bronze_bls_all_series: pd.DataFrame,
) -> pd.DataFrame:
    """Job openings from BLS JOLTS (US only)."""
    country_code = context.partition_key  # 3-letter: 'USA'

    if country_code != "USA":
        raise ValueError(
            f"Job openings data only available for USA, not {country_code}. "
            f"This indicator is sourced from BLS JOLTS which only covers the United States."
        )

    # Convert to 2-letter for crosswalk lookup
    country_code_2 = COUNTRY_CODE_MAP_3_TO_2.get(country_code, country_code)
    context.log.info(f"Creating job openings indicator for {country_code}...")

    sources = filter_crosswalk_by_slug(indicator_id_crosswalk, "job_openings")

    df, source_used = load_bls_indicator(
        context, bronze_bls_all_series, sources, country_code_2, "job_openings"
    )

    if df is None or df.empty:
        raise ValueError(
            f"No job openings data available for {country_code}. "
            f"Verify that upstream BLS raw assets are materialized."
        )

    df = df.assign(country_code=country_code)

    add_indicator_metadata(context, df, country_code, source_used)
    context.log.info(
        f"Job openings indicator created for {country_code}: {len(df)} records from {source_used}"
    )
    return df


# =============================================================================
# NEW COUNTRY INDICATOR ASSETS
# =============================================================================


@dg.asset(
    name="inflation",
    key_prefix=["gold", "economic", "prices"],
    partitions_def=worldbank_country_partitions,
    code_version="3",
    group_name="country_indicators",
    ins={
        "world_bank_data": dg.AssetIn(
            key=dg.AssetKey(["bronze", "world_bank", "timeseries"]),
        ),
        "fred_data": dg.AssetIn(
            key=dg.AssetKey(["bronze", "fred", "series"]),
            partition_mapping=dg.AllPartitionMapping(),
        ),
    },
    metadata={
        "layer": "gold",
        "visibility": "llm_accessible",
        "description": "Inflation rate (CPI) from FRED (USA) or World Bank (other countries)",
        "questions_answered": [
            "What is the inflation rate in {country}?",
            "How much have prices increased in {country}?",
            "What is the CPI in {country}?",
        ],
    },
)
def inflation(
    context: dg.AssetExecutionContext,
    world_bank_data: pd.DataFrame,
    fred_data: pd.DataFrame,
) -> pd.DataFrame:
    """Inflation rate from FRED (USA) or World Bank (other countries)."""
    country_code = context.partition_key  # 3-letter: 'USA', 'CHN', etc.
    context.log.info(f"Creating inflation indicator for {country_code}...")

    if country_code == "USA":
        # Use FRED for US (higher quality, more frequent updates)
        series_id = FRED_SERIES_MAP["inflation"]
        source_used = f"fred:{series_id}"
        df = (
            fred_data[fred_data["series_id"] == series_id]
            .rename(columns={"value": "inflation_rate"})
            .drop(columns=["series_id"])
        )
    else:
        # Use World Bank for other countries
        indicator_code = INDICATOR_CODE_MAP["inflation"]
        source_used = f"worldbank:{country_code}/{indicator_code}"
        df = filter_worldbank_by_indicator(
            world_bank_data, indicator_code, "inflation_rate"
        )

    if df is None or df.empty:
        raise ValueError(
            f"No inflation data available for {country_code}. "
            f"Verify that upstream assets are materialized."
        )

    df = df.assign(country_code=country_code, source=source_used)

    add_indicator_metadata(context, df, country_code, source_used)
    context.log.info(
        f"Inflation indicator created for {country_code}: {len(df)} records from {source_used}"
    )
    return df


@dg.asset(
    name="interest_rate",
    key_prefix=["gold", "economic", "monetary"],
    partitions_def=interest_rate_partitions,
    code_version="4",
    group_name="monetary_indicators",
    ins={
        "world_bank_data": dg.AssetIn(
            key=dg.AssetKey(["bronze", "world_bank", "timeseries"]),
        ),
        "fred_data": dg.AssetIn(
            key=dg.AssetKey(["bronze", "fred", "series"]),
            partition_mapping=dg.AllPartitionMapping(),
        ),
    },
    metadata={
        "layer": "gold",
        "visibility": "llm_accessible",
        "description": "Interest rate from FRED (USA) or World Bank (other countries)",
        "questions_answered": [
            "What is the interest rate in {country}?",
            "What is the Federal Funds rate?",
            "What are borrowing costs in {country}?",
        ],
    },
)
def interest_rate(
    context: dg.AssetExecutionContext,
    world_bank_data: pd.DataFrame,
    fred_data: pd.DataFrame,
) -> pd.DataFrame:
    """Interest rate from FRED (USA) or World Bank (other countries)."""
    country_code = context.partition_key  # 3-letter: 'USA', 'CHN', etc.
    context.log.info(f"Creating interest rate indicator for {country_code}...")

    if country_code == "USA":
        # Use FRED for US (higher quality, more frequent updates)
        series_id = FRED_SERIES_MAP["interest_rate"]
        source_used = f"fred:{series_id}"
        df = (
            fred_data[fred_data["series_id"] == series_id]
            .rename(columns={"value": "interest_rate"})
            .drop(columns=["series_id"])
        )
    else:
        # Use World Bank for other countries
        indicator_code = INDICATOR_CODE_MAP["interest_rate"]
        source_used = f"worldbank:{country_code}/{indicator_code}"
        df = filter_worldbank_by_indicator(
            world_bank_data, indicator_code, "interest_rate"
        )

    if df is None or df.empty:
        raise ValueError(
            f"No interest rate data available for {country_code}. "
            f"Verify that upstream assets are materialized."
        )

    df = df.assign(country_code=country_code, source=source_used)

    add_indicator_metadata(context, df, country_code, source_used)
    context.log.info(
        f"Interest rate indicator created for {country_code}: {len(df)} records from {source_used}"
    )
    return df


@dg.asset(
    name="balance",
    key_prefix=["gold", "economic", "trade"],
    partitions_def=worldbank_country_partitions,
    code_version="2",
    group_name="country_indicators",
    ins={
        "world_bank_data": dg.AssetIn(
            key=dg.AssetKey(["bronze", "world_bank", "timeseries"]),
        ),
    },
    metadata={
        "layer": "gold",
        "visibility": "llm_accessible",
        "description": "Trade balance (current account balance as % of GDP)",
        "questions_answered": [
            "What is the trade balance of {country}?",
            "Does {country} have a trade surplus or deficit?",
            "What is the current account balance for {country}?",
        ],
    },
)
def trade_balance(
    context: dg.AssetExecutionContext,
    world_bank_data: pd.DataFrame,
) -> pd.DataFrame:
    """Trade balance (current account) from World Bank data."""
    country_code = context.partition_key  # 3-letter: 'USA', 'CHN', etc.
    context.log.info(f"Creating trade balance indicator for {country_code}...")

    indicator_code = INDICATOR_CODE_MAP["trade_balance"]
    source_used = f"worldbank:{country_code}/{indicator_code}"

    df = filter_worldbank_by_indicator(
        world_bank_data, indicator_code, "trade_balance_pct_gdp"
    )

    if df is None or df.empty:
        raise ValueError(
            f"No trade balance data available for {country_code}. "
            f"Verify that upstream World Bank assets are materialized."
        )

    df = df.assign(country_code=country_code, source=source_used)

    add_indicator_metadata(context, df, country_code, source_used)
    context.log.info(
        f"Trade balance indicator created for {country_code}: {len(df)} records from {source_used}"
    )
    return df


@dg.asset(
    name="government_debt",
    key_prefix=["gold", "economic", "fiscal"],
    partitions_def=government_debt_partitions,
    code_version="3",
    group_name="fiscal_indicators",
    ins={
        "world_bank_data": dg.AssetIn(
            key=dg.AssetKey(["bronze", "world_bank", "timeseries"]),
        ),
    },
    metadata={
        "layer": "gold",
        "visibility": "llm_accessible",
        "description": "Government debt as % of GDP",
        "questions_answered": [
            "What is the government debt of {country}?",
            "How much debt does {country} have?",
            "What is the debt-to-GDP ratio for {country}?",
        ],
    },
)
def government_debt(
    context: dg.AssetExecutionContext,
    world_bank_data: pd.DataFrame,
) -> pd.DataFrame:
    """Government debt from World Bank data."""
    country_code = context.partition_key  # 3-letter: 'USA', 'CHN', etc.
    context.log.info(f"Creating government debt indicator for {country_code}...")

    indicator_code = INDICATOR_CODE_MAP["government_debt"]
    source_used = f"worldbank:{country_code}/{indicator_code}"

    df = filter_worldbank_by_indicator(world_bank_data, indicator_code, "debt_pct_gdp")

    if df is None or df.empty:
        raise ValueError(
            f"No government debt data available for {country_code}. "
            f"Verify that upstream World Bank assets are materialized."
        )

    df = df.assign(country_code=country_code, source=source_used)

    add_indicator_metadata(context, df, country_code, source_used)
    context.log.info(
        f"Government debt indicator created for {country_code}: {len(df)} records from {source_used}"
    )
    return df


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # Gold layer assets (LLM-accessible)
    "unemployment",
    "gdp",
    "job_openings",
    "inflation",
    "interest_rate",
    "trade_balance",
    "government_debt",
]
