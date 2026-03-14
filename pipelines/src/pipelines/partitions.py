"""Shared partition definitions for all Dagster assets.

This module centralizes partition definitions to ensure consistency across
bronze, silver, and gold medallion architecture layers.

Architecture (Medallion Pattern - Simplified):
- Bronze layer: Unpartitioned bulk downloads (SEC submissions, company_facts)
- Silver layer: Cleaned/validated data, reference tables
- Gold layer: Unpartitioned aggregated data, filtered by registries

Partition Strategy:
- Unpartitioned: Small stable datasets (FRED ~5 series, BLS ~6 series)
- Unpartitioned: SEC bulk downloads (company_facts, submissions)
- Time partitions: SEC form text (yearly, quarterly, monthly)

Country codes use 3-letter ISO format (USA, CHN, JPN) throughout all layers
for consistency with World Bank API and simpler architecture.
"""

import dagster as dg

# =============================================================================
# BRONZE LAYER PARTITIONS (Source-Native IDs)
# =============================================================================

# NOAA - Use NOAA station IDs as source-native identifiers (dynamic partitions)
noaa_stations = dg.DynamicPartitionsDefinition(name="noaa_stations")


# =============================================================================
# GOLD LAYER PARTITIONS (Friendly/Semantic IDs)
# =============================================================================

# Cities - For climate data (more granular than country-level)
climate_cities = dg.StaticPartitionsDefinition([
    "New_York",
    "Los_Angeles",
    "Chicago",
    "Houston",
    "Phoenix",
    "London",
    "Paris",
    "Tokyo",
    "Toronto",
    "Sydney",
])

# Agricultural locations - For NASA POWER agricultural weather data
agricultural_locations = dg.StaticPartitionsDefinition([
    "brazil_minas_gerais",  # Minas Gerais coffee region
    "brazil_sao_paulo",  # São Paulo coffee region
    "colombia_huila",  # Huila Department (high-quality arabica)
    "colombia_antioquia",  # Antioquia Department (coffee)
    "ethiopia_sidamo",  # Sidamo region (coffee origin)
    "ethiopia_yirgacheffe",  # Yirgacheffe (specialty coffee)
    "vietnam_dak_lak",  # Đắk Lắk Province (Central Highlands)
    "indonesia_sumatra",  # Sumatra (Gayo coffee region)
])

# Country code mapping: 2-letter (semantic) → 3-letter (World Bank)
COUNTRY_CODE_MAP = {
    "US": "USA",
    "CN": "CHN",
    "JP": "JPN",
    "DE": "DEU",
    "GB": "GBR",
    "FR": "FRA",
    "KR": "KOR",
    "IT": "ITA",
    "GR": "GRC",
    "EU": "EUU",
    "CA": "CAN",
    "IN": "IND",
    "BR": "BRA",
    "AU": "AUS",
    "MX": "MEX",
    "ES": "ESP",
    "NL": "NLD",
    "RU": "RUS",
    "SA": "SAU",
    "TR": "TUR",
}

# =============================================================================
# COUNTRY PARTITIONS (shared by World Bank and Economic assets)
# =============================================================================

# 3-letter ISO country codes (source-native for World Bank API)
WORLD_BANK_COUNTRIES = [
    "USA",
    "CHN",
    "JPN",
    "DEU",
    "GBR",
    "FRA",
    "KOR",
    "ITA",
    "GRC",
    "EUU",
    "CAN",
    "IND",
    "BRA",
    "AUS",
    "MEX",
    "ESP",
    "NLD",
    "RUS",
    "SAU",
    "TUR",
]

# Single-dimension partition: one partition per country, contains all indicators
worldbank_country_partitions = dg.StaticPartitionsDefinition(WORLD_BANK_COUNTRIES)

# Countries with government debt data (GC.DOD.TOTL.GD.ZS)
# World Bank returns null for: CHN, JPN, FRA, GRC, EUU, SAU
GOVERNMENT_DEBT_COUNTRIES = [
    "USA",
    "DEU",
    "GBR",
    "KOR",
    "ITA",
    "CAN",
    "IND",
    "BRA",
    "AUS",
    "MEX",
    "ESP",
    "NLD",
    "RUS",
    "TUR",
]
government_debt_partitions = dg.StaticPartitionsDefinition(GOVERNMENT_DEBT_COUNTRIES)

