# Data Pipeline - Agent Reference

**For detailed explanations, see pipelines/README.md (human docs)**

## Current State

### Partitions (see `partitions.py`)

The pipeline uses a **simplified single-dimension partition scheme**:

```python
# Unpartitioned assets (small, stable datasets that refresh together)
bronze/fred/all_series      # 5 series in one asset
bronze/bls/all_series       # 6 series in one asset

# Country-based partitions (20 countries, 3-letter codes)
worldbank_country_partitions: ['USA', 'CHN', 'JPN', 'DEU', 'GBR', 'FRA', 'KOR', 'ITA', 'GRC', 'EUU', 'CAN', 'IND', 'BRA', 'AUS', 'MEX', 'ESP', 'NLD', 'RUS', 'SAU', 'TUR']
semantic_countries: ['USA', 'CHN', 'JPN', 'DEU', 'GBR', 'FRA', 'KOR', 'ITA', 'GRC', 'EUU', 'CAN', 'IND', 'BRA', 'AUS', 'MEX', 'ESP', 'NLD', 'RUS', 'SAU', 'TUR']  # Gold layer uses same 3-letter codes

# Time-based partitions (SEC filings)
sec_yearly_partitions: ['2020', '2021', '2022', '2023', '2024', '2025']  # 10-K
sec_quarterly_partitions: ['2020-Q1', '2020-Q2', ..., '2025-Q4']  # 10-Q, 13-F
sec_monthly_partitions: ['2020-01', '2020-02', ..., '2025-12']  # Form 4
fsds_quarterly_partitions: ['2009-Q1', ..., current_quarter]  # FSDS (auto-extends)
```

### Assets (~90 total)

Summary by layer:
- **Bronze**: ~51 assets (raw ingestion from external APIs)
- **Silver**: ~21 assets (cleaned, enriched, reference tables)
- **Gold**: ~18 assets (business-ready, LLM-accessible)

See `docs/generated/DATA_INVENTORY.md` for complete listing.

**Key asset categories:**

| Category | Bronze | Silver | Gold |
|----------|--------|--------|------|
| FRED | `series_registry`, `series` | - | - |
| BLS API | `all_series` | - | - |
| BLS Bulk | `cpi`, `labor_force`, `employment`, `jolts` (+ downloads) | - | - |
| BEA | `nipa_bulk`, `nipa_current` | `nipa_data` | - |
| ECB | `exchange_rates` | - | - |
| USDA | `psd_bulk`, `psd_current` | `psd_data` | - |
| World Bank | `timeseries` (20 countries) | - | - |
| SEC Registry | `sec_filer_registry` | `company_registry`, `institution_registry` | - |
| SEC Bulk | `company_facts_download`, `company_facts`, `submissions` | `xbrl_taxonomy` | - |
| SEC Forms | `form_10k_text`, `form_10q_text`, `form_4`, `form_13f` | sections/transactions | reports/activity/holdings |
| SEC FSDS | `fsds` (67 quarters) | segments, financials, metadata | segments, financials, company_profiles |
| Patents | `bulk` (8 tables) | - | - |
| NASA POWER | `daily`, `monthly` | - | - |
| Economic | - | - | `unemployment`, `gdp`, `inflation`, etc. (country-partitioned) |
| Agriculture | - | - | `daily` (location-partitioned) |

### Groups

```python
# Data sources
'fred', 'bls', 'bea', 'ecb', 'usda', 'world_bank', 'sec_filings', 'patents', 'nasa_power', 'noaa'

# Reference data
'reference'

# Published indicators
'country_indicators', 'monetary_indicators', 'fiscal_indicators',
'agriculture_indicators', 'climate_indicators'
```

### Jobs (26 total)

See `docs/generated/SCHEDULES.md` for complete details.

