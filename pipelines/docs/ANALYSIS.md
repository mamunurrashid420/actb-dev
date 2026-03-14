# Data Analysis

This guide shows you how to analyze materialized data using Jupyter notebooks, DuckDB queries, and Python scripts.

## Table of Contents

1. [Jupyter Notebooks](#jupyter-notebooks)
2. [Loading Assets](#loading-assets)
3. [DuckDB Queries](#duckdb-queries)
4. [Common Analysis Patterns](#common-analysis-patterns)

---

## Jupyter Notebooks

### Setup

```bash
# Install dependencies (Jupyter is included)
uv sync

# Launch Jupyter Notebook
uv run jupyter notebook

# Or use Jupyter Lab (recommended)
uv run jupyter lab
```

This opens Jupyter in your browser at `http://localhost:8888`.

### Create a Notebook

1. Click "New" → "Python 3"
2. Create a new notebook in the `pipelines/` directory
3. Start analyzing!

---

## Loading Assets

### Using load_assets.py Helper

The `load_assets.py` helper makes it easy to load materialized data:

```python
from load_assets import load_asset

# Load GDP data (returns DataFrame or list of DataFrames for partitioned assets)
gdp_data = load_asset('gold/economic/growth/gdp')

# Load specific partition
us_gdp = load_asset('gold/economic/growth/gdp', partition='USA')

# Load raw FRED data (unpartitioned)
fred_data = load_asset('bronze/fred/all_series')
```

### Direct Parquet Loading

For more control, load Parquet files directly:

```python
import pandas as pd

# Load single partition
df = pd.read_parquet('_data/assets/gold/economic/growth/gdp/partition=USA/data.parquet')

# Load all partitions for an asset
import glob
files = glob.glob('_data/assets/gold/economic/growth/gdp/*/data.parquet')
dfs = [pd.read_parquet(f) for f in files]
all_gdp = pd.concat(dfs, ignore_index=True)
```

---

## DuckDB Queries

DuckDB lets you query Parquet files with SQL without loading them into memory.

### Basic Queries

```python
import duckdb

# Query unpartitioned asset (FRED)
result = duckdb.sql('''
    SELECT *
    FROM '_data/assets/bronze/fred/all_series/data.parquet'
    WHERE series_id = 'GDP' AND date >= '2020-01-01'
''').to_df()

# Query all partitions (use wildcard)
all_countries_gdp = duckdb.sql('''
    SELECT *
    FROM '_data/assets/gold/economic/growth/gdp/*/data.parquet'
    ORDER BY country, date
''').to_df()
```

### Joins Across Assets

```python
# Join GDP and unemployment data
combined = duckdb.sql('''
    SELECT
        g.country,
        g.date,
        g.gdp_value,
        u.unemployment_value
    FROM '_data/assets/gold/economic/growth/gdp/*/data.parquet' g
    JOIN '_data/assets/gold/economic/labor_market/unemployment/*/data.parquet' u
        ON g.country = u.country
        AND g.date = u.date
    WHERE g.date >= '2020-01-01'
''').to_df()
```

### Aggregations

```python
# Calculate average GDP growth by country
growth_by_country = duckdb.sql('''
    SELECT
        country,
        AVG(gdp_value) as avg_gdp,
        MAX(gdp_value) as max_gdp,
        MIN(gdp_value) as min_gdp
    FROM '_data/assets/gold/economic/growth/gdp/*/data.parquet'
    GROUP BY country
    ORDER BY avg_gdp DESC
''').to_df()
```

### Time Series Analysis

```python
# Calculate year-over-year growth
yoy_growth = duckdb.sql('''
    SELECT
        country,
        date,
        gdp_value,
        LAG(gdp_value, 4) OVER (PARTITION BY country ORDER BY date) as gdp_year_ago,
        (gdp_value - LAG(gdp_value, 4) OVER (PARTITION BY country ORDER BY date))
            / LAG(gdp_value, 4) OVER (PARTITION BY country ORDER BY date) * 100 as yoy_growth_pct
    FROM '_data/assets/gold/economic/growth/gdp/*/data.parquet'
    ORDER BY country, date
''').to_df()
```

---

## Common Analysis Patterns

### Pattern 1: Cross-Country Comparison

```python
import pandas as pd
import matplotlib.pyplot as plt

# Load GDP for multiple countries
countries = ['USA', 'CHN', 'JPN', 'DEU', 'GBR']
gdp_data = []

for country in countries:
    df = pd.read_parquet(f'_data/assets/gold/economic/growth/gdp/partition={country}/data.parquet')
    df['country'] = country
    gdp_data.append(df)

combined = pd.concat(gdp_data)

# Plot
pivot = combined.pivot(index='date', columns='country', values='gdp_value')
pivot.plot(figsize=(12, 6), title='GDP Comparison')
plt.ylabel('GDP (billions USD)')
plt.show()
```

### Pattern 2: Correlation Analysis

```python
import duckdb

# Get GDP and unemployment for correlation analysis
data = duckdb.sql('''
    SELECT
        g.country,
        g.date,
        g.gdp_value,
        u.unemployment_value
    FROM '_data/assets/gold/economic/growth/gdp/*/data.parquet' g
    JOIN '_data/assets/gold/economic/labor_market/unemployment/*/data.parquet' u
        ON g.country = u.country AND g.date = u.date
    WHERE g.country = 'USA'
''').to_df()

# Calculate correlation
correlation = data[['gdp_value', 'unemployment_value']].corr()
print(f"GDP vs Unemployment Correlation: {correlation.iloc[0, 1]:.3f}")
```

### Pattern 3: Company Financial Analysis

```python
# Load Apple's annual reports
apple_reports = pd.read_parquet('_data/assets/gold/companies/financials/annual_report/partition=AAPL/data.parquet')

# Plot revenue trend by fiscal year
apple_reports.plot(x='fiscal_year', y='revenue', kind='bar', title='Apple Revenue Trend')
plt.ylabel('Revenue (billions)')
plt.show()
```

### Pattern 4: Time Series Decomposition

```python
from statsmodels.tsa.seasonal import seasonal_decompose

# Load US GDP
us_gdp = pd.read_parquet('_data/assets/gold/economic/growth/gdp/partition=USA/data.parquet')
us_gdp['date'] = pd.to_datetime(us_gdp['date'])
us_gdp = us_gdp.set_index('date').sort_index()

# Decompose time series
decomposition = seasonal_decompose(us_gdp['gdp_value'], model='additive', period=4)

# Plot
fig, axes = plt.subplots(4, 1, figsize=(12, 10))
decomposition.observed.plot(ax=axes[0], title='Observed')
decomposition.trend.plot(ax=axes[1], title='Trend')
decomposition.seasonal.plot(ax=axes[2], title='Seasonal')
decomposition.resid.plot(ax=axes[3], title='Residual')
plt.tight_layout()
plt.show()
```

### Pattern 5: Export to CSV for External Tools

```python
import duckdb

# Export query results to CSV
duckdb.sql('''
    COPY (
        SELECT *
        FROM '_data/assets/gold/economic/growth/gdp/*/data.parquet'
        WHERE date >= '2020-01-01'
    ) TO 'gdp_export.csv' (HEADER, DELIMITER ',')
''')
```

---

## Visualization Examples

### GDP Growth Heatmap

```python
import seaborn as sns
import pandas as pd
import glob

# Load GDP for all countries
gdp_files = glob.glob('_data/assets/gold/economic/growth/gdp/*/data.parquet')
gdp_data = pd.concat([pd.read_parquet(f) for f in gdp_files])

# Pivot for heatmap
pivot = gdp_data.pivot_table(
    index='date',
    columns='country',
    values='gdp_growth_rate',
    aggfunc='mean'
)

# Plot heatmap
plt.figure(figsize=(14, 10))
sns.heatmap(pivot.T, cmap='RdYlGn', center=0, fmt='.1f')
plt.title('GDP Growth Rate by Country')
plt.show()
```

### Company Comparison Dashboard

```python
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Load financial data for multiple companies
companies = ['AAPL', 'MSFT', 'SBUX', 'MCD']
financials = []

for ticker in companies:
    df = pd.read_parquet(f'_data/assets/gold/companies/financials/annual_report/partition={ticker}/data.parquet')
    df['ticker'] = ticker
    financials.append(df)

combined = pd.concat(financials)

# Create subplot dashboard
fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=('Revenue', 'Net Income', 'Profit Margin', 'ROE')
)

fig.add_trace(
    go.Bar(x=combined['ticker'], y=combined['revenue'], name='Revenue'),
    row=1, col=1
)

fig.add_trace(
    go.Bar(x=combined['ticker'], y=combined['net_income'], name='Net Income'),
    row=1, col=2
)

fig.add_trace(
    go.Bar(x=combined['ticker'], y=combined['profit_margin'], name='Profit Margin'),
    row=2, col=1
)

fig.add_trace(
    go.Bar(x=combined['ticker'], y=combined['roe'], name='ROE'),
    row=2, col=2
)

fig.update_layout(height=800, showlegend=False, title_text="Company Financial Comparison")
fig.show()
```

---

## Best Practices

### 1. Use DuckDB for Large Datasets

If you're querying hundreds of partitions, use DuckDB instead of loading everything into pandas:

```python
# ✅ Good - Query with DuckDB (doesn't load all data into memory)
result = duckdb.sql('''
    SELECT AVG(gdp_value)
    FROM '_data/assets/gold/economic/growth/gdp/*/data.parquet'
''').fetchone()[0]

# ❌ Bad - Load everything then filter
all_data = pd.concat([pd.read_parquet(f) for f in glob.glob('_data/assets/gold/economic/growth/gdp/*/data.parquet')])
avg_gdp = all_data['gdp_value'].mean()
```

### 2. Cache Expensive Computations

```python
# Cache results to avoid re-querying
if not os.path.exists('cached_analysis.parquet'):
    result = duckdb.sql('''...long query...''').to_df()
    result.to_parquet('cached_analysis.parquet')
else:
    result = pd.read_parquet('cached_analysis.parquet')
```

### 3. Verify Data Exists

```python
import os

# Check if asset is materialized before trying to load
asset_path = '_data/assets/gold/economic/growth/gdp/partition=USA/data.parquet'
if not os.path.exists(asset_path):
    print(f"Asset not materialized yet. Run: dg asset materialize --select 'gold/economic/growth/gdp' --partition 'USA'")
else:
    df = pd.read_parquet(asset_path)
```

---

## Next Steps

- [Add new data sources](ADDING_DATA_SOURCES.md)
- [Run automated schedules](OPERATIONS.md)
- [Write tests](TESTING.md)

Happy analyzing! 📊
