"""SEC data access with filtering for financials, segments, and company profiles.

This module provides convenient access to SEC data from gold layer assets:
- gold/sec/financials: Financial statements with theme-aware filtering
- gold/sec/segments: Segment financials (geographic, business, product)
- gold/sec/company_profiles: Company metadata (filer category, industry)

Basic usage:
    from shared import data

    # Financials
    df = data.sec.financials(ticker='AAPL', theme='profitability', fiscal_year=2024)

    # Segments (revenue by region, product breakdown)
    df = data.sec.segments(ticker='AAPL', segment_type='geographic')
    df = data.sec.segments(ticker='AAPL', segment_type='business', fiscal_year=2024)

    # Company profiles
    df = data.sec.companies(ticker='AAPL')
    df = data.sec.companies(filer_category='Large Accelerated Filer')

    # Discovery
    data.sec.list_tickers()                    # All tickers in financials
    data.sec.list_segments('AAPL')             # Segment names for a company
    data.sec.list_filer_categories()           # Available filer categories
"""

from pathlib import Path

import pandas as pd
import polars as pl

from shared.data.assets import current_env, get_environment
from shared.data.themes import get_concepts_for_theme

# Asset path for SEC financials (sharded parquet)
_FINANCIALS_ASSET = "gold/sec/financials"