```python
# Agriculture (4 jobs)
'nasa_power_raw_refresh'          # NASA POWER raw data (all locations)
'agriculture_indicators_refresh'  # Published agriculture indicators
'agriculture_full_pipeline'       # Complete pipeline (raw → published)
'brazil_coffee_refresh'           # Brazil coffee regions only

# SEC (9 jobs)
'sec_bulk_downloads_refresh'      # Submissions + company facts bulk
'sec_registry_refresh'            # SEC filer registry
'sec_form4_refresh'               # Form 4 (monthly partitions)
'sec_10k_refresh'                 # 10-K (yearly partitions)
'sec_10q_refresh'                 # 10-Q (quarterly partitions)
'sec_13f_refresh'                 # 13-F (quarterly partitions)
'sec_fsds_refresh'                # FSDS (quarterly since 2009)
'sec_financials_refresh'          # Extract financials from bulk
'sec_gold_refresh'                # All SEC gold assets

# BLS Bulk (5 jobs)
'bls_cpi_refresh'                 # CPI-U from FTP
'bls_labor_force_refresh'         # Labor force stats from FTP
'bls_employment_refresh'          # CES employment from FTP
'bls_jolts_refresh'               # JOLTS from FTP
'bls_bulk_refresh'                # All BLS bulk datasets

# Other (4 jobs)
'patents_refresh'                 # PatentsView bulk download (~5.4 GB)
'bea_nipa_bulk_refresh'           # BEA NIPA flat files
'usda_psd_bulk_refresh'           # USDA PSD CSV data
```

### Schedules (21 total, all start STOPPED)

See `docs/generated/SCHEDULES.md` for complete details.

```python
# Weekly - Bronze source data
'weekly_fred_refresh'             # Mon 2 AM ET → group:fred
'weekly_bls_refresh'              # Fri 7 AM ET → group:bls
'weekly_world_bank_refresh'       # Sun 2 AM ET → group:world_bank
'weekly_ecb_exchange_rates_refresh'  # Mon 3 AM ET → group:ecb
'weekly_nasa_power_refresh'       # Mon 3 AM ET → nasa_power job
'weekly_bea_current_refresh'      # Mon 5 AM ET → bronze/bea/nipa_current
'weekly_usda_current_refresh'     # Mon 4 AM ET → bronze/usda/psd_current

# Weekly - SEC (time-partitioned)
'weekly_sec_registry_refresh'     # Sun 1 AM ET → sec_registry job
'weekly_sec_bulk_refresh'         # Sun 2 AM ET → sec_bulk_downloads job
'weekly_sec_10k_refresh'          # Mon 2 AM ET → 10-K job
'weekly_sec_10q_refresh'          # Mon 2 AM ET → 10-Q job
'weekly_sec_13f_refresh'          # Mon 2 AM ET → 13-F job

# Weekly - Published indicators
'weekly_combined_indicators'      # Mon 4 AM ET → group:country_indicators
'weekly_fiscal_indicators'        # Mon 4 AM ET → group:fiscal_indicators
'weekly_monetary_indicators'      # Mon 4 AM ET → group:monetary_indicators
'weekly_agriculture_refresh'      # Mon 5 AM ET → agriculture_indicators job

# Daily
'daily_sec_form4_refresh'         # Daily 6 AM ET → Form 4 job

# Monthly
'monthly_usda_registry_refresh'   # 1st of month 2 AM ET → USDA registries

# Quarterly
'quarterly_bea_bulk_refresh'      # 1st of Jan/Apr/Jul/Oct → BEA NIPA bulk
'quarterly_usda_bulk_refresh'     # 1st of Jan/Apr/Jul/Oct → USDA PSD bulk
'quarterly_fsds_refresh'          # 15th of Jan/Apr/Jul/Oct → FSDS job
```

### Sensors (7 total, event-driven, check daily)

All sensors check daily (minimum_interval_seconds=86400) and start STOPPED.

