"""NASA POWER agricultural weather data assets.

Architecture:
- Bronze layer: Partitioned by agricultural location (semantic location IDs)
- Location-based partitioning: Semantic location names → lat/lon coordinates
- Silver layer: Location registry and variable crosswalks (reference data)

Data available:
- Daily: Agriculture-optimized weather variables (since 1981)
- Monthly: Monthly aggregated weather data
- Variables: Temperature, precipitation, humidity, soil temperature, solar radiation
"""

import dagster as dg
import pandas as pd

from pipelines.partitions import agricultural_locations
from pipelines.resources import NasaPowerApiResource

# =============================================================================
# CONSTANTS
# =============================================================================

# Location registry - Maps semantic location IDs to coordinates
LOCATION_REGISTRY = [
    {
        "location_id": "brazil_minas_gerais",
        "name": "Minas Gerais Coffee Region",
        "country": "BR",
        "latitude": -18.9433,
        "longitude": -46.9978,
        "region_type": "coffee_growing",
    },
    {
        "location_id": "brazil_sao_paulo",
        "name": "São Paulo Coffee Region",
        "country": "BR",
        "latitude": -23.5505,
        "longitude": -46.6333,
        "region_type": "coffee_growing",
    },
    {
        "location_id": "colombia_huila",
        "name": "Huila Department",
        "country": "CO",
        "latitude": 2.5350,
        "longitude": -75.5273,
        "region_type": "coffee_growing",
    },
    {
        "location_id": "colombia_antioquia",
        "name": "Antioquia Department",
        "country": "CO",
        "latitude": 6.2442,
        "longitude": -75.5812,
        "region_type": "coffee_growing",
    },
    {
        "location_id": "ethiopia_sidamo",
        "name": "Sidamo Region",
        "country": "ET",
        "latitude": 6.2000,
        "longitude": 38.5000,
        "region_type": "coffee_growing",
    },
    {
        "location_id": "ethiopia_yirgacheffe",
        "name": "Yirgacheffe",
        "country": "ET",
        "latitude": 6.1594,
        "longitude": 38.1986,
        "region_type": "coffee_growing",
    },
    {
        "location_id": "vietnam_dak_lak",
        "name": "Đắk Lắk Province",
        "country": "VN",
        "latitude": 12.7100,
        "longitude": 108.2378,
        "region_type": "coffee_growing",
    },
    {
        "location_id": "indonesia_sumatra",
        "name": "Sumatra Gayo Region",
        "country": "ID",
        "latitude": 4.6000,
        "longitude": 96.8000,
        "region_type": "coffee_growing",
    },
]

# Dictionary lookup for O(1) location access
LOCATIONS_BY_ID = {loc["location_id"]: loc for loc in LOCATION_REGISTRY}


def get_location_coordinates(location_id: str) -> tuple[float, float]:
    """Get latitude and longitude for a location ID.

    Args:
        location_id: Semantic location identifier

    Returns:
        Tuple of (latitude, longitude)

    Raises:
        ValueError: If location_id is not found in registry
    """
    try:
        location_info = LOCATIONS_BY_ID[location_id]
    except KeyError:
        raise ValueError(
            f"No location registry entry found for: {location_id}. "
            f"Valid location IDs are defined in LOCATION_REGISTRY."
        ) from None
    return location_info["latitude"], location_info["longitude"]


# Variable crosswalk - Maps NASA POWER parameter codes to semantic names
VARIABLE_CROSSWALK = [
    {
        "semantic_name": "temperature_avg_c",
        "nasa_code": "T2M",
        "description": "Temperature at 2 meters (average)",
        "units": "celsius",
    },
    {
        "semantic_name": "temperature_max_c",
        "nasa_code": "T2M_MAX",
        "description": "Temperature at 2 meters (maximum)",
        "units": "celsius",
    },
    {
        "semantic_name": "temperature_min_c",
        "nasa_code": "T2M_MIN",
        "description": "Temperature at 2 meters (minimum)",
        "units": "celsius",
    },
    {
        "semantic_name": "precipitation_mm",
        "nasa_code": "PRECTOTCORR",
        "description": "Precipitation (corrected)",
        "units": "millimeters",
    },
    {
        "semantic_name": "humidity_pct",
        "nasa_code": "RH2M",
        "description": "Relative humidity at 2 meters",
        "units": "percent",
    },
    {
        "semantic_name": "soil_temperature_c",
        "nasa_code": "TS",
        "description": "Earth skin temperature",
        "units": "celsius",
    },
    {
        "semantic_name": "solar_radiation_mj_m2",
        "nasa_code": "ALLSKY_SFC_SW_DWN",
        "description": "All sky surface shortwave downward irradiance",
        "units": "mj_per_square_meter_per_day",
    },
]


# =============================================================================
# BRONZE ASSETS - NASA POWER data ingestion
# =============================================================================