# Countries with interest rate data (FR.INR.RINR)
# World Bank returns null for: DEU, FRA, GRC, EUU, ESP, SAU, TUR
INTEREST_RATE_COUNTRIES = [
    "USA",
    "CHN",
    "JPN",
    "GBR",
    "KOR",
    "ITA",
    "CAN",
    "IND",
    "BRA",
    "AUS",
    "MEX",
    "NLD",
    "RUS",
]
interest_rate_partitions = dg.StaticPartitionsDefinition(INTEREST_RATE_COUNTRIES)


# =============================================================================
# STATIC TIME PARTITIONS
# =============================================================================

# Fiscal years (for SEC Form 10-K annual reports)
fiscal_year_partitions = dg.StaticPartitionsDefinition([
    f"FY{year}" for year in range(2020, 2026)
])

# Quarters (for SEC Form 10-Q - Q1, Q2, Q3 only, Q4 covered by 10-K)
quarterly_partitions = dg.StaticPartitionsDefinition([
    f"{year}-Q{q}" for year in range(2020, 2026) for q in [1, 2, 3]
])

# All quarters including Q4 (for 13F which files all 4 quarters)
quarterly_all_partitions = dg.StaticPartitionsDefinition([
    f"{year}-Q{q}" for year in range(2020, 2026) for q in [1, 2, 3, 4]
])

# Months (for SEC Form 8-K and Form 4 filings)
monthly_partitions = dg.StaticPartitionsDefinition([
    f"{year}-{month:02d}" for year in range(2020, 2026) for month in range(1, 13)
])

# =============================================================================
# SEC TIME-BASED PARTITIONS (for narrative text and transactions)
# =============================================================================

# Yearly partitions for 10-K text (narrative content)
sec_yearly_partitions = dg.StaticPartitionsDefinition([
    str(year) for year in range(2020, 2026)
])

# =============================================================================
# USDA ESR MARKET YEAR PARTITIONS
# =============================================================================

# ESR market year partitions (1990-present)
# ESR data is organized by USDA market year (varies by commodity, typically Oct-Sep)
# Full historical coverage enables backfill and year-over-year analysis
esr_market_year_partitions = dg.StaticPartitionsDefinition(
    [str(year) for year in range(1990, 2026)]  # 36 years of history
)

# =============================================================================
# USDA GATS CENSUS MONTH PARTITIONS
# =============================================================================


def generate_census_months() -> list[str]:
    """Generate rolling 12-month partition keys for GATS Census data.

    Census data has a ~2 month release lag, so we start the window from
    2 months ago to avoid empty partitions. For example, in December 2025,
    the most recent available data is October 2025.

    Returns:
        List of month strings sorted ascending: ['2024-01', '2024-02', ...]
    """
    import datetime as dt
    from datetime import timedelta

    today = dt.datetime.now()
    # Start 2 months ago (Census data release lag)
    start_date = today.replace(day=1) - timedelta(days=60)
    months = []
    for i in range(12):
        date = start_date - timedelta(days=30 * i)
        months.append(f"{date.year}-{date.month:02d}")
    return sorted(months)


# GATS Census month partitions (rolling 12-month window)
# Evaluated at module load time - restarts pick up new months
gats_census_month_partitions = dg.StaticPartitionsDefinition(generate_census_months())

# Quarterly partitions for 10-Q text and 13-F
sec_quarterly_partitions = dg.StaticPartitionsDefinition([
    f"{year}-Q{q}" for year in range(2020, 2026) for q in [1, 2, 3, 4]
])

# Monthly partitions for Form 4 (high volume)
sec_monthly_partitions = dg.StaticPartitionsDefinition([
    f"{year}-{month:02d}" for year in range(2020, 2026) for month in range(1, 13)
])


# =============================================================================
# PARTITION KEY PARSERS
# =============================================================================


def parse_fiscal_year(key: str) -> int:
    """Parse fiscal year partition key.

    Example: "FY2023" -> 2023
    """
    return int(key[2:])


def parse_quarter(key: str) -> tuple[int, int]:
    """Parse quarter partition key.

    Example: "2024-Q2" -> (2024, 2)
    """
    year_str, quarter_str = key.split("-Q")
    return int(year_str), int(quarter_str)


def parse_month(key: str) -> tuple[int, int]:
    """Parse month partition key.

    Example: "2024-05" -> (2024, 5)
    """
    year_str, month_str = key.split("-")
    return int(year_str), int(month_str)


# =============================================================================
# PARTITION KEY GENERATORS (for SEC time-based partitions)
# =============================================================================


