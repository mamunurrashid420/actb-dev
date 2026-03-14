# actBI Data Pipeline

A Dagster-based data pipeline for fetching and processing economic and financial data from 11 external sources including FRED, BLS, BEA, ECB, USDA, World Bank, SEC EDGAR, and PatentsView.

## Overview

This pipeline is the foundation of actBI—an AI-powered Business Intelligence platform. It fetches, processes, and organizes external data into clean, well-structured datasets that both humans and AI systems can easily query and analyze.

**Key features:**
- **Partition-based architecture** for scalable data management
- **Flexible DAG** supporting variable transformation depth
- **Semantic routing** from source-native IDs to user-friendly partitions
- **LLM-optimized** metadata and structure
- **Data quality first** with validation at every step

## Documentation

**New to actBI?** Start here: **[📚 Introduction](docs/INTRODUCTION.md)**

### Getting Started
- **[Getting Started](docs/GETTING_STARTED.md)** - Install and run in 10 minutes
- **[Core Concepts](docs/CONCEPTS.md)** - Understand assets, partitions, and the DAG

### Understanding the System
- **[Architecture](docs/ARCHITECTURE.md)** - Design decisions and patterns
- **[Data Sources](docs/DATA_SOURCES.md)** - FRED, BLS, World Bank, SEC EDGAR details

### Working with the Pipeline
- **[Adding Data Sources](docs/ADDING_DATA_SOURCES.md)** - Step-by-step tutorial
- **[Operations](docs/OPERATIONS.md)** - Running, scheduling, monitoring
- **[Analysis](docs/ANALYSIS.md)** - Query and analyze with Jupyter/DuckDB
- **[Testing](docs/TESTING.md)** - Write tests and ensure quality

### Contributing
- **[Contributing](docs/CONTRIBUTING.md)** - Code standards and PR process

## Quick Start

### Prerequisites

