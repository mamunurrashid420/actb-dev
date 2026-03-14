"""NOAA Climate Data Online (CDO) assets - weather and climate data.

Architecture:
- Bronze layer: Partitioned by NOAA station ID (source-native)
- Three datasets: Daily, Monthly, Annual weather summaries
- Silver layer: Station metadata and crosswalks for semantic routing

Data available:
- Daily: GHCN-Daily dataset (temperature, precipitation, snow, wind)
- Monthly: GSOM dataset (monthly aggregates)
- Annual: GSOY dataset (annual aggregates)
"""

import dagster as dg
import pandas as pd

from pipelines.partitions import noaa_stations
from pipelines.resources import NoaaApiResource
from pipelines.utils.metadata import get_date_range_metadata

# =============================================================================
# BRONZE ASSETS - NOAA CDO data ingestion
# =============================================================================


@dg.asset(
    name="daily",
    key_prefix=["bronze", "noaa"],
    partitions_def=noaa_stations,
    code_version="1",
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "noaa",
        "dataset": "ghcn_daily",
        "description": "Daily weather observations from NOAA GHCN-Daily dataset",
    },
    retry_policy=dg.RetryPolicy(max_retries=3, delay=60),
)
def noaa_daily(
    context: dg.AssetExecutionContext,
    noaa_api: NoaaApiResource,
) -> pd.DataFrame:
    """Fetch daily weather data from NOAA GHCN-Daily dataset.

    This asset is partitioned by NOAA station ID (source-native identifier).
    Contains daily observations including temperature, precipitation, and snow.

    Returns:
        DataFrame with columns: date, TMAX, TMIN, PRCP, SNOW, SNWD, etc.
    """
    station_id = context.partition_key

    context.log.info(f"Fetching daily weather data for station {station_id}...")
    df = noaa_api.get_daily_data(station_id)

    if df.empty:
        raise ValueError(
            f"NOAA API returned no daily data for station {station_id}. "
            f"Verify station ID is valid and data is available."
        )

    df = df.assign(station_id=station_id)

    context.add_output_metadata({
        "station_id": station_id,
        "num_records": len(df),
        **get_date_range_metadata(df),
        "variables": ", ".join([
            col for col in df.columns if col not in ["date", "station_id"]
        ]),
    })
    context.log.info(f"Daily data fetch complete for {station_id}")

    return df


@dg.asset(
    name="monthly",
    key_prefix=["bronze", "noaa"],
    partitions_def=noaa_stations,
    code_version="1",
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "noaa",
        "dataset": "gsom",
        "description": "Monthly weather summaries from NOAA GSOM dataset",
    },
    retry_policy=dg.RetryPolicy(max_retries=3, delay=60),
)
def noaa_monthly(
    context: dg.AssetExecutionContext,
    noaa_api: NoaaApiResource,
) -> pd.DataFrame:
    """Fetch monthly weather summaries from NOAA GSOM dataset.

    This asset is partitioned by NOAA station ID (source-native identifier).
    Contains monthly aggregated temperature, precipitation, and snow data.

    Returns:
        DataFrame with columns: date, TAVG, TMAX, TMIN, PRCP, etc.
    """
    station_id = context.partition_key

    context.log.info(f"Fetching monthly summary data for station {station_id}...")
    df = noaa_api.get_monthly_data(station_id)

    if df.empty:
        raise ValueError(
            f"NOAA API returned no monthly data for station {station_id}. "
            f"Verify station ID is valid and data is available."
        )

    df = df.assign(station_id=station_id)

    context.add_output_metadata({
        "station_id": station_id,
        "num_records": len(df),
        **get_date_range_metadata(df),
        "variables": ", ".join([
            col for col in df.columns if col not in ["date", "station_id"]
        ]),
    })
    context.log.info(f"Monthly summary fetch complete for {station_id}")

    return df