@dg.asset(
    name="daily",
    key_prefix=["bronze", "nasa_power"],
    partitions_def=agricultural_locations,
    code_version="1",
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "nasa_power",
        "temporal_resolution": "daily",
        "spatial_resolution": "50km",
        "description": "Daily agricultural weather from NASA POWER API",
    },
    retry_policy=dg.RetryPolicy(max_retries=3, delay=60),
)
def nasa_power_daily(
    context: dg.AssetExecutionContext,
    nasa_power_api: NasaPowerApiResource,
) -> pd.DataFrame:
    """Fetch daily agricultural weather data from NASA POWER (bronze layer).

    This asset is partitioned by agricultural location (semantic identifier).
    Contains daily weather observations optimized for agriculture.

    Returns:
        DataFrame with columns: date, location_id, latitude, longitude,
        T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, RH2M, TS, ALLSKY_SFC_SW_DWN
    """
    location_id = context.partition_key
    latitude, longitude = get_location_coordinates(location_id)

    context.log.info(
        f"Fetching daily agricultural weather for {location_id} ({latitude}, {longitude})..."
    )
    df = nasa_power_api.get_daily_data(latitude, longitude)

    if df.empty:
        raise ValueError(
            f"NASA POWER API returned no daily data for {location_id} ({latitude}, {longitude}). "
            f"Verify coordinates are valid and data is available."
        )

    df = df.assign(location_id=location_id)

    context.add_output_metadata({
        "location_id": location_id,
        "latitude": latitude,
        "longitude": longitude,
        "num_records": len(df),
        "date_range_start": str(df["date"].min()) if "date" in df.columns else None,
        "date_range_end": str(df["date"].max()) if "date" in df.columns else None,
        "variables": ", ".join([
            col
            for col in df.columns
            if col not in ["date", "location_id", "latitude", "longitude"]
        ]),
    })
    context.log.info(f"Daily data fetch complete for {location_id}")

    return df


@dg.asset(
    name="monthly",
    key_prefix=["bronze", "nasa_power"],
    partitions_def=agricultural_locations,
    code_version="1",
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "nasa_power",
        "temporal_resolution": "monthly",
        "spatial_resolution": "50km",
        "description": "Monthly agricultural weather from NASA POWER API",
    },
    retry_policy=dg.RetryPolicy(max_retries=3, delay=60),
)
def nasa_power_monthly(
    context: dg.AssetExecutionContext,
    nasa_power_api: NasaPowerApiResource,
) -> pd.DataFrame:
    """Fetch monthly agricultural weather data from NASA POWER (bronze layer).

    This asset is partitioned by agricultural location (semantic identifier).
    Contains monthly aggregated weather data optimized for agriculture.

    Returns:
        DataFrame with columns: date, location_id, latitude, longitude,
        T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, RH2M, TS, ALLSKY_SFC_SW_DWN
    """
    location_id = context.partition_key
    latitude, longitude = get_location_coordinates(location_id)

    context.log.info(
        f"Fetching monthly agricultural weather for {location_id} ({latitude}, {longitude})..."
    )
    df = nasa_power_api.get_monthly_data(latitude, longitude)

    if df.empty:
        raise ValueError(
            f"NASA POWER API returned no monthly data for {location_id} ({latitude}, {longitude}). "
            f"Verify coordinates are valid and data is available."
        )

    df = df.assign(location_id=location_id)

    context.add_output_metadata({
        "location_id": location_id,
        "latitude": latitude,
        "longitude": longitude,
        "num_records": len(df),
        "date_range_start": str(df["date"].min()) if "date" in df.columns else None,
        "date_range_end": str(df["date"].max()) if "date" in df.columns else None,
        "variables": ", ".join([
            col
            for col in df.columns
            if col not in ["date", "location_id", "latitude", "longitude"]
        ]),
    })
    context.log.info(f"Monthly data fetch complete for {location_id}")

    return df


# =============================================================================
# SILVER ASSETS - Reference data (crosswalks and metadata)
# =============================================================================


@dg.asset(
    key_prefix=["silver", "reference"],
    name="nasa_power_location_registry",
    code_version="1",
    metadata={
        "layer": "silver",
        "description": "Mapping of agricultural location IDs to coordinates and metadata",
        "visibility": "internal",
    },
)
def nasa_power_location_registry() -> pd.DataFrame:
    """Location registry mapping semantic location IDs to coordinates (silver layer).

    Returns:
        DataFrame with columns: location_id, name, country, latitude, longitude, region_type
    """
    return pd.DataFrame(LOCATION_REGISTRY)


@dg.asset(
    key_prefix=["silver", "reference"],
    name="nasa_power_variable_crosswalk",
    code_version="1",
    metadata={
        "layer": "silver",
        "description": "Mapping of semantic variable names to NASA POWER parameter codes",
        "visibility": "internal",
    },
)
def nasa_power_variable_crosswalk() -> pd.DataFrame:
    """Variable crosswalk mapping semantic names to NASA POWER codes (silver layer).

    Returns:
        DataFrame with columns: semantic_name, nasa_code, description, units
    """
    return pd.DataFrame(VARIABLE_CROSSWALK)


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # Bronze assets (raw ingestion layer)
    "nasa_power_daily",
    "nasa_power_monthly",
    # Silver assets (reference data)
    "nasa_power_location_registry",
    "nasa_power_variable_crosswalk",
]
