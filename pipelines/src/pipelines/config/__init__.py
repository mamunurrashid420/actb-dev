"""Configuration loader for World Bank indicators."""

from pathlib import Path
from typing import Any, TypedDict

import yaml


class CountryConfig(TypedDict, total=False):
    """Type definition for country configuration.

    Attributes:
        code: ISO country code (required)
        name: Country name (required)
        region: Geographic region (required)
        enabled: Whether to generate assets (required)
        date_range_start: Override global date_range_start (optional)
        date_range_end: Override global date_range_end (optional)
        api_timeout_seconds: Override global API timeout (optional)
    """

    code: str
    name: str
    region: str
    enabled: bool
    date_range_start: int
    date_range_end: int
    api_timeout_seconds: int


class IndicatorConfig(TypedDict, total=False):
    """Type definition for indicator configuration.

    Attributes:
        code: World Bank indicator code (required)
        name: Short name for asset naming (required)
        display_name: Human-readable name (required)
        description: Full description (required)
        unit: Unit of measurement (required)
        enabled: Whether to generate assets (required)
        date_range_start: Override global date_range_start (optional)
        date_range_end: Override global date_range_end (optional)
        allow_negative_values: Whether negative values are valid (optional)
    """

    code: str
    name: str
    display_name: str
    description: str
    unit: str
    enabled: bool
    date_range_start: int
    date_range_end: int
    allow_negative_values: bool


class SettingsConfig(TypedDict):
    """Type definition for global settings.

    Attributes:
        date_range_start: Default start year for data fetching
        date_range_end: Default end year for data fetching
        api_timeout_seconds: Default API timeout
        retry_max_attempts: Maximum retry attempts
        retry_delay_seconds: Delay between retries
        allow_negative_values: Default allow negative values
    """

    date_range_start: int
    date_range_end: int
    api_timeout_seconds: int
    retry_max_attempts: int
    retry_delay_seconds: int
    allow_negative_values: bool


class WorldBankConfig(TypedDict):
    """Type definition for complete World Bank configuration.

    Attributes:
        countries: List of country configurations
        indicators: Dict of indicator lists by category
        settings: Global settings
    """

    countries: list[CountryConfig]
    indicators: dict[str, list[IndicatorConfig]]
    settings: SettingsConfig