```python
# PatentsView (S3 Last-Modified)
'patentsview_update_sensor'       # Quarterly releases → patents_refresh job

# BLS FTP (Last-Modified header)
'bls_cpi_update_sensor'           # Monthly updates → bls_cpi_refresh job
'bls_labor_force_update_sensor'   # Monthly updates → bls_labor_force_refresh job
'bls_employment_update_sensor'    # Monthly updates → bls_employment_refresh job
'bls_jolts_update_sensor'         # Monthly updates → bls_jolts_refresh job

# BEA/USDA (HTTP Last-Modified)
'bea_nipa_update_sensor'          # GDP estimates → bea_nipa_bulk job
'usda_psd_update_sensor'          # WASDE reports → usda_psd_bulk job
```

## Architecture: Medallion Pattern

The pipeline uses a **three-layer medallion architecture** (bronze/silver/gold) with **simplified partitioning**:

### Design Principles

1. **Single-dimension partitions**: No multi-dimensional partition explosion
2. **Unpartitioned for small datasets**: FRED, BLS, BEA, ECB, USDA are single assets
3. **Time-based SEC partitions**: Yearly (10-K), quarterly (10-Q, 13-F), monthly (Form 4)
4. **Direct dependencies**: Same partition flows bronze→silver; gold aggregates via AllPartitionsMapping
5. **Layered automation**: Bronze (schedules/sensors) → Silver/Gold (AutomationCondition)

### Bronze Layer (Raw Ingestion)
- **Purpose**: Raw data from external APIs, unchanged
- **Partitions**: Simple identifiers (3-letter country codes, tickers) or unpartitioned
- **Key prefix**: `['bronze', 'source_name']`
- **No dependencies**: Source nodes fetch directly from APIs
- **Example**: `bronze/fred/all_series`, `bronze/world_bank/timeseries`, `bronze/sec/form_10k`

### Silver Layer (Cleaned & Enriched)
- **Purpose**: Validated, cleaned, and enriched data; reference tables and crosswalks
- **Partitions**: Same as bronze (same partition definition flows through)
- **Key prefix**: `['silver', 'domain']`
- **Dependencies**: Bronze assets via direct function parameters
- **Example**: `silver/sec/form_10k_financials`, `silver/reference/indicator_crosswalk`

### Gold Layer (Business-Ready)
- **Purpose**: Denormalized, aggregated; optimized for LLM queries
- **Partitions**: Same as upstream (direct dependencies, no mapping needed)
- **Key prefix**: `['gold', 'domain', 'subdomain']`
- **Dependencies**: Silver/bronze assets via direct function parameters
- **Metadata**: `{'layer': 'gold', 'visibility': 'llm_accessible'}`
- **Example**: `gold/economic/labor_market/unemployment`, `gold/companies/financials/annual_report`

### Architecture Rules

1. **Use partitions for same-structure data** (not individual assets)
2. **Prefer unpartitioned** for small, stable datasets (< 10 items)
3. **Single dimension only**: Country OR time (year/quarter/month), never combinations
4. **Direct dependencies**: Upstream data flows through function parameters
5. **Filter at runtime**: Query DataFrames to extract specific subsets

### Provenance Rule (CRITICAL for Compliance)

**Always use direct dependencies.** Pass upstream data through function parameters
so Dagster tracks provenance automatically:

```python
# CORRECT - direct dependency, same time partition flows through
@asset(partitions_def=sec_yearly_partitions)
def silver_form_10k_sections(
    bronze_sec_form_10k_text: pd.DataFrame,  # Same partition flows through
) -> pd.DataFrame:
    """Parse sections from 10-K filings."""
    return bronze_sec_form_10k_text.pipe(parse_sections)

# CORRECT - unpartitioned gold aggregates all partitions
@asset(
    ins={'silver_sec_form_10k_sections': AssetIn(partition_mapping=AllPartitionsMapping())},
)
def gold_annual_reports(
    silver_sec_form_10k_sections: dict[str, pd.DataFrame],  # All years
) -> pd.DataFrame:
    """All annual reports combined."""
    return pd.concat(silver_sec_form_10k_sections.values())

# CORRECT - country-partitioned with unpartitioned upstream
@asset(partitions_def=worldbank_country_partitions)
def gold_unemployment(
    context: AssetExecutionContext,
    bronze_fred_all_series: pd.DataFrame,  # All series in one DataFrame
    bronze_world_bank_timeseries: pd.DataFrame,  # Country partition flows through
) -> pd.DataFrame:
    """Unemployment rate by country."""
    country = context.partition_key  # Simple string: "USA", "CHN", etc.
    # Filter at runtime from unpartitioned or same-partition data
    ...
```

