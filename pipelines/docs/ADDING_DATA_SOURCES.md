# Adding Data Sources

This tutorial walks you through adding new data to the actBI pipeline, from adding a single series to an existing source all the way to integrating a completely new API.

## Table of Contents

1. [Adding to Existing Sources](#adding-to-existing-sources)
2. [Adding a New Data Source](#adding-a-new-data-source)
3. [Common Patterns](#common-patterns)
4. [Testing Your Work](#testing-your-work)

---

## Adding to Existing Sources

### Adding a FRED Series

**Example:** Add Industrial Production Index (`INDPRO`)

**Step 1:** Edit the FRED asset

Edit `src/pipelines/assets/fred.py` and add the new series ID to the list:
```python
@dg.asset(
    key_prefix=['bronze', 'fred'],
    name='all_series',
    group_name='fred',
)
def all_series(
    context: dg.AssetExecutionContext,
    fred_api: FredApiResource,
) -> pd.DataFrame:
    """Fetch all FRED series in a single asset."""
    series_ids = [
        'GDP', 'UNRATE', 'CPIAUCSL', 'PCE', 'FEDFUNDS',
        'INDPRO',  # ← Add new series ID here
    ]
    # ... rest of implementation
```

**Step 2:** Add to crosswalk (if creating published asset)

Edit `src/pipelines/assets/reference.py`:
```python
data = [
    #... existing entries
    ('fred', 'INDPRO', 'industrial_production', 'Industrial Production Index'),
]
```

**Step 3:** Materialize

```bash
# FRED is unpartitioned, so materialize the entire asset
uv run dg asset materialize --select "bronze/fred/all_series"
```

**Step 4:** Create published asset (optional)

Edit `src/pipelines/assets/economic.py`:
```python
@dg.asset(
    name='industrial_production',
    key_prefix=['gold', 'economic', 'production'],
    partitions_def=semantic_countries,  # Only USA will have data
    ins={
        'bronze_fred_all_series': dg.AssetIn(
            key=dg.AssetKey(['bronze', 'fred', 'all_series']),
        ),
    },
    metadata={'layer': 'gold', 'visibility': 'llm_accessible'},
    group_name='country_indicators',
)
def industrial_production(
    context: dg.AssetExecutionContext,
    bronze_fred_all_series: pd.DataFrame,
    silver_reference_indicator_crosswalk: pd.DataFrame,
) -> pd.DataFrame:
    """Industrial Production Index by country."""
    country = context.partition_key

    if country == 'USA':
        return (
            bronze_fred_all_series
            .query("series_id == 'INDPRO'")
            .drop(columns=['series_id'])
        )
    else:
        # No data for other countries yet
        return pd.DataFrame()
```

**Done!** That's it for adding a new FRED series.

### Adding a World Bank Country

**Example:** Add India (`IND`)

**Step 1:** Add to partition definitions

Edit `src/pipelines/partitions.py`:
```python
WORLDBANK_COUNTRIES = [
    'USA', 'CHN', 'JPN', ...,
    'IND',  # ← Add 3-letter code
]

worldbank_country_partitions = dg.StaticPartitionsDefinition(WORLDBANK_COUNTRIES)

semantic_countries = dg.StaticPartitionsDefinition([
    'USA', 'CHN', 'JPN', ...,
    'IND',  # ← Add same 3-letter code for gold layer
])
```

**Step 2:** Add to crosswalk (optional)

Edit `src/pipelines/assets/reference.py` to add India indicator mappings if needed.

**Step 3:** Materialize

```bash
# Materialize bronze layer - single partition for all indicators
uv run dg asset materialize --select "bronze/world_bank/timeseries" --partition "IND"
```

**Step 4:** Materialize published assets

```bash
uv run dg asset materialize --select "gold/economic/growth/gdp" --partition "IND"
uv run dg asset materialize --select "gold/economic/labor_market/unemployment" --partition "IND"
```

**Done!** India data is now available.

### Adding a SEC Company

**Step 1:** Add to partition definitions

Edit `src/pipelines/partitions.py`:
```python
company_partitions = dg.StaticPartitionsDefinition([
    'AAPL', 'MSFT', 'SBUX', 'MCD',
    'NFLX',  # ← Add ticker
])

TICKER_TO_CIK = {
    'AAPL': '0000320193',
    'MSFT': '0000789019',
    'SBUX': '0000829224',
    'MCD': '0000063908',
    'NFLX': '0001065280',  # ← Add ticker-to-CIK mapping
}

CIK_TO_TICKER = {v: k for k, v in TICKER_TO_CIK.items()}
```

**Step 2:** Materialize

```bash
# Check definitions loaded correctly
uv run dg check defs

# Materialize bronze layer (raw filings for all years)
uv run dg asset materialize --select "bronze/sec/form_10k" --partition "NFLX"

# Materialize silver layer (parsed financials)
uv run dg asset materialize --select "silver/sec/form_10k_financials" --partition "NFLX"

# Materialize gold layer (published)
uv run dg asset materialize --select "gold/companies/financials/annual_report" --partition "NFLX"
```

**Done!** Netflix 10-K data is available.

---

## Adding a New Data Source

Let's walk through adding a completely new data source. We'll use **commodity prices** as an example.

### Step 1: Create a Resource

Create `CommodityApiResource` in `src/pipelines/resources.py`:

```python
class CommodityApiResource(dg.ConfigurableResource):
    """Resource for commodity price API."""
    api_key: str

    def get_price_history(self, commodity: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch historical prices for a commodity."""
        # Your API client logic here
        response = requests.get(
            f'https://api.commodities.com/prices/{commodity}',
            params={'start': start_date, 'end': end_date},
            headers={'Authorization': f'Bearer {self.api_key}'}
        )
        response.raise_for_status()

        data = response.json()
        return pd.DataFrame(data['prices'])
```

### Step 2: Define Partitions

Add to `src/pipelines/partitions.py`:

```python
commodity_partitions = dg.StaticPartitionsDefinition([
    'coffee_arabica',
    'coffee_robusta',
    'crude_oil',
    'natural_gas',
    'gold',
])
```

### Step 3: Create Bronze Asset

Create `src/pipelines/assets/commodities.py`:

```python
import dagster as dg
import pandas as pd
from pipelines.partitions import commodity_partitions
from pipelines.resources import CommodityApiResource

@dg.asset(
    key_prefix=['bronze', 'commodities'],
    name='prices',
    partitions_def=commodity_partitions,
    group_name='commodities',
    metadata={
        'layer': 'bronze',
        'source': 'commodity_api',
    },
)
def prices(
    context: dg.AssetExecutionContext,
    commodity_api: CommodityApiResource
) -> pd.DataFrame:
    """Fetch raw commodity prices from API."""
    commodity = context.partition_key

    context.log.info(f'Fetching {commodity} prices...')

    df = commodity_api.get_price_history(
        commodity=commodity,
        start_date='2020-01-01',
        end_date='2025-12-31'
    )

    context.add_output_metadata({
        'num_records': len(df),
        'commodity': commodity,
        'date_range_start': str(df['date'].min()),
        'date_range_end': str(df['date'].max()),
    })

    context.log.info(f'{commodity} fetch complete')

    return df
```

### Step 4: Create Gold Asset

Add to same file:

```python
@dg.asset(
    key_prefix=['gold', 'commodities'],
    name='current_prices',
    partitions_def=commodity_partitions,
    group_name='commodities',
    metadata={
        'layer': 'gold',
        'visibility': 'llm_accessible',
        'questions_answered': [
            'What is the current {commodity} price?',
            'How has {commodity} price changed?',
        ],
    },
)
def current_prices(
    context: dg.AssetExecutionContext,
    bronze_commodities_prices: pd.DataFrame,  # Direct dependency - same partition
) -> pd.DataFrame:
    """Published commodity prices with recent trends."""
    commodity = context.partition_key

    # Transform: add rolling averages, percent changes
    df = (
        bronze_commodities_prices
        .sort_values('date')
        .assign(
            price_7d_avg=lambda x: x['price'].rolling(7).mean(),
            price_30d_avg=lambda x: x['price'].rolling(30).mean(),
            pct_change_1d=lambda x: x['price'].pct_change(),
        )
    )

    return df
```

### Step 5: Register Resource

Edit `src/pipelines/definitions.py`:

```python
from pipelines.assets import commodities  # ← Import new module
from pipelines.resources import CommodityApiResource  # ← Import resource

all_assets = [
    # ... existing assets
    *dg.load_assets_from_modules([commodities], group_name='commodities'),
]

defs = dg.Definitions(
    assets=all_assets,
    resources={
        # ... existing resources
        'commodity_api': CommodityApiResource(api_key=dg.EnvVar('COMMODITY_API_KEY')),
    }
)
```

### Step 6: Add Environment Variable

Edit `.env`:
```bash
COMMODITY_API_KEY=your_api_key_here
```

### Step 7: Test

```bash
# Validate definitions
uv run dg check defs

# Materialize bronze layer
uv run dg asset materialize --select "bronze/commodities/prices" --partition "coffee_arabica"

# Materialize gold layer
uv run dg asset materialize --select "gold/commodities/current_prices" --partition "coffee_arabica"
```

### Step 8: Add Tests

Create `tests/test_assets/test_commodities.py`:

```python
import pytest
import pandas as pd
from pipelines.assets.commodities import current_prices

class TestCommodityAssets:
    def test_current_prices_adds_rolling_averages(self):
        """Test that gold asset calculates rolling averages."""
        # Arrange
        raw_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=30),
            'price': range(100, 130)
        })

        # Act
        # (This would need mocking context.load_asset_value)

        # Assert
        # assert '7d_avg' in result.columns
        pass  # Full implementation left as exercise
```

### Step 9: Add Schedule (Optional)

Edit `src/pipelines/schedules.py`:

```python
weekly_commodity_schedule = dg.ScheduleDefinition(
    name="weekly_commodity_refresh",
    cron_schedule="0 6 * * 1",  # Monday 6 AM
    target=dg.AssetSelection.groups("commodities"),
    execution_timezone="US/Eastern",
    description="Refresh commodity prices every Monday",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)

ALL_SCHEDULES = [
    # ... existing schedules
    weekly_commodity_schedule,
]
```

**Done!** You've added a complete new data source.

---

## Common Patterns

### Pattern 1: Bronze → Gold

For data that doesn't need intermediate transforms:

```python
# Bronze asset (raw data)
@dg.asset(
    key_prefix=['bronze', 'source'],
    name='data',
    metadata={'layer': 'bronze'}
)
def data(api_resource): ...

# Gold asset (published, depends on bronze via direct dependency)
@dg.asset(
    key_prefix=['gold', 'domain'],
    name='published_data',
    metadata={'layer': 'gold', 'visibility': 'llm_accessible'}
)
def published_data(bronze_source_data: pd.DataFrame):
    """Transform bronze data for publication."""
    return transform(bronze_source_data)
```

### Pattern 2: Bronze → Silver → Gold

For data needing validation/enrichment:

```python
# Bronze (raw data)
@dg.asset(
    key_prefix=['bronze', 'source'],
    metadata={'layer': 'bronze'}
)
def raw_data(): ...

# Silver (validates, enriches)
@dg.asset(
    key_prefix=['silver', 'source'],
    metadata={'layer': 'silver'}
)
def cleaned_data(raw_data: pd.DataFrame):
    return validate_and_clean(raw_data)

# Gold (published)
@dg.asset(
    key_prefix=['gold', 'domain'],
    metadata={'layer': 'gold', 'visibility': 'llm_accessible'}
)
def published_data(cleaned_data: pd.DataFrame):
    return prepare_for_llm(cleaned_data)
```

### Pattern 3: Semantic Routing with Direct Dependencies

For assets that intelligently route between sources using direct dependencies:

```python
@dg.asset(
    key_prefix=['gold', 'economic', 'labor_market'],
    name='unemployment',
    partitions_def=semantic_countries,
    ins={
        'bronze_fred_all_series': dg.AssetIn(
            key=dg.AssetKey(['bronze', 'fred', 'all_series']),
        ),
    },
    metadata={'layer': 'gold', 'visibility': 'llm_accessible'},
    group_name='country_indicators',
)
def unemployment(
    context: dg.AssetExecutionContext,
    bronze_fred_all_series: pd.DataFrame,  # Unpartitioned source
    bronze_world_bank_timeseries: pd.DataFrame,  # Country-partitioned source
) -> pd.DataFrame:
    """Unemployment rate by country - routes between sources."""
    country = context.partition_key

    if country == 'USA':
        # Filter FRED data for US unemployment
        return (
            bronze_fred_all_series
            .query("series_id == 'UNRATE'")
            .drop(columns=['series_id'])
        )
    else:
        # World Bank data already filtered by partition
        return (
            bronze_world_bank_timeseries
            .query("indicator == 'SL.UEM.TOTL.ZS'")
            .drop(columns=['indicator'])
        )
```

---

## Testing Your Work

### 1. Validate Definitions

```bash
uv run dg check defs
```

This catches:
- Syntax errors
- Missing dependencies
- Invalid partition definitions
- Resource configuration issues

### 2. Test One Partition

```bash
uv run dg asset materialize --select "your/asset" --partition "test_partition"
```

Verify:
- API call succeeds
- Data transforms correctly
- Metadata is recorded
- File is saved

### 3. Check in UI

1. Start Dagster: `uv run dg dev`
2. Navigate to Assets tab
3. Find your asset
4. Verify metadata looks correct
5. Check dependencies are shown correctly

### 4. Write Unit Tests

See [TESTING.md](TESTING.md) for patterns.

### 5. Test Downstream Dependencies

```bash
# Materialize bronze
uv run dg asset materialize --select "bronze/source/data" --partition "X"

# Materialize gold (should use bronze data)
uv run dg asset materialize --select "gold/domain/data" --partition "X"
```

### 6. Test Schedule (Optional)

```bash
# Enable schedule
uv run dg schedule start your_schedule_name

# Trigger manually
uv run dg schedule run your_schedule_name
```

---

## Troubleshooting

### "Asset not found"

- Check you imported the module in `definitions.py`
- Verify asset key matches what you're trying to materialize
- Run `uv run dg check defs` to validate

### "Partition not found"

- Check partition is in partition definition
- Verify partition key format (single-dimension partitions use simple strings like "USA", "AAPL")

### "Resource not available"

- Check resource is registered in `definitions.py`
- Verify environment variable is set in `.env`
- Check resource name matches parameter name in asset function

### "API call fails"

- Verify API key is correct
- Check rate limits
- Add logging to see request/response
- Test API call outside Dagster first

---

## Next Steps

- [Test your assets](TESTING.md)
- [Schedule automated refreshes](OPERATIONS.md)
- [Query your data](ANALYSIS.md)

Happy data engineering! 🚀