def load_world_bank_config() -> WorldBankConfig:
    """Load World Bank indicator configuration from YAML file.

    Returns:
        WorldBankConfig dictionary with countries, indicators, and settings

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    config_path = Path(__file__).parent / "world_bank_indicators.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"World Bank config file not found: {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    if not config:
        raise ValueError("World Bank config file is empty")

    # Validate required top-level keys
    required_keys = {"countries", "indicators", "settings"}
    missing_keys = required_keys - set(config.keys())
    if missing_keys:
        raise ValueError(f"World Bank config missing required keys: {missing_keys}")

    return config


def get_enabled_countries() -> list[tuple[str, str]]:
    """Get list of enabled countries as (code, name) tuples.

    Returns:
        List of (country_code, country_name) tuples for enabled countries
    """
    config = load_world_bank_config()
    return [
        (country["code"], country["name"])
        for country in config["countries"]
        if country.get("enabled", False)
    ]


def get_enabled_indicators() -> dict[str, str]:
    """Get dictionary of enabled indicators.

    Returns:
        Dictionary mapping indicator_name -> indicator_code
    """
    config = load_world_bank_config()
    result = {}

    for _category, indicators in config["indicators"].items():
        for indicator in indicators:
            if indicator.get("enabled", False):
                result[indicator["name"]] = indicator["code"]

    return result


def get_indicator_config(indicator_name: str) -> IndicatorConfig | None:
    """Get full configuration for a specific indicator.

    Args:
        indicator_name: Short name of the indicator (e.g., 'gdp')

    Returns:
        IndicatorConfig dict if found, None otherwise
    """
    config = load_world_bank_config()

    # Build indicator map from all categories
    indicator_map = {
        ind["name"]: ind
        for indicators in config["indicators"].values()
        for ind in indicators
    }

    return indicator_map.get(indicator_name)


def get_country_config(country_code: str) -> CountryConfig | None:
    """Get full configuration for a specific country.

    Args:
        country_code: ISO country code (e.g., 'US')

    Returns:
        CountryConfig dict if found, None otherwise
    """
    config = load_world_bank_config()

    country_map = {country["code"]: country for country in config["countries"]}
    return country_map.get(country_code)


def get_setting(
    setting_name: str,
    country_config: CountryConfig | None = None,
    indicator_config: IndicatorConfig | None = None,
) -> Any:
    """Get setting value with cascading priority.

    Priority order (highest to lowest):
    1. Indicator-level override
    2. Country-level override
    3. Global default

    Args:
        setting_name: Name of the setting to retrieve
        country_config: Optional country config dict
        indicator_config: Optional indicator config dict

    Returns:
        Setting value from highest priority source
    """
    config = load_world_bank_config()
    global_settings = config["settings"]

    # Check indicator-level override first
    if indicator_config and setting_name in indicator_config:
        return indicator_config[setting_name]

    # Check country-level override
    if country_config and setting_name in country_config:
        return country_config[setting_name]

    # Fall back to global default
    return global_settings.get(setting_name)


# =============================================================================
# SEC EDGAR Configuration Helpers
# =============================================================================


class CompanyConfig(TypedDict, total=False):
    """Type definition for SEC company configuration.

    Attributes:
        cik: Central Index Key (source-native identifier, required)
        ticker: Stock ticker symbol (friendly identifier, required)
        name: Company name (required)
        forms: List of filing types to track (required)
    """

    cik: str
    ticker: str
    name: str
    forms: list[str]


class InstitutionConfig(TypedDict, total=False):
    """Type definition for institutional investor configuration.

    Attributes:
        cik: Central Index Key for the institution (source-native, required)
        name: Friendly identifier (lowercase_underscore format, required)
        display_name: Human-readable name (required)
    """

    cik: str
    name: str
    display_name: str


class SecSettingsConfig(TypedDict):
    """Type definition for SEC global settings.

    Attributes:
        identity: SEC identity string (required by SEC API)
        partition_start_date: Start date for partitions
        retry_max_attempts: Maximum retry attempts
        retry_delay_seconds: Delay between retries
    """

    identity: str
    partition_start_date: str
    retry_max_attempts: int
    retry_delay_seconds: int


class SecConfig(TypedDict):
    """Type definition for complete SEC configuration.

    Attributes:
        companies: List of company configurations
        institutions: List of institution configurations
        settings: Global settings
    """

    companies: list[CompanyConfig]
    institutions: list[InstitutionConfig]
    settings: SecSettingsConfig


def load_sec_config() -> SecConfig:
    """Load SEC filings configuration from YAML file.

    Returns:
        SecConfig dictionary with companies, institutions, and settings

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    config_path = Path(__file__).parent / "sec_filings.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"SEC config file not found: {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    if not config:
        raise ValueError("SEC config file is empty")

    # Validate required top-level keys
    required_keys = {"companies", "institutions", "settings"}
    missing_keys = required_keys - set(config.keys())
    if missing_keys:
        raise ValueError(f"SEC config missing required keys: {missing_keys}")

    return config


def get_sec_enabled_companies() -> list[CompanyConfig]:
    """Get list of all SEC companies (enabled and disabled).

    Returns:
        List of CompanyConfig dicts with cik, ticker, name, and forms
    """
    config = load_sec_config()
    return config["companies"]


def get_sec_enabled_institutions() -> list[InstitutionConfig]:
    """Get list of all institutional investors (enabled and disabled).

    Returns:
        List of InstitutionConfig dicts with cik, name, and display_name
    """
    config = load_sec_config()
    return config["institutions"]


def get_company_by_cik(cik: str) -> CompanyConfig | None:
    """Get company configuration by CIK.

    Args:
        cik: Central Index Key (e.g., '0000320193')

    Returns:
        CompanyConfig dict if found, None otherwise
    """
    companies = get_sec_enabled_companies()
    company_map = {company["cik"]: company for company in companies}
    return company_map.get(cik)


def get_company_by_ticker(ticker: str) -> CompanyConfig | None:
    """Get company configuration by ticker symbol.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')

    Returns:
        CompanyConfig dict if found, None otherwise
    """
    companies = get_sec_enabled_companies()
    company_map = {company["ticker"]: company for company in companies}
    return company_map.get(ticker)


def get_cik_by_ticker(ticker: str) -> str | None:
    """Map ticker symbol to CIK.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')

    Returns:
        CIK string if found, None otherwise
    """
    company = get_company_by_ticker(ticker)
    return company["cik"] if company else None


def get_ticker_by_cik(cik: str) -> str | None:
    """Map CIK to ticker symbol.

    Args:
        cik: Central Index Key (e.g., '0000320193')

    Returns:
        Ticker string if found, None otherwise
    """
    company = get_company_by_cik(cik)
    return company["ticker"] if company else None


def get_sec_identity() -> str:
    """Get SEC identity string from config.

    Returns:
        Identity string in format "Name email@domain.com"
    """
    config = load_sec_config()
    return config["settings"]["identity"]


def get_sec_partition_start() -> str:
    """Get partition start date for SEC assets.

    Returns:
        ISO date string (YYYY-MM-DD)
    """
    config = load_sec_config()
    return config["settings"]["partition_start_date"]