Why this matters:
- Dagster tracks provenance for **function parameter** dependencies
- No `load_asset_value()` calls needed → cleaner code
- A test enforces this rule - see `tests/test_definitions.py::TestProvenanceTracking`

## Partition Syntax

```python
# Single-dimensional (simple string access)
partition_key = context.partition_key  # "USA", "2024", "2024-Q3", "2024-01", etc.
file_path = "partition=2024/data.parquet"

# Unpartitioned assets
# No partition_key access needed - returns all data in one DataFrame
```

**Rule:** Always use simple string partition keys, never multi-dimensional

## Code Patterns

### Bronze Node (Unpartitioned - Small Datasets)

```python
@asset(
    key_prefix=['bronze', 'fred'],
    name='all_series',
    group_name='fred',
)
def all_series(
    context: AssetExecutionContext,
    fred_api: FredApiResource,
) -> pd.DataFrame:
    """Fetch all FRED series in a single asset."""
    series_ids = ['GDP', 'UNRATE', 'CPIAUCSL', 'PCE', 'FEDFUNDS']

    all_data = []
    for series_id in series_ids:
        context.log.info(f'Fetching {series_id}...')
        data = fred_api.get_series(series_id)
        df = pd.DataFrame({
            'date': data.index,
            'value': data.values,
            'series_id': series_id,
        })
        all_data.append(df)

    result = pd.concat(all_data, ignore_index=True)
    context.add_output_metadata({'num_records': len(result)})
    return result
```

### Bronze Node (Country-Partitioned)

```python
from pipelines.partitions import worldbank_country_partitions, WORLDBANK_INDICATORS

@asset(
    key_prefix=['bronze', 'world_bank'],
    name='timeseries',
    partitions_def=worldbank_country_partitions,
    group_name='world_bank',
)
def timeseries(
    context: AssetExecutionContext,
    world_bank_api: WorldBankApiResource,
) -> pd.DataFrame:
    """Fetch all indicators for a single country."""
    country = context.partition_key  # Simple string: "USA", "CHN", "JPN", etc.

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
    return result
```

### Bronze Node (Time-Partitioned SEC)

```python
from pipelines.partitions import sec_yearly_partitions

@asset(
    key_prefix=['bronze', 'sec'],
    name='form_10k_text',
    partitions_def=sec_yearly_partitions,  # Yearly: "2020", "2021", etc.
    group_name='sec_filings',
)
def form_10k_text(
    context: AssetExecutionContext,
    sec_edgar: SecEdgarResource,
    silver_sec_company_registry: pd.DataFrame,  # All enabled companies
) -> pd.DataFrame:
    """Fetch all 10-K filings for a given year (all companies)."""
    year = context.partition_key  # Simple string: "2024"

    context.log.info(f'Fetching 10-K filings for year {year}...')

    # Get all enabled companies from registry
    companies = silver_sec_company_registry['cik'].tolist()

    # Fetch filings for all companies for this year
    all_filings = []
    for cik in companies:
        filings = sec_edgar.get_filings(cik, form_type='10-K', year=year)
        all_filings.extend(filings)

    return pd.DataFrame(all_filings)
```

### Silver Node (Time-Partitioned SEC)

