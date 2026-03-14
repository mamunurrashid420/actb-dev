# Data Sources

This document describes each external data source we integrate, what data we get from them, and how to add more data from each source.

## Table of Contents

1. [FRED (Federal Reserve Economic Data)](#fred)
2. [BLS (Bureau of Labor Statistics)](#bls)
3. [World Bank](#world-bank)
4. [SEC EDGAR](#sec-edgar)

---

## FRED

### What is FRED?

The Federal Reserve Economic Data (FRED) database provides US economic indicators maintained by the Federal Reserve Bank of St. Louis. It includes over 800,000 time series covering employment, GDP, inflation, interest rates, and more.

**Website:** https://fred.stlouisfed.org/

### Authentication

**API Key Required:** Yes (free)

Get your key: https://fred.stlouisfed.org/docs/api/api_key.html

Add to `.env`:
```bash
FRED_API_KEY=your_key_here
```

### Rate Limits

- No official rate limit documented
- Best practice: Space requests ~1 second apart

### Our Assets

**Source Node:**
```
bronze/fred/all_series
Partitions: None (unpartitioned - all 5 series in one asset)
Series: GDP, UNRATE, CPIAUCSL, PCE, FEDFUNDS
Storage: _data/assets/bronze/fred/all_series/data.parquet
```

**Published Nodes:**
```
gold/economic/growth/gdp[USA]
gold/economic/labor_market/unemployment[USA]
gold/economic/prices/inflation[USA]
gold/economic/prices/consumer_spending[USA]
gold/economic/monetary/interest_rate[USA]
```

### Adding a New FRED Series

Since FRED is unpartitioned (all series in one asset), adding a new series requires updating the asset code:

1. **Find the series ID** on FRED website (e.g., `INDPRO` for Industrial Production)

2. **Edit** `src/pipelines/assets/fred.py`:
```python
@dg.asset(
    key_prefix=['bronze', 'fred'],
    name='all_series',
    group_name='fred',
)
def all_series(context, fred_api):
    """Fetch all FRED series in a single asset."""
    series_ids = [
        'GDP', 'UNRATE', 'CPIAUCSL', 'PCE', 'FEDFUNDS',
        'INDPRO',  # ← Add here
    ]
    # ... rest of implementation
```

3. **Add to crosswalk** in `src/pipelines/assets/reference.py` (if creating published asset):
```python
data = [
    # ... existing entries
    ('fred', 'INDPRO', 'industrial_production', 'Industrial Production Index'),
]
```

4. **Rematerialize** (entire asset, since unpartitioned):
```bash
uv run dg asset materialize --select "bronze/fred/all_series"
```

5. **Create published asset** (optional) in `src/pipelines/assets/economic.py`

---

## BLS

### What is BLS?

The Bureau of Labor Statistics provides US labor market data including job openings, quit rates, wages, and employment costs.

**Website:** https://www.bls.gov/developers/

### Authentication

**API Key Required:** Yes (free)

Register: https://data.bls.gov/registrationEngine/

Add to `.env`:
```bash
BLS_API_KEY=your_key_here
```

### Rate Limits

- **500 queries per day** (per API key)
- **50 requests per 10 seconds**
- Monitor usage carefully!

### Our Assets

**Source Node:**
```
bronze/bls/all_series
Partitions: None (unpartitioned - all 6 series in one asset)
Series:
  - JTS00000000JOL (Job Openings)
  - JTS00000000QUR (Quit Rate)
  - CIU1010000000000A (Wage Inflation)
  - WPUFD4 (Producer Price Index - Food)
  - LNS11300000 (Labor Force Participation Rate)
  - CES0500000003 (Average Hourly Earnings)
Storage: _data/assets/bronze/bls/all_series/data.parquet
```

**Published Nodes:**
```
gold/economic/labor_market/job_openings[USA]
gold/economic/labor_market/quit_rate[USA]
gold/economic/labor_market/wage_inflation[USA]
gold/economic/labor_market/labor_force_participation[USA]
gold/economic/labor_market/hourly_earnings[USA]
gold/economic/prices/producer_prices[USA]
```

### Adding a New BLS Series

Since BLS is unpartitioned (all series in one asset), adding a new series requires updating the asset code:

1. **Find the series ID** using BLS Series ID tool

2. **Edit** `src/pipelines/assets/bls.py`:
```python
@dg.asset(
    key_prefix=['bronze', 'bls'],
    name='all_series',
    group_name='bls',
)
def all_series(context, bls_api):
    """Fetch all BLS series in a single asset."""
    series_ids = [
        'JTS00000000JOL', 'JTS00000000QUR', ...,
        'YOUR_SERIES_ID',  # ← Add here
    ]
    # ... rest of implementation
```

3. **Update crosswalk** if needed

4. **Rematerialize** (entire asset, since unpartitioned):
```bash
uv run dg asset materialize --select "bronze/bls/all_series"
```

### BLS-Specific Notes

- Data uses period codes (`M01` = January, `Q01` = Q1)
- Our resource automatically parses these to `YYYY-MM` format
- Some series are monthly, others quarterly—resource handles both

---

## World Bank

### What is World Bank?

The World Bank Open Data provides economic and development indicators for 200+ countries, including GDP, unemployment, inflation, trade, and emissions.

**Website:** https://data.worldbank.org/

### Authentication

**No API key required** - Public API

### Rate Limits

- No official limit
- Recommended: ~5 requests per second max

### Our Assets

**Source Node:**
```
bronze/world_bank/timeseries
Partitions: country (single-dimension, 3-letter codes)
  Countries: USA, CHN, JPN, DEU, GBR, FRA, KOR, ITA, GRC, EUU, CAN, IND, BRA, AUS, MEX, ESP, NLD, RUS, SAU, TUR
  Indicators (all fetched per country partition):
    - NY.GDP.MKTP.CD (GDP current USD)
    - NY.GDP.PCAP.CD (GDP per capita)
    - GC.DOD.TOTL.GD.ZS (Government debt % GDP)
    - SL.UEM.TOTL.ZS (Unemployment rate)
    - FP.CPI.TOTL.ZG (Inflation, CPI)
    - EN.ATM.CO2E.PC (CO2 emissions per capita)
    - BN.CAB.XOKA.GD.ZS (Current account balance % GDP)
    - FR.INR.RINR (Real interest rate)
Total partitions: 20 (one per country, each contains all indicators)
Storage: _data/assets/bronze/world_bank/timeseries/partition=USA/data.parquet
```

**Published Nodes:**
```
gold/economic/growth/gdp[USA, CHN, JPN, DEU, GBR, FRA, ...]
gold/economic/labor_market/unemployment[USA, CHN, JPN, DEU, ...]
gold/economic/prices/inflation[USA, CHN, JPN, ...]
gold/economic/monetary/interest_rate[USA, CHN, JPN, ...]
gold/economic/trade/balance[USA, CHN, JPN, ...]
gold/economic/fiscal/government_debt[USA, CHN, JPN, ...]
```

### Country Code Mapping

**Important:** The pipeline uses **consistent 3-letter country codes** throughout (USA, CHN, JPN, DEU, GBR, etc).

```python
# All layers use 3-letter codes
WORLDBANK_COUNTRIES = ['USA', 'CHN', 'JPN', 'DEU', 'GBR', ...]

# Both bronze and gold use same partition definition
worldbank_country_partitions = dg.StaticPartitionsDefinition(WORLDBANK_COUNTRIES)
semantic_countries = worldbank_country_partitions  # Same definition
```

### Adding a New Country

1. **Add 3-letter code** to `src/pipelines/partitions.py`:
```python
WORLDBANK_COUNTRIES = [
    'USA', 'CHN', 'JPN', ...,
    'IND',  # ← Add country
]
```

2. **Rematerialize** (fetches all indicators for that country):
```bash
uv run dg asset materialize --select "bronze/world_bank/timeseries" --partition "IND"
```

### Adding a New Indicator

1. **Find indicator code** on World Bank website

2. **Edit** `src/pipelines/partitions.py`:
```python
WORLDBANK_INDICATORS = [
    'NY.GDP.MKTP.CD',
    # ...
    'NEW.INDICATOR.CODE',  # ← Add here
]
```

3. **Update crosswalk** in `reference.py` if creating a published asset

4. **Rematerialize all countries** (to fetch new indicator):
```bash
uv run dg asset materialize --select "bronze/world_bank/timeseries"
# (This will rematerialize all 20 country partitions with the new indicator)
```

---

## SEC EDGAR

### What is SEC EDGAR?

The Securities and Exchange Commission's EDGAR database contains public company filings including annual reports (10-K), quarterly reports (10-Q), insider trading (Form 4), and institutional holdings (13-F).

**Website:** https://www.sec.gov/edgar

### Authentication

**Identity String Required** (no API key)

SEC requires you provide contact information. This is configured in `src/pipelines/config/__init__.py`:

```python
def get_sec_identity() -> str:
    """Return SEC identity string (User-Agent)."""
    return os.getenv('SEC_IDENTITY', 'Your Name your.email@example.com')
```

Set in `.env` (optional, defaults above):
```bash
SEC_IDENTITY="Jane Doe jane.doe@company.com"
```

### Rate Limits

- **10 requests per second** (strictly enforced)
- Our resource includes built-in rate limiting

### Our Assets

SEC uses a **three-layer architecture**:

```
Bronze Layer (metadata) → Silver Layer (extracted data) → Gold Layer (LLM-ready)
```

#### Form 10-K (Annual Reports)

**Bronze:**
```
bronze/sec/form_10k
Partitions: [cik, fiscal_year]
  CIKs: 0000829224 (Starbucks), 0000063908 (McDonald's), 0000320193 (Apple), 0000789019 (Microsoft)
  Fiscal years: FY2020, FY2021, FY2022, FY2023, FY2024, FY2025
Storage: _data/assets/bronze/sec/form_10k/cik={CIK}/fiscal_year={YEAR}/data.parquet
Returns: {found: bool, filing_date: str, form_url: str}
```

**Silver:**
```
silver/sec/form_10k_financials
Partitions: [cik, fiscal_year]
Storage: _data/assets/silver/sec/form_10k_financials/cik={CIK}/fiscal_year={YEAR}/data.parquet
Returns: {
  revenue, net_income, assets, liabilities, equity,
  revenue_growth, profit_margin, roe, debt_to_equity, ...
}
```

**Gold:**
```
gold/companies/financials/annual_report
Partitions: [ticker, fiscal_year]
  Tickers: SBUX, MCD, AAPL, MSFT
Storage: _data/assets/gold/companies/financials/annual_report/ticker={TICKER}/fiscal_year={YEAR}/data.parquet
Returns: Company name, ticker, fiscal year, metrics, narrative summary
```

#### Form 10-Q (Quarterly Reports)

**Bronze:**
```
bronze/sec/form_10q
Partitions: [cik, quarter]
  Quarters: 2020-Q1, 2020-Q2, ..., 2025-Q3 (Q1-Q3 only, no Q4)
Storage: _data/assets/bronze/sec/form_10q/cik={CIK}/quarter={QUARTER}/data.parquet
```

**Silver:**
```
silver/sec/form_10q
Partitions: [cik, quarter]
Storage: _data/assets/silver/sec/form_10q/cik={CIK}/quarter={QUARTER}/data.parquet
```

**Gold:**
```
gold/companies/financials/quarterly_report
Partitions: [ticker, quarter]
Storage: _data/assets/gold/companies/financials/quarterly_report/ticker={TICKER}/quarter={QUARTER}/data.parquet
```

#### Form 4 (Insider Trading)

**Bronze:**
```
bronze/sec/form_4
Partitions: [cik, month]
  Months: 2020-01, 2020-02, ..., 2025-12
Storage: _data/assets/bronze/sec/form_4/cik={CIK}/month={MONTH}/data.parquet
```

**Silver:**
```
silver/sec/form_4_transactions
Partitions: [cik, month]
Storage: _data/assets/silver/sec/form_4_transactions/cik={CIK}/month={MONTH}/data.parquet
Returns: List of insider transactions with amounts, transaction types
```

**Gold:**
```
gold/companies/insider/insider_activity
Partitions: [ticker, month]
Storage: _data/assets/gold/companies/insider/insider_activity/ticker={TICKER}/month={MONTH}/data.parquet
```

#### Form 13-F (Institutional Holdings)

**Different:** This uses **institution CIKs**, not company CIKs.

**Bronze:**
```
bronze/sec/form_13f
Partitions: [cik, quarter]
  Institution CIKs: 0001067983 (Berkshire Hathaway), 0001364742 (Bridgewater Associates)
  Quarters: 2020-Q1, ..., 2025-Q4 (all 4 quarters)
Storage: _data/assets/bronze/sec/form_13f/cik={CIK}/quarter={QUARTER}/data.parquet
```

**Silver:**
```
silver/sec/form_13f
Partitions: [cik, quarter]
Storage: _data/assets/silver/sec/form_13f/cik={CIK}/quarter={QUARTER}/data.parquet
Returns: List of all holdings with shares, values, percentages
```

**Gold:**
```
gold/institutions/portfolio/portfolio_holdings
Partitions: [institution, quarter]
  Institutions: berkshire_hathaway, bridgewater_associates
Storage: _data/assets/gold/institutions/portfolio/portfolio_holdings/institution={INSTITUTION}/quarter={QUARTER}/data.parquet
Returns: {
  institution_name, quarter, holdings_count, total_value,
  top_10_holdings: [...],
  all_holdings: [...]
}
```

### CIK ↔ Ticker Mapping

**Registries** map between CIKs and tickers:

```
silver/reference/company_registry
Columns: cik | ticker | company_name

silver/reference/institution_registry
Columns: cik | institution_id | display_name
```

**Usage:**
```python
# Published assets load the registry
def annual_report(context, company_registry):
    ticker = context.partition_key.keys_by_dimension["ticker"]  # 'AAPL'

    # Map ticker → CIK
    company = company_registry[company_registry['ticker'] == ticker].iloc[0]
    cik = company['cik']  # '0000320193'

    # Load parsed data using CIK
    financials = context.load_asset_value(
        asset_key=dg.AssetKey(['silver', 'sec', 'form_10k_financials']),
        partition_key=f'{cik}|FY2023'
    )
```

### Adding a New Company

**Current approach:** Edit YAML config (will be automated in future)

1. **Edit** `src/pipelines/config/sec_filings.yaml`:
```yaml
companies:
  - ticker: NFLX
    cik: '0001065280'
    name: Netflix Inc.
```

2. **Reload definitions:**
```bash
uv run dg check defs
```

3. **Materialize:**
```bash
# Bronze 10-K
uv run dg asset materialize --select "bronze/sec/form_10k" --partition "0001065280|FY2023"

# Silver
uv run dg asset materialize --select "silver/sec/form_10k_financials" --partition "0001065280|FY2023"

# Gold
uv run dg asset materialize --select "gold/companies/financials/annual_report" --partition "NFLX|FY2023"
```

**Future:** Company lists will be dynamically fetched from SEC API (e.g., S&P 500 constituents).

### Adding an Institution

Similar to companies:

1. **Edit** `src/pipelines/config/sec_filings.yaml`:
```yaml
institutions:
  - institution_id: vanguard
    cik: '0000102909'
    display_name: Vanguard Group Inc.
```

2. **Materialize 13-F data**

### SEC-Specific Notes

- **Fiscal year vs calendar year:** Companies may have different fiscal year ends
- **Form 4 timing:** Insiders must file within 2 business days of transaction
- **13-F threshold:** Only institutions managing $100M+ must file
- **Rate limiting:** SEC is strict—respect the 10 req/sec limit

---

## Summary Table

| Source | Auth | Rate Limit | Partitions | Countries | Published Assets |
|--------|------|------------|------------|-----------|------------------|
| FRED | API key | None official | None (5 series unpartitioned) | US only | 5 |
| BLS | API key | 500/day | None (6 series unpartitioned) | US only | 6 |
| World Bank | None | None official | 20 countries (8 indicators each) | 20 countries | 40+ |
| SEC EDGAR | Identity | 10/sec | 4 companies × multi-period | US companies | 16 |

## Next Steps

- **Add your own data source:** See [ADDING_DATA_SOURCES.md](ADDING_DATA_SOURCES.md)
- **Query the data:** See [ANALYSIS.md](ANALYSIS.md)
- **Understand schedules:** See [OPERATIONS.md](OPERATIONS.md)

---

## Future Data Sources

Planned integrations:
- **Commodity prices** (coffee, oil, metals)
- **Currency exchange rates**
- **Social media sentiment**
- **News aggregation**

Want to add a source? See the tutorial in [ADDING_DATA_SOURCES.md](ADDING_DATA_SOURCES.md)!
