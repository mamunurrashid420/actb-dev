import os

import dagster as dg
from dagster_duckdb import DuckDBResource
from upath import UPath

from pipelines import checks  # Asset checks for data quality validation

# Import asset modules for auto-discovery
from pipelines.assets import (
    agriculture,  # Gold layer agricultural indicators
    bea,  # BEA NIPA economic data (GDP, PCE, income)
    bls,  # BLS timeseries partitioned by series ID
    climate,  # Gold layer climate indicators with city partitioning
    ecb,  # ECB exchange rate data
    economic,  # Gold layer economic indicators with partition mapping
    fred,  # FRED timeseries partitioned by series ID
    nasa_power,  # NASA POWER agricultural weather data
    noaa,  # NOAA climate data partitioned by station ID
    patents,  # PatentsView USPTO patent data
    reference,  # ID crosswalk and registry assets
    sec,  # SEC assets (new modular structure + registry)
    usda,  # USDA FAS PSD agricultural commodity data
    world_bank,  # World Bank timeseries partitioned by [country, indicator]
)
from pipelines.io_managers import FileSystemIOManager
from pipelines.jobs import ALL_JOBS
from pipelines.resources import (
    BeaApiResource,
    BlsApiResource,
    BlsBulkResource,
    EcbDataResource,
    FredApiResource,
    NasaPowerApiResource,
    NoaaApiResource,
    PatentsViewResource,
    SecEdgarResource,
    UsdaFasResource,
    WorldBankApiResource,
)
from pipelines.schedules import ALL_SCHEDULES
from pipelines.sensors import ALL_SENSORS
from shared.data.assets import get_environment

# Load all assets
all_assets = [
    # Reference assets (ID mappings)
    *dg.load_assets_from_modules([reference], group_name="reference"),
    # Raw economic data sources (source-native partitions)
    *dg.load_assets_from_modules([fred], group_name="fred"),
    *dg.load_assets_from_modules([world_bank], group_name="world_bank"),
    *dg.load_assets_from_modules([bls], group_name="bls"),
    # BEA NIPA economic data (GDP, PCE, income)
    *dg.load_assets_from_modules([bea], group_name="bea"),
    # Raw climate data sources (station-partitioned)
    *dg.load_assets_from_modules([noaa], group_name="noaa"),
    # Raw agricultural weather data (location-partitioned)
    *dg.load_assets_from_modules([nasa_power], group_name="nasa_power"),
    # Gold layer economic indicators (friendly partitions with mapping)
    # Most indicators are country_indicators, government_debt is fiscal_indicators
    *dg.load_assets_from_modules([economic]),
    # Gold layer climate indicators (city-level partitions)
    *dg.load_assets_from_modules([climate], group_name="climate_indicators"),
    # Gold layer agricultural indicators (agricultural location partitions)
    *dg.load_assets_from_modules([agriculture], group_name="agriculture_indicators"),
    # SEC registry assets (new modular structure)
    *dg.load_assets_from_modules([sec], group_name="sec_filings"),
    # ECB exchange rate data
    *dg.load_assets_from_modules([ecb], group_name="ecb"),
    # USDA FAS PSD agricultural commodity data
    *dg.load_assets_from_modules([usda], group_name="usda"),
    # PatentsView USPTO patent data (bulk downloads)
    *dg.load_assets_from_modules([patents], group_name="patents"),
]

# Load all asset checks for data quality validation
all_checks = dg.load_asset_checks_from_modules([checks])


def _create_io_manager() -> FileSystemIOManager:
    """Create IO manager based on STORAGE_ENV."""
    storage_env = os.getenv("STORAGE_ENV", "local")
    config = get_environment(storage_env)

    if config.s3_config:
        # Bind credentials at use time
        access_key = os.getenv("SUPABASE_S3_ACCESS_KEY")
        secret_key = os.getenv("SUPABASE_S3_SECRET_KEY")

        if not access_key or not secret_key:
            raise ValueError(
                "Missing Supabase S3 credentials. Set SUPABASE_S3_ACCESS_KEY and "
                "SUPABASE_S3_SECRET_KEY environment variables, or use STORAGE_ENV=local."
            )

        base_path = UPath(
            config.base_path,
            endpoint_url=config.s3_config.endpoint_url,
            key=access_key,
            secret=secret_key,
        )
    else:
        base_path = config.base_path

    return FileSystemIOManager(base_path=base_path)


# Define the Dagster definitions
defs = dg.Definitions(
    assets=all_assets,
    asset_checks=all_checks,
    schedules=ALL_SCHEDULES,
    sensors=ALL_SENSORS,
    jobs=ALL_JOBS,
    resources={
        "io_manager": _create_io_manager(),
        "duckdb": DuckDBResource(database="_data/analytics.duckdb"),
        "fred_api": FredApiResource(api_key=dg.EnvVar("FRED_API_KEY")),
        "world_bank_api": WorldBankApiResource(),
        "bls_api": BlsApiResource(api_key=dg.EnvVar("BLS_API_KEY")),
        "bls_bulk": BlsBulkResource(user_agent=dg.EnvVar("BLS_USER_AGENT")),
        "bea_api": BeaApiResource(api_key=dg.EnvVar("BEA_API_KEY")),
        "noaa_api": NoaaApiResource(api_token=dg.EnvVar("NOAA_API_TOKEN")),
        "nasa_power_api": NasaPowerApiResource(),  # No authentication required
        "sec_edgar": SecEdgarResource(identity=dg.EnvVar("SEC_IDENTITY")),
        "ecb_data": EcbDataResource(),  # No authentication required
        "usda_fas": UsdaFasResource(api_key=dg.EnvVar("USDA_FAS_API_KEY")),
        "patentsview": PatentsViewResource(),  # No authentication required
    },
)
