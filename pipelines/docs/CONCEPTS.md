# Core Concepts

This guide explains the fundamental building blocks of the actBI data pipeline. By the end, you'll understand how assets, partitions, resources, and the DAG work together to create a reliable, scalable data platform.

## Table of Contents

1. [Assets](#assets)
2. [Partitions](#partitions)
3. [Resources](#resources)
4. [The DAG](#the-dag)
5. [Asset Types](#asset-types)
6. [Partition Strategies](#partition-strategies)
7. [Why This Matters](#why-this-matters)

---

## Assets

### What is an Asset?

An **asset** is a dataset produced by the pipeline. Think of it as a table, a file, or any collection of data that you want to track and manage.

**Examples from our pipeline:**
- `bronze/fred/all_series` - Unpartitioned asset with all FRED time series
- `bronze/world_bank/timeseries` - World Bank data partitioned by country
- `gold/economic/growth/gdp` - Published GDP data ready for analysis
- `silver/reference/indicator_crosswalk` - Mapping between semantic names and source IDs

### Why Use Assets?

Traditional ETL scripts are opaque—you run a script, it does something, and hopefully produces the right output. With assets:

- **Visibility** - You can see what data exists and what doesn't
- **Dependencies** - Dagster tracks which assets depend on which
- **Selective Refresh** - Materialize only what you need, when you need it
- **Metadata** - Every asset tracks when it was created, how many records, date ranges, etc.

### Assets in Code

Assets are defined with the `@dg.asset` decorator:

```python
import dagster as dg
import pandas as pd

@dg.asset(
    key_prefix=['bronze', 'world_bank'],
    name='timeseries',
    partitions_def=worldbank_country_partitions,
)
def worldbank_timeseries(
    context: dg.AssetExecutionContext,
    world_bank_api: WorldBankApiResource
) -> pd.DataFrame:
    """Fetch all indicators for a single country from World Bank API."""
    country = context.partition_key  # Which country to fetch: 'USA', 'CHN', etc.

    all_data = []
    for indicator in WORLDBANK_INDICATORS:
        data = world_bank_api.get_indicator(indicator, [country])
        data['indicator'] = indicator
        all_data.append(data)

    df = pd.concat(all_data, ignore_index=True)

    context.add_output_metadata({
        'num_records': len(df),
        'country': country,
        'indicators_fetched': len(WORLDBANK_INDICATORS),
    })

    return df
```

**Key points:**
- **key_prefix + name** creates the asset key: `bronze/world_bank/timeseries`
- **partitions_def** divides the asset into independent slices (one per country)
- **Function parameters** define dependencies (e.g., `world_bank_api` resource)
- **Return value** is the data to save
- **Metadata** tracks important information about the asset

---

## Partitions

### What is a Partition?

A **partition** is a logical slice of an asset. Instead of one giant table with all data, you divide it into independent pieces.

**Think of it like this:**
- **Without partitions:** One file containing GDP data for all countries
- **With partitions:** Separate files for each country (US, China, Japan, etc.)

### When to Use Partitions

Use partitions when you have **logically similar data with the same structure**:

✅ **Good use cases:**
- Time series for different economic indicators (GDP, unemployment, inflation)
- Data for different countries (US, China, Japan, Germany...)
- Company filings for different fiscal years (FY2020, FY2021, FY2022...)

❌ **Bad use cases:**
- Fundamentally different data structures
- Data that needs to be analyzed together as one unit
- Only one or two instances

### Benefits of Partitions

1. **Independent materialization** - Update US data without re-fetching China data
2. **Scalability** - Add new countries by updating the partition list, not creating new assets
3. **Parallel processing** - Dagster can materialize partitions concurrently
4. **Clear organization** - Each partition is a separate file on disk

### Example: World Bank Country Data

Instead of creating separate assets for each country:

```python
# DON'T DO THIS ❌
@dg.asset
def usa_indicators(): ...

@dg.asset
def china_indicators(): ...

@dg.asset
def japan_indicators(): ...
# ... 20+ more assets
```

Use partitions:

```python
# DO THIS ✅
from pipelines.partitions import worldbank_country_partitions

@dg.asset(
    key_prefix=['bronze', 'world_bank'],
    name='timeseries',
    partitions_def=worldbank_country_partitions,  # ['USA', 'CHN', 'JPN', ...]
)
def worldbank_timeseries(context):
    country = context.partition_key  # 'USA', 'CHN', etc.
    # Fetch all indicators for this country
```

**Result:** One asset definition handles all countries.

### Partition Keys

A **partition key** identifies which slice of data you're working with. In this pipeline, we use **simple string partition keys**:

- Country: `"USA"`, `"CHN"`, `"JPN"`
- Company ticker: `"AAPL"`, `"MSFT"`, `"SBUX"`
- Institution CIK: `"0001067983"`, `"0001364742"`

When materializing:

```bash
# All partitions
uv run dg asset materialize --select "bronze/world_bank/timeseries"

# One partition
uv run dg asset materialize --select "bronze/world_bank/timeseries" --partition "USA"
```

---

## Resources

### What is a Resource?

A **resource** is a reusable connection to an external service—typically an API client.

**Examples:**
- `fred_api` - FRED API client (with your API key)
- `world_bank_api` - World Bank API client
- `sec_edgar` - SEC EDGAR filing client
- `duckdb` - DuckDB database connection

### Why Use Resources?

Without resources, each asset would need to:
- Manage its own API credentials
- Create its own HTTP clients
- Duplicate connection logic

With resources:
- **Single source of configuration** - API key defined once
- **Easy testing** - Swap real API with a mock
- **Dependency injection** - Dagster provides the resource automatically

### Resources in Code

Define a resource:

```python
from dagster import ConfigurableResource

class FredApiResource(ConfigurableResource):
    api_key: str  # Configuration from environment

    def get_series(self, series_id: str):
        """Fetch a series from FRED."""
        client = Fred(api_key=self.api_key)
        return client.get_series(series_id)
```

Register it in `definitions.py`:

```python
import dagster as dg

defs = dg.Definitions(
    assets=[...],
    resources={
        'fred_api': FredApiResource(api_key=dg.EnvVar('FRED_API_KEY')),
    }
)
```

Use it in an asset:

```python
@dg.asset
def gdp_data(context, fred_api: FredApiResource):  # ← Injected automatically
    data = fred_api.get_series('GDP')
    return pd.DataFrame(data)
```

**Magic:** Dagster sees the `fred_api` parameter, looks it up in the resources dictionary, and injects it automatically.

---

## The DAG

### What is a DAG?

**DAG stands for Directed Acyclic Graph**—a fancy term for "a flowchart without loops."

In our pipeline, the DAG shows how data flows from sources → transforms → published outputs.

### Example DAG

```
bronze/fred/all_series (unpartitioned, includes US unemployment)
    ↓
gold/economic/labor_market/unemployment[USA]

bronze/world_bank/timeseries[CHN] (includes unemployment indicator)
    ↓
gold/economic/labor_market/unemployment[CHN]
```

**This means:**
- `gold/economic/labor_market/unemployment` uses different sources per country
- FRED data is unpartitioned (all series in one asset), gold layer filters at runtime
- World Bank data is partitioned by country, same partition flows through to gold
- If you materialize raw data, the published asset becomes "stale"
- You can rematerialize the gold asset to refresh it with new upstream data

### Defining Dependencies

Dependencies are inferred from function parameters:

```python
@dg.asset
def raw_data(fred_api: FredApiResource):
    # No dependencies (besides the resource)
    return fetch_from_api()

@dg.asset
def cleaned_data(raw_data: pd.DataFrame):  # ← Depends on raw_data
    return raw_data.dropna()

@dg.asset
def summary(cleaned_data: pd.DataFrame):  # ← Depends on cleaned_data
    return cleaned_data.describe()
```

**The DAG:**
```
raw_data → cleaned_data → summary
```

### Why DAGs Matter

1. **Automatic tracking** - Dagster knows what needs to refresh when upstream data changes
2. **Selective materialization** - Only run what you need
3. **Clear lineage** - See where your data comes from
4. **Debugging** - Trace issues back to the source

---

## Asset Types

We organize assets into three conceptual types based on their role in the DAG:

### 1. Source Nodes (Bronze Layer)

**Definition:** Raw data from external APIs with no upstream dependencies.

**Characteristics:**
- Unpartitioned (for small datasets like FRED, BLS) or partitioned by simple dimensions (country, ticker)
- Minimal transformation (just fetch and save)
- Marked as internal/not LLM-accessible

**Examples:**
- `bronze/fred/all_series` - Unpartitioned asset with all 5 FRED series
- `bronze/world_bank/timeseries[USA]` - All World Bank indicators for USA
- `bronze/sec/form_10k[AAPL]` - All 10-K filings for Apple

**Storage:**
- Unpartitioned: `_data/assets/bronze/fred/all_series/data.parquet`
- Partitioned: `_data/assets/bronze/world_bank/timeseries/partition=USA/data.parquet`

### 2. Intermediate Nodes (Silver Layer)

**Definition:** Transformed, cleaned, or enriched data that feeds into published assets.

**Characteristics:**
- Depends on source nodes
- Performs validation, parsing, or calculation
- Still marked as internal

**Examples:**
- `silver/sec/form_10k_financials[AAPL]` - Extracted financial metrics from raw 10-K
- `silver/reference/indicator_crosswalk` - Unpartitioned mapping between semantic names and source IDs
- `silver/reference/company_registry` - Unpartitioned registry of all companies

**Note:** Not all pipelines need intermediate nodes! Economic indicators often go directly from bronze → gold.

### 3. Leaf Nodes (Gold Layer - Published Assets)

**Definition:** LLM-ready, user-facing data optimized for analysis.

**Characteristics:**
- Partitioned by semantic IDs (3-letter country codes, tickers)
- Pre-aggregated and narrative-ready
- Includes `questions_answered` metadata for LLM discovery
- Marked as `llm_accessible`

**Examples:**
- `gold/economic/labor_market/unemployment[USA]` - US unemployment rate
- `gold/economic/labor_market/unemployment[CHN]` - China unemployment rate
- `gold/companies/financials/annual_report[AAPL]` - Apple's annual report (all years)

**Storage:** `_data/assets/gold/economic/labor_market/unemployment/partition=USA/data.parquet`

### The Flow

```
Bronze Layer              Silver Layer              Gold Layer
    ↓                          ↓                        ↓
Raw data             → Cleaned/parsed data   →  Published data
Unpartitioned or        Same partitions or      Semantic partitions
simple partitions       unpartitioned refs      (country, ticker)
Internal only           Internal only            LLM-accessible
```

**Flexibility:** The number of silver nodes varies. Simple data might need none. Complex data might need several.

**Partition flow:** Use the same partition definition from bronze → silver → gold for direct dependencies.

---

## Partition Strategies

This pipeline uses a **simplified single-dimension partition architecture** to avoid complexity and maintain clean provenance tracking.

### Three Partition Strategies

#### 1. Unpartitioned Assets (Small, Stable Datasets)

**When to use:** Data with few items (< 10) that all refresh together

**Examples:**
- `bronze/fred/all_series` - 5 FRED series in one asset
- `bronze/bls/all_series` - 6 BLS series in one asset
- `silver/reference/indicator_crosswalk` - Unpartitioned reference table

**Benefits:**
- Simple to maintain
- No partition explosion
- All data refreshes atomically

```python
@dg.asset(key_prefix=['bronze', 'fred'], name='all_series')
def all_series(context, fred_api: FredApiResource) -> pd.DataFrame:
    """Fetch all FRED series in one asset."""
    series_ids = ['GDP', 'UNRATE', 'CPIAUCSL', 'PCE', 'FEDFUNDS']

    all_data = []
    for series_id in series_ids:
        data = fred_api.get_series(series_id)
        df = pd.DataFrame({'date': data.index, 'value': data.values, 'series_id': series_id})
        all_data.append(df)

    return pd.concat(all_data, ignore_index=True)
```

#### 2. Single-Dimension Partitions (Many Similar Items)

**When to use:** Logically similar data with the same structure (countries, companies, etc.)

**Examples:**
- `bronze/world_bank/timeseries` - Partitioned by country (20 partitions)
- `bronze/sec/form_10k` - Partitioned by ticker (4 companies)
- `gold/economic/labor_market/unemployment` - Partitioned by country

**Benefits:**
- Independent materialization per partition
- Parallel processing
- Clear provenance (same partition flows bronze → silver → gold)

```python
@dg.asset(
    key_prefix=['bronze', 'world_bank'],
    name='timeseries',
    partitions_def=worldbank_country_partitions,  # ['USA', 'CHN', 'JPN', ...]
)
def worldbank_timeseries(context, world_bank_api: WorldBankApiResource) -> pd.DataFrame:
    """Fetch all indicators for one country."""
    country = context.partition_key  # Simple string: 'USA'

    # Fetch all 8 indicators for this country
    all_data = []
    for indicator in WORLDBANK_INDICATORS:
        df = world_bank_api.get_indicator(indicator, [country])
        df['indicator'] = indicator
        all_data.append(df)

    return pd.concat(all_data, ignore_index=True)
```

**Storage:** `_data/assets/bronze/world_bank/timeseries/partition=USA/data.parquet`

#### 3. Runtime Filtering (Mixing Unpartitioned and Partitioned)

**When to use:** Gold layer needs to combine unpartitioned upstream data with partitioned data

**Pattern:** Accept unpartitioned data via function parameter, filter at runtime

```python
@dg.asset(
    key_prefix=['gold', 'economic', 'labor_market'],
    name='unemployment',
    partitions_def=semantic_countries,  # ['USA', 'CHN', 'JPN', ...]
    ins={
        'bronze_fred_all_series': dg.AssetIn(
            key=dg.AssetKey(['bronze', 'fred', 'all_series']),
        ),
    },
)
def unemployment(
    context,
    bronze_fred_all_series: pd.DataFrame,      # Unpartitioned - all series
    bronze_world_bank_timeseries: pd.DataFrame,  # Already filtered by partition
) -> pd.DataFrame:
    """Unemployment rate by country."""
    country = context.partition_key

    if country == 'USA':
        # Filter FRED data at runtime
        return bronze_fred_all_series.query("series_id == 'UNRATE'")
    else:
        # World Bank data already filtered to this country
        return bronze_world_bank_timeseries.query("indicator == 'SL.UEM.TOTL.ZS'")
```

### Why Single-Dimension Only?

We deliberately avoid multi-dimensional partitions (e.g., `country|indicator`) because:

❌ **Partition explosion:** 20 countries × 8 indicators = 160 partitions
❌ **Complex mappings:** Requires AllPartitionMapping for dependencies
❌ **Provenance tracking:** Harder to track lineage across dimensions
❌ **Runtime overhead:** Loading all combinations to filter is expensive

✅ **Instead:** Fetch all indicators for one country in a single partition

### Design Rule

**"Partition by the outer dimension, loop over the inner dimension"**

- World Bank: Partition by country → fetch all indicators per country
- SEC: Partition by ticker → fetch all years per company
- FRED/BLS: Unpartitioned → fetch all series in one asset

---

## Why This Matters

### For Data Quality

- **Partitions** let you isolate and fix bad data without reprocessing everything
- **The DAG** ensures downstream assets stay in sync with sources
- **Resources** centralize API logic, making it easier to add retry/validation

### For Scalability

- **Partitions** enable parallel processing (materialize multiple countries at once)
- **Asset types** clarify what's internal vs. published, reducing clutter
- **Flexible DAG** adapts to simple and complex transformations without refactoring

### For AI Integration

- **Semantic partitions** (US, CN, JP) match natural language queries
- **Metadata** (`questions_answered`) helps LLMs discover relevant data
- **Published assets** are pre-aggregated, reducing LLM context window usage

### For Developer Experience

- **Explicit dependencies** make the system easy to understand
- **Dagster UI** provides visibility into what exists and what's stale
- **Testing** is easier because each asset is an independent unit

---

## Next Steps

Now that you understand these concepts:

1. **See them in action** - Read [ARCHITECTURE.md](ARCHITECTURE.md) to see how we apply these patterns
2. **Explore data sources** - Check [DATA_SOURCES.md](DATA_SOURCES.md) to see what data we're ingesting
3. **Add your own data** - Follow [ADDING_DATA_SOURCES.md](ADDING_DATA_SOURCES.md) to create your first asset

**Key takeaway:** Assets, partitions, resources, and the DAG work together to create a pipeline that's reliable, scalable, and maintainable. Master these concepts and you'll understand the entire system.