def _get_financials_lazyframe() -> pl.LazyFrame:
    """Load SEC financials as LazyFrame from sharded parquet."""
    env_config = get_environment(current_env())
    base_path = Path(env_config.base_path).resolve()
    asset_dir = base_path / _FINANCIALS_ASSET

    # Find all parquet shards
    parquet_files = sorted(asset_dir.glob("part-*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No parquet files found in {asset_dir}")

    # Scan as lazy dataset
    return pl.scan_parquet(parquet_files)


def financials(
    ticker: str | list[str] | None = None,
    theme: str | list[str] | None = None,
    concept: str | list[str] | None = None,
    fiscal_year: int | list[int] | None = None,
    fiscal_period: str | list[str] | None = None,
    unit: str | list[str] | None = None,
    long: bool = False,
    lazy: bool = False,
) -> "pd.DataFrame | pl.LazyFrame":
    """Query SEC financial data with optional filtering.

    All parameters are optional. When multiple filters are provided, they are
    combined with AND logic. Returns all data if no filters specified.

    Args:
        ticker: Filter by ticker symbol(s). e.g., 'AAPL' or ['AAPL', 'MSFT']
        theme: Filter by theme(s). e.g., 'profitability' or ['profitability', 'revenue']
            Available themes: profitability, revenue, balance_sheet, cash_position,
            cash_flow_operations, cash_flow_investing, cash_flow_financing,
            earnings_per_share, debt_leverage, shareholder_returns, expenses, taxes
        concept: Filter by specific XBRL concept(s). Overrides theme filter if both
            provided.
        fiscal_year: Filter by fiscal year(s). e.g., 2024 or [2023, 2024]
        fiscal_period: Filter by period(s). e.g., 'FY' or ['Q1', 'Q2', 'Q3', 'Q4']
        unit: Filter by currency unit(s). e.g., 'USD' or ['USD', 'EUR']
            Common units: USD (US Dollar), JPY (Japanese Yen), CNY (Chinese Yuan)
        long: If True, return long format (one row per concept). If False (default),
            return wide format with concepts as columns.
        lazy: If True, return Polars LazyFrame (implies long=True).

    Returns:
        pandas DataFrame. Wide format (default) has concepts as columns.
        Long format has columns: ticker, company_name, cik, concept, label,
        value, unit, fiscal_year, fiscal_period, form_type, end_date, filed_date.
        Returns Polars LazyFrame if lazy=True.

    Examples:
        >>> df = data.sec.financials(ticker='AAPL', theme='profitability')  # wide
        >>> df = data.sec.financials(ticker='AAPL', theme='profitability', long=True)
        >>> lf = data.sec.financials(theme='revenue', lazy=True)  # always long
    """
    lf = _get_financials_lazyframe()

    # Build filter expressions
    filters = []

    if ticker:
        tickers = [ticker] if isinstance(ticker, str) else ticker
        filters.append(pl.col("ticker").is_in(tickers))

    if theme and not concept:
        themes = [theme] if isinstance(theme, str) else theme
        concepts_set: set[str] = set()
        for t in themes:
            concepts_set.update(get_concepts_for_theme(t))
        filters.append(pl.col("concept").is_in(list(concepts_set)))

    if concept:
        concepts = [concept] if isinstance(concept, str) else concept
        filters.append(pl.col("concept").is_in(concepts))

    if fiscal_year:
        years = [fiscal_year] if isinstance(fiscal_year, int) else fiscal_year
        filters.append(pl.col("fiscal_year").is_in(years))

    if fiscal_period:
        periods = [fiscal_period] if isinstance(fiscal_period, str) else fiscal_period
        filters.append(pl.col("fiscal_period").is_in(periods))

    if unit:
        units = [unit] if isinstance(unit, str) else unit
        filters.append(pl.col("unit").is_in(units))

    # Apply filters with AND logic
    if filters:
        combined = filters[0]
        for f in filters[1:]:
            combined = combined & f
        lf = lf.filter(combined)

    # Return LazyFrame if requested (always long format)
    if lazy:
        return lf

    # Collect to pandas
    df = lf.collect().to_pandas()

    # Return long format if requested
    if long:
        return df

    # Convert to wide format: pivot concepts to columns
    index_cols = ["ticker", "company_name", "cik", "fiscal_year", "fiscal_period"]
    return df.pivot_table(
        index=index_cols,
        columns="concept",
        values="value",
        aggfunc="first",
    ).reset_index()


def list_tickers() -> list[str]:
    """List all available tickers in SEC financials.

    Returns:
        Sorted list of ticker symbols (e.g., ['A', 'AA', 'AAL', ...])
    """
    lf = _get_financials_lazyframe()
    return lf.select("ticker").unique().collect()["ticker"].sort().to_list()


def list_concepts(theme: str | None = None) -> list[str]:
    """List available XBRL concepts, optionally filtered by theme.

    Args:
        theme: If provided, returns only concepts for that theme.
            If None, returns all concepts in the dataset.

    Returns:
        Sorted list of concept names.
    """
    if theme:
        return sorted(get_concepts_for_theme(theme))
    lf = _get_financials_lazyframe()
    return lf.select("concept").unique().collect()["concept"].sort().to_list()


def list_units() -> list[str]:
    """List all available currency units in SEC financials.

    Returns:
        Sorted list of currency units (e.g., ['CNY', 'EUR', 'JPY', 'USD', ...])
    """
    lf = _get_financials_lazyframe()
    return lf.select("unit").unique().collect()["unit"].sort().to_list()


# =============================================================================
# SEGMENTS
# =============================================================================

# Asset path for SEC segments
_SEGMENTS_ASSET = "gold/sec/segments"


def _get_segments_lazyframe() -> pl.LazyFrame:
    """Load SEC segments as LazyFrame."""
    env_config = get_environment(current_env())
    base_path = Path(env_config.base_path).resolve()
    asset_path = base_path / _SEGMENTS_ASSET / "data.parquet"

    if not asset_path.exists():
        raise FileNotFoundError(f"Segments data not found at {asset_path}")

    return pl.scan_parquet(asset_path)


def segments(
    ticker: str | list[str] | None = None,
    segment_type: str | list[str] | None = None,
    segment_name: str | list[str] | None = None,
    concept: str | list[str] | None = None,
    fiscal_year: int | list[int] | None = None,
    fiscal_period: str | list[str] | None = None,
    use_raw_names: bool = False,
    lazy: bool = False,
) -> "pd.DataFrame | pl.LazyFrame":
    """Query SEC segment data with optional filtering.

    Segment data provides financial metrics broken down by business segment,
    geographic region, product line, etc.

    Segment names are normalized to snake_case by default (e.g., 'us', 'china',
    'intl_operated'). This provides continuity across years despite raw SEC
    name variations (e.g., 'US', 'UnitedStates', 'USMarket' all become 'us').

    Args:
        ticker: Filter by ticker symbol(s). e.g., 'AAPL' or ['AAPL', 'MSFT']
        segment_type: Filter by segment type. Options: business, geographic,
            product, equity, investment, consolidation, legal_entity, other
        segment_name: Filter by segment name(s). Uses canonical names by default
            (e.g., 'us', 'china', 'intl_operated'). Set use_raw_names=True for
            original SEC names.
        concept: Filter by XBRL concept(s). e.g., 'RevenueFromContractWithCustomer'
        fiscal_year: Filter by fiscal year(s). e.g., 2024 or [2023, 2024]
        fiscal_period: Filter by period(s). e.g., 'FY' or ['Q1', 'Q2', 'Q3', 'Q4']
        use_raw_names: If True, filter and return raw SEC segment names instead
            of normalized canonical names. Default False.
        lazy: If True, return Polars LazyFrame.

    Returns:
        pandas DataFrame with columns: ticker, company_name, cik, concept, label,
        value, unit, fiscal_year, fiscal_period, form_type, segment_type,
        segment_name (canonical or raw depending on use_raw_names).
        Returns Polars LazyFrame if lazy=True.

    Examples:
        >>> df = data.sec.segments(ticker='AAPL', segment_type='geographic')
        >>> df = data.sec.segments(ticker='MCD', segment_name='us')  # canonical
        >>> df = data.sec.segments(
        ...     ticker='MCD', segment_name='USMarket', use_raw_names=True
        ... )
    """
    lf = _get_segments_lazyframe()

    # Determine which segment_name column to use
    name_col = "segment_name" if use_raw_names else "segment_name_canonical"

    filters = []

    if ticker:
        tickers = [ticker] if isinstance(ticker, str) else ticker
        filters.append(pl.col("ticker").is_in(tickers))

    if segment_type:
        types = [segment_type] if isinstance(segment_type, str) else segment_type
        filters.append(pl.col("segment_type").is_in(types))

    if segment_name:
        names = [segment_name] if isinstance(segment_name, str) else segment_name
        filters.append(pl.col(name_col).is_in(names))

    if concept:
        concepts = [concept] if isinstance(concept, str) else concept
        filters.append(pl.col("concept").is_in(concepts))

    if fiscal_year:
        years = [fiscal_year] if isinstance(fiscal_year, int) else fiscal_year
        filters.append(pl.col("fiscal_year").is_in(years))

    if fiscal_period:
        periods = [fiscal_period] if isinstance(fiscal_period, str) else fiscal_period
        filters.append(pl.col("fiscal_period").is_in(periods))

    if filters:
        combined = filters[0]
        for f in filters[1:]:
            combined = combined & f
        lf = lf.filter(combined)

    # Rename to consistent 'segment_name' column for output
    if not use_raw_names:
        lf = lf.with_columns(pl.col("segment_name_canonical").alias("segment_name"))

    if lazy:
        return lf

    return lf.collect().to_pandas()


def list_segments(
    ticker: str,
    segment_type: str | None = None,
    use_raw_names: bool = False,
) -> list[str]:
    """List segment names for a company.

    Returns canonical (normalized) segment names by default. These are
    snake_case names that are consistent across years (e.g., 'us' instead
    of 'US', 'UnitedStates', 'USMarket' variations).

    Args:
        ticker: Company ticker (required).
        segment_type: Optional filter by segment type (business, geographic,
            product, equity, investment, consolidation, legal_entity, other).
        use_raw_names: If True, return raw SEC segment names instead of
            normalized canonical names. Default False.

    Returns:
        Sorted list of segment names for that company.

    Examples:
        >>> data.sec.list_segments('AAPL')  # Canonical segment names
        >>> data.sec.list_segments('MCD', segment_type='business')
        ['intl_licensed', 'intl_operated', 'us']
        >>> data.sec.list_segments('MCD', use_raw_names=True)  # Raw SEC names
    """
    lf = _get_segments_lazyframe()
    lf = lf.filter(pl.col("ticker") == ticker)
    if segment_type:
        lf = lf.filter(pl.col("segment_type") == segment_type)

    name_col = "segment_name" if use_raw_names else "segment_name_canonical"
    return lf.select(name_col).unique().collect()[name_col].sort().to_list()


# =============================================================================
# COMPANIES
# =============================================================================

# Asset path for SEC company profiles
_COMPANIES_ASSET = "gold/sec/company_profiles"


def _get_companies_lazyframe() -> pl.LazyFrame:
    """Load SEC company profiles as LazyFrame."""
    env_config = get_environment(current_env())
    base_path = Path(env_config.base_path).resolve()
    asset_path = base_path / _COMPANIES_ASSET / "data.parquet"

    if not asset_path.exists():
        raise FileNotFoundError(f"Company profiles data not found at {asset_path}")

    return pl.scan_parquet(asset_path)


def companies(
    ticker: str | list[str] | None = None,
    filer_category: str | list[str] | None = None,
    sic_code: int | list[int] | None = None,
    country: str | list[str] | None = None,
    state: str | list[str] | None = None,
    lazy: bool = False,
) -> "pd.DataFrame | pl.LazyFrame":
    """Query SEC company profile data with optional filtering.

    Company profiles contain metadata about SEC filers including industry
    classification, filer category, and location.

    Args:
        ticker: Filter by ticker symbol(s). e.g., 'AAPL' or ['AAPL', 'MSFT']
        filer_category: Filter by SEC filer category. Options:
            'Large Accelerated Filer', 'Accelerated Filer', 'Non-accelerated Filer',
            'Unknown'
        sic_code: Filter by SIC industry code(s). e.g., 3826 or [3826, 3674]
        country: Filter by country of business. e.g., 'US'
        state: Filter by state of business. e.g., 'CA' or ['CA', 'NY', 'TX']
        lazy: If True, return Polars LazyFrame.

    Returns:
        pandas DataFrame with columns: ticker, company_name, cik, sic_code,
        filer_category, is_wksi, country_business, state_business,
        country_incorporation, fiscal_year_end_month.
        Returns Polars LazyFrame if lazy=True.

    Examples:
        >>> df = data.sec.companies(ticker='AAPL')  # Apple's profile
        >>> df = data.sec.companies(filer_category='Large Accelerated Filer')
        >>> df = data.sec.companies(state='CA')  # California companies
    """
    lf = _get_companies_lazyframe()

    filters = []

    if ticker:
        tickers = [ticker] if isinstance(ticker, str) else ticker
        filters.append(pl.col("ticker").is_in(tickers))

    if filer_category:
        categories = (
            [filer_category] if isinstance(filer_category, str) else filer_category
        )
        filters.append(pl.col("filer_category").is_in(categories))

    if sic_code:
        codes = [sic_code] if isinstance(sic_code, int) else sic_code
        filters.append(pl.col("sic_code").is_in(codes))

    if country:
        countries = [country] if isinstance(country, str) else country
        filters.append(pl.col("country_business").is_in(countries))

    if state:
        states = [state] if isinstance(state, str) else state
        filters.append(pl.col("state_business").is_in(states))

    if filters:
        combined = filters[0]
        for f in filters[1:]:
            combined = combined & f
        lf = lf.filter(combined)

    if lazy:
        return lf

    return lf.collect().to_pandas()


def list_filer_categories() -> list[str]:
    """List all available filer categories.

    Returns:
        Sorted list of filer categories (e.g., ['Accelerated Filer', ...])
    """
    lf = _get_companies_lazyframe()
    return (
        lf
        .select("filer_category")
        .unique()
        .collect()["filer_category"]
        .sort()
        .to_list()
    )