def generate_years(start_year: int = 2020, end_year: int | None = None) -> list[str]:
    """Generate yearly partition keys.

    Args:
        start_year: First year to include (default: 2020)
        end_year: Last year to include (default: current year)

    Returns:
        List of year strings: ['2020', '2021', '2022', ...]
    """
    import datetime as dt

    if end_year is None:
        end_year = dt.datetime.now().year
    return [str(year) for year in range(start_year, end_year + 1)]


def generate_quarters(start_year: int = 2020, end_year: int | None = None) -> list[str]:
    """Generate quarterly partition keys.

    Args:
        start_year: First year to include (default: 2020)
        end_year: Last year to include (default: current year)

    Returns:
        List of quarter strings: ['2020-Q1', '2020-Q2', ..., '2024-Q4']
    """
    import datetime as dt

    if end_year is None:
        end_year = dt.datetime.now().year
    return [
        f"{year}-Q{q}" for year in range(start_year, end_year + 1) for q in [1, 2, 3, 4]
    ]


def generate_months(start_year: int = 2020, end_year: int | None = None) -> list[str]:
    """Generate monthly partition keys.

    Args:
        start_year: First year to include (default: 2020)
        end_year: Last year to include (default: current year)

    Returns:
        List of month strings: ['2020-01', '2020-02', ..., '2024-12']
    """
    import datetime as dt

    if end_year is None:
        end_year = dt.datetime.now().year
    return [
        f"{year}-{month:02d}"
        for year in range(start_year, end_year + 1)
        for month in range(1, 13)
    ]


# =============================================================================
# SEC FINANCIAL STATEMENT DATA SETS (FSDS) PARTITIONS
# =============================================================================


def generate_fsds_quarters() -> list[str]:
    """Generate FSDS quarterly partition keys from 2009 to current completed quarter.

    FSDS data is available since Q1 2009. Only includes completed quarters
    (current quarter excluded since data won't be available yet).

    Returns:
        List of quarter strings: ['2009-Q1', '2009-Q2', ..., '2024-Q3']
    """
    import datetime as dt

    now = dt.datetime.now()
    current_quarter = (now.month - 1) // 3 + 1

    quarters = []
    for year in range(2009, now.year + 1):
        for q in [1, 2, 3, 4]:
            # Skip current and future quarters (data not yet available)
            if year == now.year and q >= current_quarter:
                break
            quarters.append(f"{year}-Q{q}")

    return quarters


# FSDS quarterly partitions - auto-extends to current completed quarter
# Evaluated at module load time, so restarts pick up new quarters
fsds_quarterly_partitions = dg.StaticPartitionsDefinition(generate_fsds_quarters())


def partition_key_to_fsds_filename(partition_key: str) -> str:
    """Convert partition key to SEC FSDS filename format.

    Example: '2024-Q3' -> '2024q3'
    """
    year, q = partition_key.split("-Q")
    return f"{year}q{q}"


def fsds_filename_to_partition_key(filename: str) -> str:
    """Convert SEC FSDS filename to partition key format.

    Example: '2024q3' or '2024q3.zip' -> '2024-Q3'
    """
    base = filename.replace(".zip", "")
    year = base[:4]
    quarter = base[5]
    return f"{year}-Q{quarter}"


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # Bronze layer partitions (source-native IDs)
    "noaa_stations",
    # Semantic layer partitions
    "climate_cities",
    "agricultural_locations",
    # Constants
    "COUNTRY_CODE_MAP",
    # Country partitions (shared by World Bank and Economic assets)
    "WORLD_BANK_COUNTRIES",
    "worldbank_country_partitions",
    "GOVERNMENT_DEBT_COUNTRIES",
    "government_debt_partitions",
    "INTEREST_RATE_COUNTRIES",
    "interest_rate_partitions",
    # Static time partitions
    "fiscal_year_partitions",
    "quarterly_partitions",
    "quarterly_all_partitions",
    "monthly_partitions",
    # SEC time-based partitions
    "sec_yearly_partitions",
    "sec_quarterly_partitions",
    "sec_monthly_partitions",
    # Parsers
    "parse_fiscal_year",
    "parse_quarter",
    "parse_month",
    # Generators
    "generate_years",
    "generate_quarters",
    "generate_months",
    # FSDS partitions
    "fsds_quarterly_partitions",
    "generate_fsds_quarters",
    "partition_key_to_fsds_filename",
    "fsds_filename_to_partition_key",
    # ESR partitions
    "esr_market_year_partitions",
    # GATS partitions
    "gats_census_month_partitions",
    "generate_census_months",
]
