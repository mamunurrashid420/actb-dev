# Operations

This guide covers running, scheduling, and monitoring the actBI data pipeline in production and development.

## Table of Contents

1. [Running the Pipeline](#running-the-pipeline)
2. [Asset Selection](#asset-selection)
3. [Schedules](#schedules)
4. [Monitoring](#monitoring)
5. [Troubleshooting](#troubleshooting)

---

## Running the Pipeline

### Start Dagster UI

```bash
cd pipelines  # from repository root
uv run dagster dev
```

Open http://localhost:3000

**Custom port:**
```bash
uv run dagster dev --port 3001
```

### Validate Definitions

Before materializing, always validate:

```bash
uv run dagster check defs
```

This catches configuration errors, missing dependencies, and invalid partition definitions.

---

## Asset Selection

### Selection Syntax

Dagster uses a powerful selection syntax for targeting assets:

**All assets:**
```bash
uv run dagster asset materialize --select "*"
```

**By group:**
```bash
uv run dagster asset materialize --select "group:fred"
uv run dagster asset materialize --select "group:country_indicators"
```

**By asset key:**
```bash
uv run dagster asset materialize --select "bronze/fred/all_series"
uv run dagster asset materialize --select "gold/economic/growth/gdp"
```

**With upstream dependencies:**
```bash
# Materialize asset AND everything it depends on
uv run dagster asset materialize --select "+gold/economic/growth/gdp"
```

**With downstream dependents:**
```bash
# Materialize asset AND everything that depends on it
uv run dagster asset materialize --select "bronze/fred/all_series+"
```

**Both:**
```bash
uv run dagster asset materialize --select "+gold/economic/growth/gdp+"
```

### Partition Selection

**All partitions:**
```bash
uv run dagster asset materialize --select "bronze/world_bank/timeseries"
```

**Single partition:**
```bash
uv run dagster asset materialize --select "bronze/world_bank/timeseries" --partition "USA"
uv run dagster asset materialize --select "bronze/sec/form_10k" --partition "AAPL"
```

**Multiple specific partitions:**
```bash
uv run dagster asset materialize --select "bronze/world_bank/timeseries" --partition "USA" --partition "CHN" --partition "JPN"
uv run dagster asset materialize --select "bronze/sec/form_10k" --partition "AAPL" --partition "MSFT"
```

**Unpartitioned assets:**
```bash
# FRED and BLS are unpartitioned - materialize all series at once
uv run dagster asset materialize --select "bronze/fred/all_series"
uv run dagster asset materialize --select "bronze/bls/all_series"
```

### Common Workflows

**Daily refresh of US indicators:**
```bash
uv run dagster asset materialize --select "group:fred"
uv run dagster asset materialize --select "group:bls"
uv run dagster asset materialize --select "group:country_indicators" --partition "USA"
```

**Weekly refresh of all international data:**
```bash
uv run dagster asset materialize --select "group:world_bank"
uv run dagster asset materialize --select "group:country_indicators"
```

**Update specific company's financials:**
```bash
uv run dagster asset materialize --select "bronze/sec/form_10k" --partition "AAPL"
uv run dagster asset materialize --select "gold/companies/financials/annual_report" --partition "AAPL"
```

---

## Schedules

### Available Schedules

The pipeline includes **6 weekly schedules** (all start STOPPED):

| Schedule | Day/Time | Target | Description |
|----------|----------|--------|-------------|
| `weekly_fred_refresh` | Mon 2 AM ET | `group:fred` | FRED economic data |
| `weekly_bls_refresh` | Fri 7 AM ET | `group:bls` | BLS labor market data |
| `weekly_world_bank_refresh` | Sun 2 AM ET | `group:world_bank` | World Bank country indicators |
| `weekly_nasa_power_refresh` | Mon 3 AM ET | NASA POWER raw data | Climate/agriculture data |
| `weekly_combined_indicators` | Mon 4 AM ET | `group:country_indicators` | Published economic indicators |
| `weekly_agriculture_refresh` | Mon 5 AM ET | Agriculture indicators | Published agriculture indicators |

### Managing Schedules

**List all schedules:**
```bash
uv run dagster schedule list
```

Output shows:
- Schedule name
- Status (RUNNING or STOPPED)
- Cron schedule
- Next tick time (if running)

**Start a schedule:**
```bash
uv run dagster schedule start weekly_fred_refresh
```

**Stop a schedule:**
```bash
uv run dagster schedule stop weekly_fred_refresh
```

**Trigger a schedule manually:**
```bash
# Immediately run what the schedule would run
uv run dagster asset materialize --select "group:fred"
```

### Schedule Design

Schedules are timed to run in dependency order:

1. **Source data** (Fri-Sun): FRED, BLS, World Bank refresh raw data
2. **Published indicators** (Mon 4-5 AM): Transform raw → published
3. **Dependencies satisfied**: Published assets run after all sources are fresh

**Why STOPPED by default?**
- Prevents accidental API quota usage
- Let you control when automation starts
- Test manually before enabling schedules

---

## Monitoring

### Dagster UI

**Assets Tab:**
- **Green checkmark** ✅ - Materialized and up-to-date
- **Yellow warning** ⚠ - Stale (upstream changed)
- **Gray circle** ○ - Never materialized
- **Red X** ❌ - Failed last materialization

Click any asset to see:
- Metadata (record counts, date ranges, etc.)
- Lineage (upstream/downstream assets)
- Materializations history
- Partition coverage

**Runs Tab:**
- All materialization attempts (success/fail)
- Logs for each run
- Execution time
- Metadata captured

**Asset Groups:**

Navigate by group to see related assets:
- `fred` - 5 FRED series (unpartitioned)
- `bls` - 6 BLS series (unpartitioned)
- `world_bank` - 20 country partitions × multiple indicators
- `country_indicators` - Published economic indicators (country-partitioned)
- `sec_filings` - SEC company and institution data (company/institution-partitioned)
- `reference` - Crosswalk and registry assets (unpartitioned)

### Logs

**View logs in UI:**
1. Go to Runs tab
2. Click on a run
3. See logs in real-time or after completion

**Log levels:**
- `context.log.info()` - Normal progress updates
- `context.log.warning()` - Data quality issues
- `context.log.error()` - Failures

**What to log:**
- Asset start/end (status updates only)
- Data quality issues (missing values, unexpected formats)
- API errors
- **Not**: Detailed metrics (use metadata instead)

### Metadata Monitoring

Check metadata for anomalies:

**Expected patterns:**
- Record counts should be consistent (GDP usually has ~100 years of data)
- Date ranges should extend to recent dates
- No sudden drops in data volume

**Red flags:**
- Record count drops significantly
- Date range doesn't include recent data
- Missing partitions

---

## Troubleshooting

### Common Issues

#### Issue: "No module named 'pipelines'"

**Cause:** PYTHONPATH not set

**Solution:** Always run from `pipelines/` directory:
```bash
cd pipelines  # from repository root
uv run dagster dev
```

#### Issue: "Asset not found"

**Cause:** Asset key doesn't match what you typed

**Solution:** Check exact asset key in UI or run:
```bash
uv run dagster asset list
```

#### Issue: "Partition not found"

**Cause:** Partition key doesn't exist in partition definition

**Solution:** Check `src/pipelines/partitions.py` for valid partition keys.

All partitions are now **single-dimension strings**:
```bash
--partition "USA"          # Country code (3 letters)
--partition "AAPL"         # Company ticker
--partition "0001067983"   # Institution CIK
```

Valid country codes:
- USA, CHN, JPN, DEU, GBR, FRA, KOR, ITA, GRC, EUU, CAN, IND, BRA, AUS, MEX, ESP, NLD, RUS, SAU, TUR

Valid company tickers (expand as needed):
- AAPL, MSFT, SBUX, MCD

#### Issue: Schedule won't start

**Cause:** Schedule references non-existent asset group or job

**Solution:** Check schedule target in `src/pipelines/schedules.py` matches group names in `definitions.py`.

#### Issue: API rate limit exceeded

**Cause:** Too many requests to external API

**Solutions:**
- **BLS**: 500 queries/day limit. Materialize fewer partitions or spread over multiple days.
- **SEC**: 10 req/sec limit. Our resource has built-in rate limiting, but parallel materializations may trigger it.
- **FRED/World Bank**: No official limits, but be respectful

#### Issue: Assets shown as "stale"

**Cause:** Upstream asset was re-materialized

**Solution:** This is expected! Stale means "upstream data changed, you should refresh me too."

Fix by materializing the stale asset:
```bash
uv run dagster asset materialize --select "stale/asset"
```

#### Issue: Materialization fails with "Missing API key"

**Cause:** Environment variable not set

**Solution:**
1. Check `.env` file has the API key
2. Restart Dagster (it loads `.env` on startup)
3. Verify key is correct

```bash
# .env should contain:
FRED_API_KEY=your_actual_key
BLS_API_KEY=your_actual_key
```

#### Issue: Parquet file not found when loading

**Cause:** Asset hasn't been materialized yet

**Solution:**
```bash
# Materialize first
uv run dagster asset materialize --select "bronze/fred/all_series"

# Then load
from load_assets import load_asset
data = load_asset('bronze/fred/all_series')
```

### Debugging Workflow

1. **Check definitions:**
   ```bash
   uv run dagster check defs
   ```

2. **Test one partition:**
   ```bash
   uv run dagster asset materialize --select "bronze/world_bank/timeseries" --partition "USA"
   ```

3. **Check logs in UI** - Look for warnings or errors

4. **Verify upstream data exists** - If asset depends on others, make sure they're materialized

5. **Check metadata** - Does record count make sense? Date range correct?

6. **Test API directly** - Use Python console to test API call outside Dagster

---

## Advanced Topics

### DuckDB Queries

Query materialized assets with SQL:

```python
import duckdb

# Query unpartitioned asset
result = duckdb.sql('''
    SELECT *
    FROM '_data/assets/bronze/fred/all_series/data.parquet'
    WHERE date >= '2020-01-01'
''').to_df()

# Query across all partitions
result = duckdb.sql('''
    SELECT *
    FROM '_data/assets/bronze/world_bank/timeseries/**/data.parquet'
    WHERE date >= '2020-01-01'
''').to_df()

# Query specific partition
result = duckdb.sql('''
    SELECT *
    FROM '_data/assets/bronze/world_bank/timeseries/partition=USA/data.parquet'
''').to_df()
```

See [ANALYSIS.md](ANALYSIS.md) for more examples.

### Custom Asset Groups

To create logical groupings:

Edit `src/pipelines/definitions.py`:
```python
all_assets = [
    *dg.load_assets_from_modules([my_module], group_name='my_custom_group'),
]
```

Then materialize:
```bash
uv run dagster asset materialize --select "group:my_custom_group"
```

### Backfilling Historical Data

To materialize all partitions for historical analysis:

```bash
# All FRED series (unpartitioned)
uv run dagster asset materialize --select "bronze/fred/all_series"

# All World Bank data for specific countries
uv run dagster asset materialize --select "bronze/world_bank/timeseries" \
  --partition "USA" \
  --partition "CHN" \
  --partition "JPN"

# All World Bank data (20 countries)
uv run dagster asset materialize --select "bronze/world_bank/timeseries"

# All SEC 10-Ks for specific companies
uv run dagster asset materialize --select "bronze/sec/form_10k" \
  --partition "AAPL" \
  --partition "MSFT" \
  --partition "SBUX"
```

---

## Next Steps

- [Analyze your data](ANALYSIS.md)
- [Write tests](TESTING.md)
- [Add new data sources](ADDING_DATA_SOURCES.md)

For questions or issues, see [CONTRIBUTING.md](CONTRIBUTING.md).