```python
from pipelines.partitions import sec_yearly_partitions

@asset(
    key_prefix=['silver', 'sec'],
    name='form_10k_sections',
    partitions_def=sec_yearly_partitions,  # Same as bronze (yearly)
    group_name='sec_filings',
)
def form_10k_sections(
    context: AssetExecutionContext,
    bronze_sec_form_10k_text: pd.DataFrame,  # Dagster passes matching partition
) -> pd.DataFrame:
    """Extract and parse sections from 10-K filings for a year."""
    year = context.partition_key  # Simple string: "2024"

    # Clean and validate - data already filtered to this year
    df = (
        bronze_sec_form_10k_text
        .pipe(extract_sections)
        .pipe(parse_financial_data)
    )

    context.add_output_metadata({
        'num_filings': len(df),
        'year': year,
    })
    return df
```

### Gold Node (Aggregating Time-Partitioned Data)

SEC gold assets are **unpartitioned** - they aggregate all time partitions into a single dataset:

```python
@asset(
    key_prefix=['gold', 'companies', 'financials'],
    name='annual_reports',
    # No partitions_def - aggregates all years
    ins={
        'silver_sec_form_10k_sections': AssetIn(
            partition_mapping=AllPartitionsMapping(),  # All years
        ),
    },
    metadata={'layer': 'gold', 'visibility': 'llm_accessible'},
    group_name='sec_filings',
)
def annual_reports(
    context: AssetExecutionContext,
    silver_sec_form_10k_sections: dict[str, pd.DataFrame],  # All partitions as dict
) -> pd.DataFrame:
    """All annual reports aggregated into one dataset."""
    # Combine all years
    all_data = pd.concat(silver_sec_form_10k_sections.values(), ignore_index=True)

    return (
        all_data
        .pipe(format_for_llm)
    )
```

### Gold Node (Filtering Unpartitioned Data)

```python
@asset(
    key_prefix=['gold', 'economic', 'labor_market'],
    name='unemployment',
    partitions_def=semantic_countries,
    ins={
        'bronze_fred_all_series': AssetIn(
            key=AssetKey(['bronze', 'fred', 'all_series']),
        ),
    },
    metadata={'layer': 'gold', 'visibility': 'llm_accessible'},
    group_name='country_indicators',
)
def unemployment(
    context: AssetExecutionContext,
    bronze_fred_all_series: pd.DataFrame,
    bronze_world_bank_timeseries: pd.DataFrame,
) -> pd.DataFrame:
    """Unemployment rate by country."""
    country = context.partition_key  # Simple string: 'USA', 'CHN', 'JPN', etc.

    if country == 'USA':
        # Filter FRED data for US unemployment
        return (
            bronze_fred_all_series
            .query("series_id == 'UNRATE'")
            .drop(columns=['series_id'])
        )
    else:
        # World Bank data already filtered by partition (country matches)
        return (
            bronze_world_bank_timeseries
            .query("indicator == 'SL.UEM.TOTL.ZS'")
            .drop(columns=['indicator'])
        )
```

### Polars LazyFrame Pattern (Memory-Efficient Streaming)

For large datasets, return `pl.LazyFrame` instead of `pd.DataFrame` to avoid memory bloat.
The IOManager handles streaming writes via `sink_parquet()`.

**When to use:**
- Datasets > 1M rows or > 100MB
- Bulk downloads that would OOM with pandas
- Denormalized joins across large dimension tables

```python
import polars as pl

@asset(key_prefix=['bronze', 'bls'], name='cpi')
def cpi(
    context: AssetExecutionContext,
    bronze_bls_cpi_download: dict,  # Downloaded file paths
) -> pl.LazyFrame:
    """Parse CPI data - returns LazyFrame for streaming write."""
    data_path = bronze_bls_cpi_download['data_path']

    return (
        pl.scan_csv(data_path, separator='\t')
        .filter(pl.col('value').is_not_null())
        .with_columns([
            pl.col('year').cast(pl.Int32),
            pl.col('value').cast(pl.Float64),
        ])
    )
    # DO NOT call .collect() - IOManager handles it via sink_parquet()
```