- Python 3.12
- `uv` for dependency management
- FRED API key ([get one here](https://fred.stlouisfed.org/docs/api/api_key.html)) - **Optional**, only needed for US-specific indicators (unemployment, CPI)
- BLS API key ([register here](https://data.bls.gov/registrationEngine/)) - **Optional**, only needed for US labor market and price indicators

### Installation

```bash
# Install dependencies
uv sync

# Create .env file with API keys (optional - only needed for US indicators)
cat > .env << EOF
FRED_API_KEY=your_fred_key_here
BLS_API_KEY=your_bls_key_here
DAGSTER_HOME=$(pwd)/.dagster
EOF

# Create Dagster home directory for persistent storage
mkdir -p .dagster
```

**Important**: Always run `uv sync` after updating dependencies, and ensure the `.dagster` directory exists before starting Dagster.

**Note**: World Bank API requires no authentication. GDP data for all countries is fetched without an API key. BLS and FRED APIs are optional and only needed for US-specific indicators.

### Running the Pipeline

```bash
# Start Dagster UI (default port 3000)
uv run dg dev

# Start Dagster UI on custom port
uv run dg dev --port 3001

# Materialize all assets (from Dagster UI or CLI)
uv run dg asset materialize --select "*"

# Materialize specific asset group
uv run dg asset materialize --select "fred"

# Materialize an asset with all upstream dependencies
uv run dg asset materialize --select "+gold/economic/growth/gdp"

# Manage schedules (21 schedules for automated refresh)
uv run dg schedule list                    # List all schedules and their status
uv run dg schedule start weekly_fred_refresh   # Enable a schedule
uv run dg schedule stop weekly_fred_refresh    # Disable a schedule
```

**Note**: All commands must be run from the `pipelines/` directory where the `.env` file is located.

**Schedules**: The pipeline includes 21 schedules organized by frequency (all start STOPPED, must be manually enabled):

| Frequency | Count | Examples |
|-----------|-------|----------|
| Weekly | 15 | FRED, BLS, World Bank, ECB, SEC forms, BEA/USDA current, indicators |
| Daily | 1 | SEC Form 4 insider trading |
| Monthly | 1 | USDA registries |
| Quarterly | 4 | BEA/USDA bulk, SEC FSDS |

**Key schedules:**
- `weekly_fred_refresh` - Monday 2 AM ET → FRED economic data
- `weekly_bls_refresh` - Friday 7 AM ET → BLS labor data
- `weekly_world_bank_refresh` - Sunday 2 AM ET → World Bank indicators
- `daily_sec_form4_refresh` - Daily 6 AM ET → SEC insider trading
- `quarterly_fsds_refresh` - 15th of Q months → SEC FSDS financial data

View schedules in the UI: http://localhost:3000/schedules

See `docs/generated/SCHEDULES.md` for complete listing.

## Project Structure

```
pipelines/
├── src/                        # Source code
│   └── pipelines/              # Python package (root_module)
│       ├── __init__.py
│       ├── definitions.py      # Dagster definitions (entry point)
│       ├── resources.py        # 11 external API resources
│       ├── io_managers.py      # Custom IO managers (pandas, polars, sharded)
│       ├── partitions.py       # Partition definitions and mappings
│       ├── jobs.py             # 26 job definitions
│       ├── schedules.py        # 21 schedule definitions
│       ├── sensors.py          # 7 sensor definitions
│       ├── checks.py           # Asset checks and validations
│       ├── assets/             # ~90 assets organized by source
│       │   ├── federal_reserve.py  # FRED series
│       │   ├── bls/            # BLS API + bulk (Polars LazyFrames)
│       │   ├── bea/            # BEA NIPA (Polars LazyFrames)
│       │   ├── ecb/            # ECB exchange rates
│       │   ├── usda/           # USDA PSD data
│       │   ├── world_bank.py   # World Bank (country-partitioned)
│       │   ├── sec/            # SEC forms, FSDS, bulk (sharded parquet)
│       │   ├── patents.py      # PatentsView bulk (sharded)
│       │   ├── reference.py    # Crosswalks and lookups
│       │   └── economic.py     # Gold economic indicators
│       └── utils/              # Utility modules
├── tests/                      # Test suite
├── docs/                       # Documentation
│   └── generated/              # Auto-generated docs (always current)
├── _data/
│   ├── assets/                 # Materialized asset outputs (gitignored)
│   └── analytics.duckdb        # DuckDB database (gitignored)
├── .dagster/                   # Dagster run history (gitignored)
├── AI_INSTRUCTIONS.md          # Agent reference (patterns, commands)
├── pyproject.toml              # Dependencies
└── .env                        # Local secrets (gitignored)
```

## Architecture

This project implements a **medallion architecture** with three layers: bronze (raw), silver (parsed/reference), and gold (business-ready). Assets form a flexible DAG from raw sources to published business-ready data.

### Key Concepts

- **Medallion Layers**: Bronze (raw API data) → Silver (parsed/reference data) → Gold (business-ready indicators)
- **Partition-Based Assets**: Use partitions for logically similar data (same structure, different instances)
- **Flexible DAG**: Assets form a dependency graph from bronze → silver → gold with optional intermediate transforms
- **Reference Assets**: Crosswalk routing for semantic → source-native partition mapping (silver layer)
- **Rich Metadata**: Support LLM discovery with `questions_answered` and other published information
- **Hierarchical Storage**: Asset keys map to directory structure for organized persistence

### Documentation

- **[Architecture](docs/ARCHITECTURE.md)** - Asset design patterns, DAG structure, metadata standards, and asset groups
- **[Execution Reference](docs/EXECUTION_REFERENCE.md)** - Detailed examples for jobs, schedules, and sensors
- **[Jupyter Setup](docs/JUPYTER_SETUP.md)** - How to analyze data in Jupyter notebooks
- **[Testing Strategy](docs/TESTING_STRATEGY.md)** - Test organization, patterns, and best practices

### Resources

**FredApiResource** (`src/pipelines/resources.py`):
- Extends `ConfigurableResource` for dependency injection
- Configured with API key from environment via `EnvVar`
- Provides `get_series()` method for fetching FRED data series

**WorldBankApiResource** (`src/pipelines/resources.py`):
- No authentication required
- Provides `get_indicator()` method for fetching World Bank indicators
- Supports country-specific data requests

**BlsApiResource** (`src/pipelines/resources.py`):
- Extends `ConfigurableResource` for dependency injection
- Configured with API key from environment via `EnvVar`
- Provides `get_series()` method for fetching BLS time series data
- Supports monthly and quarterly data with automatic period parsing
- Rate limit: 500 queries/day, 50 requests per 10 seconds

**SecEdgarResource** (`src/pipelines/resources.py`):
- Downloads SEC bulk data files (companyfacts.zip, submissions.zip) with local caching
- Fetches individual filings via direct HTTP using httpx with retry logic (stamina)
- Provides `download_company_facts()`, `download_submissions()`, `fetch_filing_content()` methods
- No API key required but identity string mandatory per SEC rules
- Rate limited: 100ms delay between requests (10 req/sec per SEC guidelines)

### Current Assets

**Bronze Layer** (Raw Data with Source-Native Partitions):

**FRED Economic Data** (`bronze/fred/all_series`):
- Unpartitioned - all 5 series in a single asset
- Series included: 'GDP', 'UNRATE', 'CPIAUCSL', 'PCE', 'FEDFUNDS'
- All series have same structure (date, value, series_id)
- Stored as: `_data/assets/bronze/fred/all_series/data.parquet`

**BLS Labor Market Data** (`bronze/bls/all_series`):
- Unpartitioned - all 6 series in a single asset
- Series included: 'JTS00000000JOL' (job openings), 'JTS00000000QUR' (quit rate), and 4 others
- Monthly and quarterly data with automatic period parsing
- Stored as: `_data/assets/bronze/bls/all_series/data.parquet`

**World Bank Country Indicators** (`bronze/world_bank/timeseries`):
- Partitioned by country only (20 partitions, all indicators per country)
- Countries: USA, CHN, JPN, DEU, GBR, FRA, KOR, ITA, GRC, EUU, CAN, IND, BRA, AUS, MEX, ESP, NLD, RUS, SAU, TUR
- Fetches all 8 indicators per country: GDP, GDP per capita, debt, unemployment, inflation, CO2 emissions, current account, real interest rate
- Stored as: `_data/assets/bronze/world_bank/timeseries/partition=USA/data.parquet`

**SEC EDGAR Filings** (`bronze/sec/`):
- **form_10k** - Annual reports, partitioned by ticker
- **form_10q** - Quarterly reports, partitioned by ticker
- **form_4** - Insider transactions, partitioned by ticker
- **form_13f** - Institutional holdings, partitioned by institution CIK
- Companies: AAPL (Apple), MSFT (Microsoft), SBUX (Starbucks), MCD (McDonald's)
- Institutions: 0001067983 (Berkshire Hathaway), 0001364742 (Bridgewater Associates)
- Stored as: `_data/assets/bronze/sec/form_10k/partition=AAPL/data.parquet`

**Silver Layer** (Parsed Data & Reference Assets):

**Indicator ID Crosswalk** (`silver/reference/indicator_crosswalk`):
- Maps semantic indicator slugs → source-specific series IDs
- Enables intelligent routing from gold assets to appropriate bronze sources
- Example: 'unemployment_rate' → FRED 'UNRATE' (for USA) or World Bank 'SL.UEM.TOTL.ZS' (for other countries)

**SEC Registries** (`silver/reference/`):
- **company_registry** - Maps CIK ↔ ticker ↔ company name
- **institution_registry** - Maps institution CIK ↔ name

**Gold Layer** (Business-Ready Assets with Semantic Partitions):

**Economic Indicators** (`gold/economic/labor_market/`, `gold/economic/growth/`):
- Partitioned by 3-letter country codes: 'USA', 'CHN', 'JPN', 'DEU', 'GBR', 'FRA', 'KOR', 'ITA', 'GRC', 'EUU', 'CAN', 'IND', 'BRA', 'AUS', 'MEX', 'ESP', 'NLD', 'RUS', 'SAU', 'TUR'
- Assets: `unemployment`, `gdp`, `job_openings`, `quit_rate`, `wage_inflation`, `producer_prices`, `labor_force_participation`, `hourly_earnings`
- Uses crosswalk for intelligent routing (FRED for USA data, World Bank for international data)
- Gold assets depend directly on bronze; filtering by indicator happens at runtime
- Includes `questions_answered` metadata for LLM discovery
- Stored as: `_data/assets/gold/economic/labor_market/unemployment/partition=USA/data.parquet`

**SEC Published Filings** (`gold/companies/`, `gold/institutions/`):
- **companies/financials/annual_report** - Partitioned by ticker
- **companies/financials/quarterly_report** - Partitioned by ticker
- **companies/insider/trading_activity** - Partitioned by ticker
- **institutions/holdings/quarterly_positions** - Partitioned by institution CIK
- Tickers: SBUX, MCD, AAPL, MSFT
- Stored as: `_data/assets/gold/companies/financials/annual_report/partition=AAPL/data.parquet`

### IO Manager

**FileSystemIOManager** (`src/pipelines/io_managers.py`):
- Automatically handles different data types:
  - pandas DataFrames → Parquet files (.parquet)
  - Polars LazyFrames → Streaming parquet via `sink_parquet()` (memory-efficient)
  - Dicts → JSON files (.json)
- Handles both partitioned and non-partitioned assets
- Creates hierarchical directories matching asset key structure
- Partitioned assets stored in `partition=KEY/data.parquet` format
- Detects sharded parquet (`part-*.parquet`) and returns `pl.LazyFrame`
- Example: Asset `bronze/world_bank/timeseries` with partition `USA` → File `_data/assets/bronze/world_bank/timeseries/partition=USA/data.parquet`

**Polars LazyFrame Pattern** (for large datasets):
```python
@dg.asset
def large_dataset() -> pl.LazyFrame:
    """Return LazyFrame - IOManager streams to parquet without materializing."""
    return pl.scan_csv(path).filter(...).with_columns(...)
    # Never call .collect() - IOManager handles it
```

See `AI_INSTRUCTIONS.md` for detailed patterns on LazyFrames and sharded parquet.

### DuckDB Integration

**DuckDB Resource** (`duckdb`):
- Enables SQL queries across Parquet files without loading them into memory
- Database file: `_data/analytics.duckdb`
- Use for ad-hoc analysis, complex joins, and cross-asset queries
- Parquet files remain the primary storage format

## Asset Execution Pattern

**Example 1: Unpartitioned Asset (FRED)**

```python
@dg.asset(
    key_prefix=['bronze', 'fred'],
    name='all_series',
    metadata={'layer': 'bronze', 'source': 'federal_reserve'},
    retry_policy=dg.RetryPolicy(max_retries=3, delay=60),
    group_name='fred',
)
def all_series(
    context: dg.AssetExecutionContext,
    fred_api: FredApiResource
) -> pd.DataFrame:
    """Fetch all FRED series in a single asset."""
    series_ids = ['GDP', 'UNRATE', 'CPIAUCSL', 'PCE', 'FEDFUNDS']

    context.log.info(f'Fetching {len(series_ids)} series from FRED...')

    all_data = []
    for series_id in series_ids:
        data = fred_api.get_series(series_id)
        df = pd.DataFrame({
            'date': data.index,
            'value': data.values,
            'series_id': series_id,
        })
        all_data.append(df)

    result = pd.concat(all_data, ignore_index=True)

    context.add_output_metadata({
        'num_records': len(result),
        'num_series': len(series_ids),
        'date_range_start': str(result['date'].min()),
        'date_range_end': str(result['date'].max()),
    })

    context.log.info('Data fetch complete')
    return result
```

**Example 2: Partitioned Asset (World Bank)**

```python
@dg.asset(
    key_prefix=['bronze', 'world_bank'],
    name='timeseries',
    partitions_def=worldbank_country_partitions,
    metadata={'layer': 'bronze', 'source': 'world_bank'},
    retry_policy=dg.RetryPolicy(max_retries=3, delay=60),
    group_name='world_bank',
)
def timeseries(
    context: dg.AssetExecutionContext,
    world_bank_api: WorldBankApiResource
) -> pd.DataFrame:
    """Fetch all indicators for a single country."""
    country = context.partition_key  # 'USA', 'CHN', etc.
    context.log.info(f'Fetching all indicators for {country}...')

    all_data = []
    for indicator in WORLDBANK_INDICATORS:
        df = world_bank_api.get_indicator(indicator, [country])
        df['indicator'] = indicator
        all_data.append(df)

    result = pd.concat(all_data, ignore_index=True)

    context.add_output_metadata({
        'num_records': len(result),
        'country': country,
        'indicators_fetched': len(WORLDBANK_INDICATORS),
    })

    context.log.info('Data fetch complete')
    return result
```

## Adding New Data Sources

### 1. Create a Resource

Add to `src/resources.py`:

```python
class NewApiResource(dg.ConfigurableResource):
    """Resource for New API.

    Attributes:
        api_key: API key for authentication
    """

    api_key: str

    def fetch_data(self, endpoint: str):
        """Fetch data from API endpoint."""
        # Implementation here
        pass
```

### 2. Create Asset Module

Create `src/assets/new_source.py`:

```python
import pandas as pd
import dagster as dg
from resources import NewApiResource

@dg.asset(
    key_prefix=['bronze', 'new_source'],
    name='timeseries',
    metadata={
        'layer': 'bronze',
        'source': 'new_source',
    },
    group_name='new_source',
)
def new_source_timeseries(
    context: dg.AssetExecutionContext,
    new_api: NewApiResource
) -> pd.DataFrame:
    """Fetch data from new source."""
    data = new_api.fetch_data('/endpoint')

    df = pd.DataFrame(data)
    context.add_output_metadata({'num_records': len(df)})

    return df
```

### 3. Register in Definitions

Update `src/definitions.py`:

```python
from assets import new_source
from resources import NewApiResource

defs = dg.Definitions(
    assets=[..., new_source.new_source_timeseries],
    resources={
        ...,
        'new_api': NewApiResource(api_key=dg.EnvVar('NEW_API_KEY')),
    },
)
```

### 4. Add Environment Variable

Add to `.env`:
```
NEW_API_KEY=your_api_key
```

## Configuration

### Environment Variables

Dagster automatically loads `.env` files in local development. Use `EnvVar` in resource configuration:

```python
FredApiResource(api_key=dg.EnvVar('FRED_API_KEY'))
```

This approach:
- Evaluates secrets at runtime (not code-load time)
- Hides values in Dagster UI for security
- Works seamlessly across local and deployed environments

### Dagster Configuration

The project uses a proper Python package structure with `pipelines` as the root module. Configuration in `pyproject.toml`:

```toml
[tool.dg]
directory_type = "project"

[tool.dg.project]
root_module = "pipelines"
```

Start the Dagster UI with:

```bash
uv run dg dev
```

**DAGSTER_HOME**: Set in `.env` to persist run history, schedules, and metadata between server restarts:
```bash
DAGSTER_HOME=$(pwd)/.dagster
```

## Loading Materialized Data

Use the provided helper to load asset outputs:

```python
from load_assets import load_asset

# Load bronze layer assets (raw data)
fred_all = load_asset('bronze/fred/all_series')  # Unpartitioned - all series
bls_all = load_asset('bronze/bls/all_series')  # Unpartitioned - all series
world_bank = load_asset('bronze/world_bank/timeseries', partition='USA')  # All indicators for USA
sec_10k = load_asset('bronze/sec/form_10k', partition='AAPL')  # All 10-K filings for Apple

# Load silver layer assets (reference data)
crosswalk = load_asset('silver/reference/indicator_crosswalk')
company_registry = load_asset('silver/reference/company_registry')

# Load gold layer assets (business-ready data)
unemployment = load_asset('gold/economic/labor_market/unemployment', partition='USA')
gdp_france = load_asset('gold/economic/growth/gdp', partition='FRA')
apple_annual = load_asset('gold/companies/financials/annual_report', partition='AAPL')
```

## Testing

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_assets/test_bls.py
```

## Development

### Code Style

Follow the guidelines in `CODING_STANDARDS.md`:
- Use abbreviated imports (`import dagster as dg`)
- Include type hints on all functions
- Use Google-style docstrings
- Use method chaining for pandas operations

### Project Guidelines

See `../../AI_INSTRUCTIONS.md` for:
- Architectural patterns
- Common tasks and workflows
- Best practices for resources and assets
- Testing strategies

## Dependencies

- **dagster** (>=1.11.16) - Orchestration framework
- **dagster-webserver** (>=1.11.16) - Dagster UI
- **dagster-dg-cli** (>=1.11.16) - Modern dg CLI
- **dagster-duckdb** (>=1.11.16) - DuckDB integration for SQL queries
- **pandas** (>=2.3.3) - Data manipulation
- **fredapi** (>=0.5.2) - FRED API client
- **pyarrow** (>=18.1.0) - Parquet file support
- **pytest** (>=8.4.2) - Testing framework

## License

[Add your license here]