@dg.asset(
    name="annual",
    key_prefix=["bronze", "noaa"],
    partitions_def=noaa_stations,
    code_version="1",
    metadata={
        "layer": "bronze",
        "visibility": "internal",
        "source": "noaa",
        "dataset": "gsoy",
        "description": "Annual weather summaries from NOAA GSOY dataset",
    },
    retry_policy=dg.RetryPolicy(max_retries=3, delay=60),
)
def noaa_annual(
    context: dg.AssetExecutionContext,
    noaa_api: NoaaApiResource,
) -> pd.DataFrame:
    """Fetch annual weather summaries from NOAA GSOY dataset.

    This asset is partitioned by NOAA station ID (source-native identifier).
    Contains annual aggregated temperature and precipitation data.

    Returns:
        DataFrame with columns: date, TAVG, TMAX, TMIN, PRCP
    """
    station_id = context.partition_key

    context.log.info(f"Fetching annual summary data for station {station_id}...")
    df = noaa_api.get_annual_data(station_id)

    if df.empty:
        raise ValueError(
            f"NOAA API returned no annual data for station {station_id}. "
            f"Verify station ID is valid and data is available."
        )

    df = df.assign(station_id=station_id)

    context.add_output_metadata({
        "station_id": station_id,
        "num_records": len(df),
        **get_date_range_metadata(df),
        "variables": ", ".join([
            col for col in df.columns if col not in ["date", "station_id"]
        ]),
    })
    context.log.info(f"Annual summary fetch complete for {station_id}")

    return df


# =============================================================================
# SILVER ASSETS - Crosswalks and metadata
# =============================================================================


@dg.asset(
    key_prefix=["silver", "reference"],
    name="noaa_stations",
    code_version="1",
    metadata={
        "layer": "silver",
        "description": "Mapping of NOAA station IDs to locations and metadata",
        "visibility": "internal",
    },
)
def noaa_station_registry() -> pd.DataFrame:
    """Silver layer station registry mapping station IDs to geographic locations.

    Returns:
        DataFrame with columns: station_id, name, country, latitude, longitude, elevation
    """
    # Initial curated list with metadata
    # In production, this would query NOAA stations API
    stations = [
        {
            "station_id": "USW00094728",
            "name": "New York Central Park",
            "country": "US",
            "city": "New York",
            "latitude": 40.7789,
            "longitude": -73.9692,
            "elevation": 42.7,
        },
        {
            "station_id": "USW00023174",
            "name": "Los Angeles Intl Airport",
            "country": "US",
            "city": "Los Angeles",
            "latitude": 33.9381,
            "longitude": -118.3889,
            "elevation": 30.5,
        },
        {
            "station_id": "USW00014819",
            "name": "Chicago O'Hare",
            "country": "US",
            "city": "Chicago",
            "latitude": 41.9950,
            "longitude": -87.9336,
            "elevation": 201.5,
        },
        {
            "station_id": "USW00012960",
            "name": "Houston Intercontinental",
            "country": "US",
            "city": "Houston",
            "latitude": 29.9669,
            "longitude": -95.3486,
            "elevation": 29.0,
        },
        {
            "station_id": "USW00023183",
            "name": "Phoenix Sky Harbor",
            "country": "US",
            "city": "Phoenix",
            "latitude": 33.4342,
            "longitude": -112.0089,
            "elevation": 337.4,
        },
        {
            "station_id": "UKW00035769",
            "name": "London Heathrow",
            "country": "GB",
            "city": "London",
            "latitude": 51.4775,
            "longitude": -0.4614,
            "elevation": 25.0,
        },
        {
            "station_id": "FRW00007149",
            "name": "Paris Orly",
            "country": "FR",
            "city": "Paris",
            "latitude": 48.7233,
            "longitude": 2.3794,
            "elevation": 89.0,
        },
        {
            "station_id": "JAW00047662",
            "name": "Tokyo",
            "country": "JP",
            "city": "Tokyo",
            "latitude": 35.6895,
            "longitude": 139.6917,
            "elevation": 36.0,
        },
        {
            "station_id": "CAW00071624",
            "name": "Toronto Pearson",
            "country": "CA",
            "city": "Toronto",
            "latitude": 43.6777,
            "longitude": -79.6248,
            "elevation": 173.4,
        },
        {
            "station_id": "ASW00094767",
            "name": "Sydney Observatory",
            "country": "AU",
            "city": "Sydney",
            "latitude": -33.8599,
            "longitude": 151.2055,
            "elevation": 39.0,
        },
    ]

    return pd.DataFrame(stations)


