# Getting Started with actBI Data Pipeline

This guide will get you from zero to a running data pipeline in about 10 minutes.

## Prerequisites

Before you begin, make sure you have:

- **Python 3.12** or newer
- **`uv`** package manager ([installation instructions](https://github.com/astral-sh/uv))
- A terminal/command line interface

**Optional (for full functionality):**
- **FRED API key** - Get one [here](https://fred.stlouisfed.org/docs/api/api_key.html) (free, required for US economic data)
- **BLS API key** - Register [here](https://data.bls.gov/registrationEngine/) (free, required for US labor market data)
- **World Bank** - No API key needed (always available)
- **SEC EDGAR** - No API key needed (identity string required, see below)

## Installation

### 1. Navigate to the Project

```bash
cd pipelines  # from repository root
```

**Important:** All commands in this guide must be run from the `pipelines/` directory.

### 2. Install Dependencies

```bash
uv sync
```

This reads `pyproject.toml` and installs all required packages into a virtual environment (`.venv`).

### 3. Set Up Configuration

Create a `.env` file with your API keys and configuration:

```bash
# Copy the example file
cp .env.example .env

# Edit it with your API keys
nano .env  # or use your preferred editor
```

Your `.env` file should look like this:

```bash
# API Keys (optional - only needed for specific data sources)
FRED_API_KEY=your_fred_key_here
BLS_API_KEY=your_bls_key_here
NOAA_API_TOKEN=your_noaa_token_here

# SEC EDGAR Identity (required for SEC data)
# Format: "Your Name email@domain.com"
SEC_IDENTITY="Your Name your.email@domain.com"

# Dagster configuration (required)
# Set DAGSTER_HOME to the .dagster directory in the current project
# Run: echo "DAGSTER_HOME=$(pwd)/.dagster" >> .env
DAGSTER_HOME=
```

**Notes:**
- **World Bank** and **NASA POWER** require no API key—you can use them immediately
- **SEC EDGAR** requires an identity string (your name and email for contact purposes)
- Leave API keys blank if you don't have them—those data sources simply won't be available

### 4. Create Dagster Storage Directory

```bash
mkdir -p .dagster
```

This directory stores Dagster's run history, schedule state, and metadata.

## First Run

### Start the Dagster UI

```bash
uv run dg dev
```

You should see output like:

```
Serving dagster-webserver on http://127.0.0.1:3000 in process 12345
```

**Open your browser to http://localhost:3000** to see the Dagster UI.

### What You'll See

The Dagster UI has several main views:

#### **Assets Tab** (most important)
Shows all available datasets in the pipeline. You'll see:

- **Asset groups** - Organized by data source:
  - `reference` - Crosswalk and registry data
  - `fred` - Federal Reserve economic data
  - `bls` - Bureau of Labor Statistics data
  - `world_bank` - International economic indicators
  - `country_indicators` - Published country-level indicators
  - `sec_filings` - SEC public company filings

- **Asset keys** - The full path to each asset (e.g., `bronze/fred/timeseries`)

- **Status indicators**:
  - Green checkmark ✅ - Materialized (data exists)
  - Gray circle ○ - Not yet materialized (no data)
  - Yellow warning ⚠ - Stale (dependencies updated, needs refresh)

#### **Runs Tab**
Shows history of materializations (successful and failed).

#### **Schedules Tab**
Shows 4 weekly schedules (all start STOPPED—you must enable them manually).

## Your First Materialization

Let's materialize some data! We'll start with World Bank GDP data since it requires no API key.

### Option 1: Using the UI (Easiest)

1. Click the **Assets** tab
2. Find `bronze/world_bank/timeseries` in the asset graph
3. Click on it to open the details panel
4. Click **"Materialize"** button
5. In the dialog, select specific partitions or click "All partitions"
6. Click **"Launch run"**

You'll be redirected to the Runs tab where you can watch the progress.

### Option 2: Using the CLI

```bash
# Materialize all World Bank data (20 country partitions, each with all indicators)
uv run dg asset materialize --select "bronze/world_bank/timeseries"

# Materialize just one country partition (faster for testing)
uv run dg asset materialize --select "bronze/world_bank/timeseries" --partition "USA"
```

**Expected output:**
```
2025-11-22 10:30:15 +0000 - dagster - INFO - Launching run...
2025-11-22 10:30:18 +0000 - dagster - INFO - Fetching all indicators for USA...
2025-11-22 10:30:22 +0000 - dagster - INFO - World Bank fetch complete
```

### Understanding What Just Happened

1. Dagster called the World Bank API
2. Downloaded all configured indicators for the USA (one partition contains all indicators for a country)
3. Converted it to a pandas DataFrame
4. Saved it as a Parquet file in `_data/assets/bronze/world_bank/timeseries/partition=USA/data.parquet`
5. Recorded metadata (record count, date range, indicators fetched) in the Dagster database

## Next Steps

### Materialize More Data

Now that you understand the basics, try materializing more assets:

```bash
# If you have a FRED API key:
uv run dg asset materialize --select "bronze/fred/all_series"

# Materialize the reference crosswalk (no API needed):
uv run dg asset materialize --select "silver/reference/indicator_crosswalk"

# Materialize published indicators (depends on raw data being available):
uv run dg asset materialize --select "gold/economic/growth/gdp" --partition "USA"
```

### Explore Your Data

Use the provided helper script to load materialized data:

```python
from load_assets import load_asset

# Load GDP data
gdp_raw = load_asset('bronze/world_bank/timeseries')  # Returns a list of DataFrames
print(gdp_raw[0].head())
```

Or use DuckDB for SQL queries:

```python
import duckdb

duckdb.sql('''
    SELECT *
    FROM '_data/assets/bronze/world_bank/timeseries/**/*.parquet'
    WHERE country = 'USA'
''').show()
```

See [ANALYSIS.md](ANALYSIS.md) for more examples.

## Common Commands Cheat Sheet

### Running the Pipeline

```bash
# Start Dagster UI
uv run dg dev

# Start on a different port
uv run dg dev --port 3001

# Validate definitions (check for errors)
uv run dg check defs
```

### Materializing Assets

```bash
# All assets
uv run dg asset materialize --select "*"

# Specific asset group
uv run dg asset materialize --select "group:fred"

# Unpartitioned asset (FRED/BLS all series)
uv run dg asset materialize --select "bronze/fred/all_series"

# Partitioned asset - all partitions
uv run dg asset materialize --select "bronze/world_bank/timeseries"

# Specific partition (country code for World Bank, ticker for SEC)
uv run dg asset materialize --select "bronze/world_bank/timeseries" --partition "USA"
uv run dg asset materialize --select "bronze/sec/form_10k" --partition "AAPL"

# Asset and all its upstream dependencies
uv run dg asset materialize --select "+gold/economic/growth/gdp"
```

### Managing Schedules

```bash
# List all schedules and their status
uv run dg schedule list

# Enable a schedule
uv run dg schedule start weekly_fred_refresh

# Disable a schedule
uv run dg schedule stop weekly_fred_refresh
```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_assets/test_fred_raw.py

# Run with verbose output
uv run pytest -v
```

## Troubleshooting

### "Command not found: dg"

**Problem:** The `dg` command isn't available.

**Solution:** Make sure you're using `uv run dg` (not just `dg`), and that you've run `uv sync` to install dependencies.

### "FRED_API_KEY environment variable not set"

**Problem:** Trying to materialize FRED data without an API key.

**Solution:**
1. Get a FRED API key from https://fred.stlouisfed.org/docs/api/api_key.html
2. Add it to your `.env` file: `FRED_API_KEY=your_key_here`
3. Restart Dagster (`uv run dg dev`)

### "No partitions found"

**Problem:** Trying to materialize a specific partition that doesn't exist.

**Solution:** Check available partitions in `src/pipelines/partitions.py`. For example:
- FRED: Unpartitioned (use `bronze/fred/all_series` without --partition flag)
- BLS: Unpartitioned (use `bronze/bls/all_series` without --partition flag)
- World Bank: Country codes like `USA`, `CHN`, `JPN` (3-letter codes)
- SEC: Company tickers like `AAPL`, `MSFT`, `SBUX` or institution CIKs like `0001067983`

### Dagster UI shows stale assets

**Problem:** After materializing upstream assets, downstream assets show as "stale".

**Solution:** This is expected! It means the upstream data changed and downstream assets need to be rematerialized. Click the stale asset and materialize it again.

### Directory not found errors

**Problem:** Parquet files fail to save.

**Solution:** Make sure you created the `.dagster` directory:
```bash
mkdir -p .dagster
```

And that `_data/assets/` directory is writable:
```bash
mkdir -p _data/assets
```

### For More Help

- Check [OPERATIONS.md](OPERATIONS.md#troubleshooting) for detailed troubleshooting
- Review Dagster logs in the UI under the "Runs" tab
- Ask questions in the project issue tracker

## What's Next?

Now that you have the pipeline running:

1. **Understand the concepts** - Read [CONCEPTS.md](CONCEPTS.md) to learn about assets, partitions, and the DAG
2. **Explore the architecture** - See [ARCHITECTURE.md](ARCHITECTURE.md) for design decisions
3. **Add new data** - Follow [ADDING_DATA_SOURCES.md](ADDING_DATA_SOURCES.md) to add your own data sources
4. **Analyze the data** - Check out [ANALYSIS.md](ANALYSIS.md) for query examples

Happy data pipelining! 🚀
