"""Agriculture indicators - gold layer with agricultural location partitions.

This module creates gold layer agricultural weather indicators that route to NASA POWER
bronze data using the location registry.

Architecture:
- Semantic partitions: Agricultural location names (brazil_minas_gerais, colombia_huila, etc.)
- Bronze partitions: Same agricultural locations (coordinate-based at bronze layer)
- Mapping: Via silver/reference/nasa_power_location_registry asset
- Single comprehensive weather asset with all variables as columns

Implementation:
- Uses direct Dagster dependencies (function parameters) for provenance tracking
- Same partition definition flows through bronze → gold
- Transforms NASA parameter codes to semantic column names with units
"""

import dagster as dg
import pandas as pd

from pipelines.partitions import agricultural_locations
from pipelines.utils.metadata import get_date_range_metadata

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def transform_to_semantic_columns(df: pd.DataFrame, location: str) -> pd.DataFrame:
    """Transform NASA POWER parameter codes to semantic column names.

    Args:
        df: DataFrame with NASA POWER raw data (NASA parameter codes)
        location: Agricultural location ID

    Returns:
        DataFrame with semantic column names and units
    """
    return df.rename(
        columns={
            "location_id": "location",
            "T2M": "temperature_avg_c",
            "T2M_MAX": "temperature_max_c",
            "T2M_MIN": "temperature_min_c",
            "PRECTOTCORR": "precipitation_mm",
            "RH2M": "humidity_pct",
            "TS": "soil_temperature_c",
            "ALLSKY_SFC_SW_DWN": "solar_radiation_mj_m2",
        }
    )[
        [
            "date",
            "location",
            "latitude",
            "longitude",
            "temperature_avg_c",
            "temperature_max_c",
            "temperature_min_c",
            "precipitation_mm",
            "humidity_pct",
            "soil_temperature_c",
            "solar_radiation_mj_m2",
        ]
    ]


def add_agriculture_metadata(
    context: dg.AssetExecutionContext,
    df: pd.DataFrame,
    location: str,
) -> None:
    """Add standardized output metadata for agricultural weather assets."""
    context.add_output_metadata({
        "location": location,
        "num_records": len(df),
        **get_date_range_metadata(df),
        "latitude": (
            float(df["latitude"].iloc[0])
            if "latitude" in df.columns and len(df) > 0
            else None
        ),
        "longitude": (
            float(df["longitude"].iloc[0])
            if "longitude" in df.columns and len(df) > 0
            else None
        ),
    })


# =============================================================================
# GOLD LAYER ASSETS - LLM-ACCESSIBLE AGRICULTURAL WEATHER
# =============================================================================


@dg.asset(
    name="daily",
    key_prefix=["gold", "agriculture", "weather"],
    partitions_def=agricultural_locations,
    code_version="2",
    ins={
        "nasa_power_daily": dg.AssetIn(
            key=dg.AssetKey(["bronze", "nasa_power", "daily"]),
        ),
    },
    metadata={
        "layer": "gold",
        "visibility": "llm_accessible",
        "description": "Daily agricultural weather conditions for coffee-growing regions",
        "domain": "agriculture",
        "questions_answered": [
            "What is the weather in {region}?",
            "What is the temperature and rainfall in Brazil coffee regions?",
            "Show me soil temperature for Ethiopia Sidamo",
            "What are the weather conditions in Colombian coffee regions?",
        ],
    },
    group_name="agriculture_indicators",
)
def agriculture_weather_daily(
    context: dg.AssetExecutionContext,
    nasa_power_daily: pd.DataFrame,
) -> pd.DataFrame:
    """Daily agricultural weather conditions with semantic column names.

    Returns DataFrame with all weather variables as columns:
        - date: Date of observation
        - location: Agricultural location ID
        - latitude, longitude: Coordinates
        - temperature_avg_c: Average temperature (Celsius)
        - temperature_max_c: Maximum temperature (Celsius)
        - temperature_min_c: Minimum temperature (Celsius)
        - precipitation_mm: Precipitation (millimeters)
        - humidity_pct: Relative humidity (percent)
        - soil_temperature_c: Soil temperature (Celsius)
        - solar_radiation_mj_m2: Solar radiation (MJ/m² per day)
    """
    location = context.partition_key
    context.log.info(f"Creating daily agricultural weather for {location}...")

    if nasa_power_daily is None or nasa_power_daily.empty:
        raise ValueError(
            f"No daily weather data available for {location}. "
            f"Verify that upstream NASA POWER bronze assets are materialized."
        )

    df = transform_to_semantic_columns(nasa_power_daily, location)

    add_agriculture_metadata(context, df, location)
    context.log.info(
        f"Daily agricultural weather created for {location}: {len(df)} records"
    )

    return df


@dg.asset(
    name="monthly",
    key_prefix=["gold", "agriculture", "weather"],
    partitions_def=agricultural_locations,
    code_version="2",
    ins={
        "nasa_power_monthly": dg.AssetIn(
            key=dg.AssetKey(["bronze", "nasa_power", "monthly"]),
        ),
    },
    metadata={
        "layer": "gold",
        "visibility": "llm_accessible",
        "description": "Monthly agricultural weather aggregates for coffee-growing regions",
        "domain": "agriculture",
        "questions_answered": [
            "What is the monthly weather trend in {region}?",
            "Show monthly rainfall totals for Brazil coffee regions",
            "What are the monthly temperature patterns in Ethiopia?",
        ],
    },
    group_name="agriculture_indicators",
)
def agriculture_weather_monthly(
    context: dg.AssetExecutionContext,
    nasa_power_monthly: pd.DataFrame,
) -> pd.DataFrame:
    """Monthly agricultural weather aggregates with semantic column names.

    Returns DataFrame with all weather variables as columns:
        - date: First day of month
        - location: Agricultural location ID
        - latitude, longitude: Coordinates
        - temperature_avg_c: Average temperature (Celsius)
        - temperature_max_c: Maximum temperature (Celsius)
        - temperature_min_c: Minimum temperature (Celsius)
        - precipitation_mm: Total precipitation (millimeters)
        - humidity_pct: Average relative humidity (percent)
        - soil_temperature_c: Average soil temperature (Celsius)
        - solar_radiation_mj_m2: Average solar radiation (MJ/m² per day)
    """
    location = context.partition_key
    context.log.info(f"Creating monthly agricultural weather for {location}...")

    if nasa_power_monthly is None or nasa_power_monthly.empty:
        raise ValueError(
            f"No monthly weather data available for {location}. "
            f"Verify that upstream NASA POWER bronze assets are materialized."
        )

    df = transform_to_semantic_columns(nasa_power_monthly, location)

    add_agriculture_metadata(context, df, location)
    context.log.info(
        f"Monthly agricultural weather created for {location}: {len(df)} records"
    )

    return df


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    "agriculture_weather_daily",
    "agriculture_weather_monthly",
]