**IOManager behavior:**
- Detects `pl.LazyFrame` return type
- Calls `sink_parquet()` for streaming write to `data.parquet`
- On read: Returns `pl.LazyFrame` via `scan_parquet()` for continued lazy evaluation

**Current assets using this pattern:**
- `bronze/bls/cpi`, `bronze/bls/labor_force`, `bronze/bls/employment`, `bronze/bls/jolts`
- `bronze/bea/nipa_bulk`, `bronze/bea/nipa_current`, `silver/bea/nipa_data`

**Key rules:**
1. Never call `.collect()` in the asset - let IOManager handle materialization
2. Use `pl.scan_csv()` or `pl.scan_parquet()` to start lazy
3. Chain transformations lazily (filter, with_columns, join, etc.)
4. IOManager streams result to disk with minimal memory footprint

### Sharded Parquet Pattern (Very Large Datasets)

For datasets > 50M rows, use PyArrow `ParquetWriter` with row-based sharding.
This creates multiple `part-NNNN.parquet` files for parallel reads.

**When to use:**
- Datasets > 50M rows
- When downstream consumers need parallel read capability
- When single-file writes would exceed memory

```python
import pyarrow as pa
import pyarrow.parquet as pq

ROWS_PER_SHARD = 6_000_000   # ~35MB per shard
WRITE_BATCH_SIZE = 10_000    # ~10MB peak memory

@asset(key_prefix=['bronze', 'sec'], name='company_facts')
def company_facts(
    context: AssetExecutionContext,
    bronze_sec_company_facts_download: dict,
) -> None:
    """Stream to sharded parquet - IOManager not used for output."""
    output_dir = Path('_data/assets/bronze/sec/company_facts')
    output_dir.mkdir(parents=True, exist_ok=True)

    shard_num = 0
    row_count = 0
    writer = None
    batch_records = []

    for record in stream_from_zip(bronze_sec_company_facts_download['zip_path']):
        batch_records.append(record)

        if len(batch_records) >= WRITE_BATCH_SIZE:
            batch = create_record_batch(batch_records)

            # Start new shard if needed
            if writer is None or row_count >= ROWS_PER_SHARD:
                if writer:
                    writer.close()
                shard_path = output_dir / f'part-{shard_num:04d}.parquet'
                writer = pq.ParquetWriter(str(shard_path), SCHEMA)
                shard_num += 1
                row_count = 0

            writer.write_batch(batch)
            row_count += len(batch_records)
            batch_records = []

    # Final cleanup
    if batch_records and writer:
        writer.write_batch(create_record_batch(batch_records))
    if writer:
        writer.close()
```

**IOManager behavior on read:**
- Detects `part-*.parquet` files in directory
- Returns `pl.LazyFrame` via `scan_parquet("path/*.parquet")`
- Enables predicate pushdown and parallel reads

**Current assets using this pattern:**
- `bronze/sec/company_facts` (~119M rows, ~20 shards, ~35MB each)
- `bronze/sec/fsds` NUM files (~120M rows per quarter)
- `bronze/patents/bulk` citations (~151M rows)

**Key rules:**
1. Asset returns `None` - writes directly to filesystem
2. Use PyArrow `ParquetWriter` for true streaming
3. Shard by row count (not file count) for even sizes
4. Use small batch sizes (10K rows) for minimal memory (~10MB peak)

## Commands