@dg.asset(
    key_prefix=["silver", "reference"],
    name="noaa_variables",
    code_version="1",
    metadata={
        "layer": "silver",
        "description": "Mapping of semantic variable names to NOAA data type codes",
        "visibility": "internal",
    },
)
def noaa_variable_crosswalk() -> pd.DataFrame:
    """Silver layer variable crosswalk mapping semantic names to NOAA codes.

    Returns:
        DataFrame with columns: semantic_name, noaa_code, description, units
    """
    variables = [
        {
            "semantic_name": "max_temperature",
            "noaa_code": "TMAX",
            "description": "Maximum temperature",
            "units": "degrees_celsius",
        },
        {
            "semantic_name": "min_temperature",
            "noaa_code": "TMIN",
            "description": "Minimum temperature",
            "units": "degrees_celsius",
        },
        {
            "semantic_name": "avg_temperature",
            "noaa_code": "TAVG",
            "description": "Average temperature",
            "units": "degrees_celsius",
        },
        {
            "semantic_name": "precipitation",
            "noaa_code": "PRCP",
            "description": "Precipitation",
            "units": "millimeters",
        },
        {
            "semantic_name": "snowfall",
            "noaa_code": "SNOW",
            "description": "Snowfall",
            "units": "millimeters",
        },
        {
            "semantic_name": "snow_depth",
            "noaa_code": "SNWD",
            "description": "Snow depth",
            "units": "millimeters",
        },
        {
            "semantic_name": "avg_wind_speed",
            "noaa_code": "AWND",
            "description": "Average wind speed",
            "units": "meters_per_second",
        },
    ]

    return pd.DataFrame(variables)


@dg.asset(
    key_prefix=["silver", "reference"],
    name="noaa_locations",
    code_version="1",
    metadata={
        "layer": "silver",
        "description": "Mapping of countries/cities to primary NOAA stations",
        "visibility": "internal",
    },
)
def noaa_location_crosswalk() -> pd.DataFrame:
    """Silver layer location crosswalk for routing semantic locations to stations.

    Maps 2-letter country codes and city names to primary weather stations
    for semantic layer routing.

    Returns:
        DataFrame with columns: country_code, city, primary_station_id
    """
    locations = [
        {"country_code": "US", "city": "New York", "primary_station_id": "USW00094728"},
        {
            "country_code": "US",
            "city": "Los Angeles",
            "primary_station_id": "USW00023174",
        },
        {"country_code": "US", "city": "Chicago", "primary_station_id": "USW00014819"},
        {"country_code": "US", "city": "Houston", "primary_station_id": "USW00012960"},
        {"country_code": "US", "city": "Phoenix", "primary_station_id": "USW00023183"},
        {"country_code": "GB", "city": "London", "primary_station_id": "UKW00035769"},
        {"country_code": "FR", "city": "Paris", "primary_station_id": "FRW00007149"},
        {"country_code": "JP", "city": "Tokyo", "primary_station_id": "JAW00047662"},
        {"country_code": "CA", "city": "Toronto", "primary_station_id": "CAW00071624"},
        {"country_code": "AU", "city": "Sydney", "primary_station_id": "ASW00094767"},
    ]

    return pd.DataFrame(locations)


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # Bronze assets (source layer)
    "noaa_daily",
    "noaa_monthly",
    "noaa_annual",
    # Silver assets (reference layer)
    "noaa_station_registry",
    "noaa_variable_crosswalk",
    "noaa_location_crosswalk",
]
