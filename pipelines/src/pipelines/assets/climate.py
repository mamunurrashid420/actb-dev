"""Climate indicators - gold layer with city-level partitions.

This module creates gold layer climate indicators that route to NOAA bronze data
using the silver layer location crosswalk.

Architecture:
- Gold partitions: City names (New_York, London, Tokyo)
- Bronze partitions: NOAA station IDs (USW00094728, etc.)
- Mapping: Via silver/reference/noaa_locations asset

Implementation:
- Uses context.load_asset_value() to fetch from upstream partitions
- Requires upstream NOAA bronze assets to be materialized first
- Routes to appropriate station based on city via location crosswalk
"""

import dagster as dg
import pandas as pd

from pipelines.partitions import climate_cities
from pipelines.utils.metadata import get_date_range_metadata

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def load_noaa_daily_for_city(
    context: dg.AssetExecutionContext,
    location_crosswalk: pd.DataFrame,
    city: str,
) -> tuple[pd.DataFrame | None, str | None]:
    """Load NOAA daily data for a given city from bronze layer.

    Args:
        context: Dagster execution context
        location_crosswalk: Location crosswalk DataFrame
        city: City name (e.g., 'New_York', 'London')

    Returns:
        Tuple of (DataFrame with weather data, station_id used)
        Returns (None, None) if data unavailable
    """
    # Find primary station for this city
    city_stations = location_crosswalk[
        location_crosswalk["city"] == city.replace("_", " ")
    ]

    if city_stations.empty:
        context.log.warning(f"No station mapping found for city: {city}")
        return None, None

    station_id = city_stations.iloc[0]["primary_station_id"]
    context.log.info(f"Loading NOAA daily data for {city} from station {station_id}")

    try:
        df = context.load_asset_value(
            asset_key=dg.AssetKey(["bronze", "noaa", "daily"]),
            partition_key=station_id,
        )
        return df, station_id
    except Exception as e:
        context.log.warning(f"Failed to load NOAA data for {city}: {e}")
        return None, None


def add_climate_metadata(
    context: dg.AssetExecutionContext,
    df: pd.DataFrame,
    city: str,
    station_id: str | None,
) -> None:
    """Add standardized output metadata for climate assets."""
    context.add_output_metadata({
        "city": city,
        "station_id": station_id or "none",
        "num_records": len(df),
        **get_date_range_metadata(df),
    })


# =============================================================================
# GOLD LAYER ASSETS - LLM-ACCESSIBLE CLIMATE INDICATORS
# =============================================================================


@dg.asset(
    name="average",
    key_prefix=["gold", "climate", "temperature"],
    partitions_def=climate_cities,
    code_version="1",
    ins={
        "location_crosswalk": dg.AssetIn(
            key=dg.AssetKey(["silver", "reference", "noaa_locations"]),
            partition_mapping=dg.AllPartitionMapping(),
        ),
    },
    deps=[
        dg.AssetDep(
            dg.AssetKey(["bronze", "noaa", "daily"]),
            partition_mapping=dg.AllPartitionMapping(),
        ),
    ],
    metadata={
        "layer": "gold",
        "visibility": "llm_accessible",
        "description": "Average temperature from NOAA daily weather data",
        "questions_answered": [
            "What is the temperature in {city}?",
            "What is the average temperature in {city}?",
            "How hot is it in {city}?",
        ],
    },
)
def temperature_average(
    context: dg.AssetExecutionContext,
    location_crosswalk: pd.DataFrame,
) -> pd.DataFrame:
    """Average temperature - gold layer indicator routing to NOAA bronze data via city."""
    city = context.partition_key
    context.log.info(f"Creating temperature indicator for {city}...")

    df, station_id = load_noaa_daily_for_city(context, location_crosswalk, city)

    if df is None or df.empty:
        raise ValueError(
            f"No temperature data available for {city}. "
            f"Verify that upstream NOAA bronze assets are materialized and location crosswalk contains this city."
        )

    # Calculate average temperature from TMAX and TMIN
    if "TMAX" in df.columns and "TMIN" in df.columns:
        df = df.assign(
            avg_temperature=lambda x: (x["TMAX"] + x["TMIN"]) / 2,
            city=city,
        )[["city", "date", "avg_temperature", "TMAX", "TMIN", "station_id"]]
    else:
        raise ValueError(
            f"NOAA data missing required TMAX/TMIN columns for {city}. "
            f"This indicates a data quality issue with the upstream NOAA asset."
        )

    add_climate_metadata(context, df, city, station_id)
    context.log.info(
        f"Temperature indicator created for {city}: {len(df)} records from {station_id}"
    )
    return df


@dg.asset(
    name="total",
    key_prefix=["gold", "climate", "precipitation"],
    partitions_def=climate_cities,
    code_version="1",
    ins={
        "location_crosswalk": dg.AssetIn(
            key=dg.AssetKey(["silver", "reference", "noaa_locations"]),
            partition_mapping=dg.AllPartitionMapping(),
        ),
    },
    deps=[
        dg.AssetDep(
            dg.AssetKey(["bronze", "noaa", "daily"]),
            partition_mapping=dg.AllPartitionMapping(),
        ),
    ],
    metadata={
        "layer": "gold",
        "visibility": "llm_accessible",
        "description": "Precipitation totals from NOAA daily weather data",
        "questions_answered": [
            "How much rain fell in {city}?",
            "What is the precipitation in {city}?",
            "Is it raining in {city}?",
        ],
    },
)
def precipitation_total(
    context: dg.AssetExecutionContext,
    location_crosswalk: pd.DataFrame,
) -> pd.DataFrame:
    """Precipitation total - gold layer indicator routing to NOAA bronze data via city."""
    city = context.partition_key
    context.log.info(f"Creating precipitation indicator for {city}...")

    df, station_id = load_noaa_daily_for_city(context, location_crosswalk, city)

    if df is None or df.empty:
        raise ValueError(
            f"No precipitation data available for {city}. "
            f"Verify that upstream NOAA bronze assets are materialized and location crosswalk contains this city."
        )

    # Extract precipitation data
    if "PRCP" in df.columns:
        df = df.rename(columns={"PRCP": "precipitation"}).assign(city=city)[
            ["city", "date", "precipitation", "station_id"]
        ]
    else:
        raise ValueError(
            f"NOAA data missing required PRCP column for {city}. "
            f"This indicates a data quality issue with the upstream NOAA asset."
        )

    add_climate_metadata(context, df, city, station_id)
    context.log.info(
        f"Precipitation indicator created for {city}: {len(df)} records from {station_id}"
    )
    return df


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    "temperature_average",
    "precipitation_total",
]