```bash
# Materialize assets (use dg launch --assets)
DAGSTER_HOME=.dagster uv run dg launch --assets "bronze/fred/all_series"                    # Unpartitioned
DAGSTER_HOME=.dagster uv run dg launch --assets "bronze/world_bank/timeseries"              # All countries
DAGSTER_HOME=.dagster uv run dg launch --assets "bronze/world_bank/timeseries" --partition "USA"
DAGSTER_HOME=.dagster uv run dg launch --assets "bronze/sec/form_10k_text" --partition "2024"  # Yearly

# Materialize silver assets (cleaned & enriched)
DAGSTER_HOME=.dagster uv run dg launch --assets "silver/sec/form_10k_sections"              # All years
DAGSTER_HOME=.dagster uv run dg launch --assets "silver/sec/form_10k_sections" --partition "2024"

# Materialize gold assets (business-ready)
DAGSTER_HOME=.dagster uv run dg launch --assets "gold/economic/labor_market/unemployment" --partition "USA"
DAGSTER_HOME=.dagster uv run dg launch --assets "gold/economic/growth/gdp_real" --partition "CHN"
DAGSTER_HOME=.dagster uv run dg launch --assets "gold/companies/financials/annual_reports"  # Unpartitioned

# Execute jobs (use dg launch --job)
DAGSTER_HOME=.dagster uv run dg launch --job "agriculture_full_pipeline"
DAGSTER_HOME=.dagster uv run dg launch --job "nasa_power_raw_refresh"

# Schedules
dg schedule list                                     # List all schedules
dg schedule start weekly_nasa_power_refresh          # Enable NASA POWER schedule

# Validation
dg check defs

# Testing
uv run pytest

# Linting & Formatting
uv run ruff check src/                 # Check for lint errors
uv run ruff check --fix src/           # Auto-fix lint errors
uv run ruff format src/                # Format code
uv run pre-commit run --all-files      # Run all hooks
```

## Adding Data

### New Company (SEC)

SEC assets are time-partitioned, not company-partitioned. To add a new company:

1. Update `silver/sec/company_registry` configuration to include the new ticker/CIK
2. Re-materialize the time partitions to include the new company's filings:
   ```bash
   DAGSTER_HOME=.dagster uv run dg launch --assets "bronze/sec/form_10k_text" --partition "2024"
   ```

### New Country (World Bank/Economic)

1. Update `partitions.py`: Add 3-letter code to `WORLDBANK_COUNTRIES` and `semantic_countries`
2. Update `reference.py`: Add to crosswalk if needed
3. Materialize: `dg asset materialize --select "bronze/world_bank/timeseries" --partition "NEW_COUNTRY"`

### New Series (FRED/BLS)

Since FRED/BLS are unpartitioned, adding a new series requires:
1. Update the asset code to include the new series ID
2. Rematerialize: `dg asset materialize --select "bronze/fred/all_series"`

### New Data Source

1. `resources.py`: Create `NewApiResource(ConfigurableResource)`
2. `partitions.py`: Define partition if needed (prefer unpartitioned for small datasets)
3. `assets/new_source.py`: Create bronze asset with `key_prefix=['bronze', 'new_source']`
4. `definitions.py`: Register asset + resource
5. `.env`: Add `NEW_API_KEY=...`

### Adding Transformation Layers

**Bronze → Silver:**
1. Create silver asset in `assets/` directory
2. Use `key_prefix=['silver', 'domain']`
3. Use same partition definition as bronze (direct dependency)
4. Accept bronze data as function parameter

**Silver → Gold:**
1. Create gold asset in `assets/` directory
2. Use `key_prefix=['gold', 'domain', 'subdomain']`
3. Use same partition definition as silver (direct dependency)
4. Add `metadata={'layer': 'gold', 'visibility': 'llm_accessible'}`
5. Accept silver data as function parameter

## File Structure

```
src/pipelines/
├── definitions.py          # Entry point
├── resources.py            # API resources (11 data sources)
├── io_managers.py          # FileSystemIOManager (pandas, polars, sharded)
├── partitions.py           # ALL partition definitions + mappings
├── jobs.py                 # Job definitions (26 jobs)
├── schedules.py            # Schedule definitions (21 schedules)
├── sensors.py              # Sensor definitions (7 sensors)
├── checks.py               # Asset checks and validations
├── assets/
│   ├── federal_reserve.py  # FRED series_registry, series
│   ├── bls/                # BLS API + bulk downloads (Polars LazyFrames)
│   │   ├── api.py          # all_series (API)
│   │   ├── bulk_downloads.py  # cpi, labor_force, employment, jolts
│   │   └── common.py       # Shared BLS parsing utilities
│   ├── bea/                # BEA NIPA (Polars LazyFrames)
│   │   └── nipa.py         # nipa_bulk, nipa_current, nipa_data
│   ├── ecb/                # ECB exchange rates
│   │   └── exchange_rates.py
│   ├── usda/               # USDA PSD data
│   │   ├── psd_data.py     # psd_bulk, psd_current, psd_data
│   │   └── registry.py     # commodities, countries
│   ├── world_bank.py       # timeseries (country-partitioned)
│   ├── sec/                # SEC filings (time-partitioned + bulk)
│   │   ├── bulk_downloads.py  # company_facts (sharded), submissions
│   │   ├── fsds.py         # FSDS (67 quarters since 2009)
│   │   ├── form_10k.py     # 10-K annual reports
│   │   ├── form_10q.py     # 10-Q quarterly reports
│   │   ├── form_4.py       # Form 4 insider trading
│   │   ├── form_13f.py     # 13-F institutional holdings
│   │   ├── financials.py   # Extracted financials from bulk
│   │   ├── registry.py     # company/institution registries
│   │   └── taxonomy.py     # XBRL taxonomy
│   ├── patents.py          # PatentsView bulk (sharded)
│   ├── noaa.py             # NOAA weather stations
│   ├── nasa_power.py       # NASA POWER agricultural weather
│   ├── reference.py        # Crosswalks and lookups
│   ├── economic.py         # Gold economic indicators
│   ├── climate.py          # Gold climate indicators
│   └── agriculture.py      # Gold agriculture indicators
└── utils/
    ├── metadata.py         # MetadataBuilder
    └── formatters.py       # FinancialFormatter
```

## Country Codes

- **Consistent 3-letter codes throughout**: 'USA', 'CHN', 'JPN', 'DEU', 'GBR', 'FRA', 'KOR', 'ITA', 'GRC', 'EUU', 'CAN', 'IND', 'BRA', 'AUS', 'MEX', 'ESP', 'NLD', 'RUS', 'SAU', 'TUR'
- Bronze (World Bank) and Gold (economic indicators) layers use identical 3-letter codes
- No 2-letter codes or multi-dimensional partitions
- **Partition definitions**: `worldbank_country_partitions` and `semantic_countries` use the same 3-letter codes
- **Mapping**: `WORLDBANK_COUNTRIES` in `partitions.py` defines the complete list

## Data Sources

| Source | Auth | Partition Type |
|--------|------|----------------|
| FRED | API Key | None (unpartitioned) |
| BLS | API Key | None (unpartitioned) |
| World Bank | None | Single (country, 3-letter) |
| BEA | API Key | None (unpartitioned) |
| ECB | None | None (unpartitioned) |
| USDA FAS | API Key | None (unpartitioned) |
| SEC EDGAR | Identity | Time-based (yearly/quarterly/monthly) |
| PatentsView | None | None (unpartitioned) |
| NASA POWER | None | Single (agricultural location) |
| NOAA | API Token | Dynamic (station ID) |

## Discovery

1. **Asset inventory**: See `docs/generated/DATA_INVENTORY.md` (auto-generated, always current)
2. **Schedules/jobs**: See `docs/generated/SCHEDULES.md` (auto-generated)
3. **Lineage**: See `docs/generated/LINEAGE.md` (auto-generated)
4. **Partitions**: Check `partitions.py` for definitions and mappings
5. **Current patterns**: Read `src/pipelines/assets/*.py`
6. **Resources**: Check `definitions.py`
7. **UI**: http://localhost:3000
8. **Exploration**: Use Task tool with `subagent_type='Explore'`
