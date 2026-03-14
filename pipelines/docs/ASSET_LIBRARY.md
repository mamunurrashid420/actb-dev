# Data Asset Library

## Overview

The Data Asset Library provides a unified Python API for accessing Dagster assets across different environments (local, dev, production). It offers a simple, intuitive interface for both developers and LLM agents to discover, load, and save data assets.

**Import style:**
```python
from pipelines import get, save, describe
```

## Package Structure

```
pipelines/src/pipelines/
├── __init__.py       # Public API exports
├── assets.py         # AssetLoader and core functionality
└── exceptions.py     # Custom exceptions
```

---

## Core API

### Loading Assets

#### get()
Load a single partition of an asset.

```python
from pipelines import get

# Load unpartitioned asset (FRED - all series in one asset)
df = get('bronze/fred/all_series')

# Load partitioned asset (World Bank - single country)
df = get('bronze/world_bank/timeseries', partition='USA')

# Load non-partitioned reference asset
df = get('silver/reference/indicator_crosswalk')

# Cross-environment loading
prod_data = get('gold/economic/growth/gdp', partition='USA', env='prod')
```

#### get_all()
Load all partitions of an asset.

```python
from pipelines import get_all

# Load all partitions (returns dict[partition_key, DataFrame])
all_countries = get_all('bronze/world_bank/timeseries')
# Returns: {'USA': df1, 'CHN': df2, 'JPN': df3, ...}

# Iterate over all partitions
for country, df in all_countries.items():
    print(f"{country}: {len(df)} records")
```

#### get_many()
Load specific partitions of an asset.

```python
from pipelines import get_many

# Load specific partitions (returns dict[partition_key, DataFrame])
selected = get_many('bronze/world_bank/timeseries', partitions=['USA', 'CHN', 'JPN'])
# Returns: {'USA': df1, 'CHN': df2, 'JPN': df3}
```

### Saving Assets

#### save()
Save data to an asset with permission checks.

```python
from pipelines import save

# Save non-partitioned asset
save('silver/reference/new_crosswalk', crosswalk_df)

# Save partitioned asset
save('gold/economic/growth/gdp', us_gdp_df, partition='USA')

# Save to specific environment (requires write permission)
save('test/data', test_df, env='local')
```

**Permission checks:**
- Cannot write to `prod` environment (read-only)
- Can write to `local` environment
- Environment permissions configured in `assets.py`

---

## Discovery API

### list_assets()
List all available assets in the current environment.

```python
from pipelines import list_assets

# List all assets
assets = list_assets()
# Returns: ['bronze/fred/all_series', 'bronze/world_bank/timeseries', 'silver/reference/indicator_crosswalk', ...]

# Filter by prefix
economic_assets = [a for a in list_assets() if a.startswith('gold/economic/')]
```

### list_partitions()
List all partitions for a given asset.

```python
from pipelines import list_partitions

# List partitions for World Bank (country-partitioned)
partitions = list_partitions('bronze/world_bank/timeseries')
# Returns: ['USA', 'CHN', 'JPN', 'DEU', 'GBR', 'FRA', ...]

# Check if partition exists
if 'USA' in list_partitions('bronze/world_bank/timeseries'):
    df = get('bronze/world_bank/timeseries', partition='USA')
```

### describe()
Get detailed metadata about an asset.

```python
from pipelines import describe

# Get asset metadata
info = describe('bronze/world_bank/timeseries')

# AssetMetadata fields:
# - asset_key: str - Full asset path
# - asset_type: str - 'partitioned' or 'non_partitioned'
# - partition_count: int | None - Number of partitions (if partitioned)
# - partitions: list[str] | None - List of partition keys (if partitioned)
# - schema: dict[str, str] | None - Inferred column types
# - storage_path: str - Physical storage location
# - environments: list[str] - Environments where asset exists

print(f"Type: {info.asset_type}")
print(f"Partitions: {info.partition_count}")
print(f"Schema: {info.schema}")
```

### tree()
Get hierarchical view of all assets.

```python
from pipelines import tree

# Get full asset tree
asset_tree = tree()
# Returns nested dict structure:
# {
#     'bronze': {
#         'fred': ['all_series'],
#         'world_bank': ['timeseries']
#     },
#     'gold': {
#         'economic': {
#             'growth': ['gdp'],
#             'labor_market': ['unemployment']
#         }
#     }
# }

# Pretty print
import json
print(json.dumps(tree(), indent=2))
```

### search()
Search for assets by keyword.

```python
from pipelines import search

# Keyword search (searches asset paths and partition keys)
results = search('gdp')
# Returns: ['gold/economic/growth/gdp', 'bronze/fred/all_series', ...]

# Search is case-insensitive
results = search('GDP')  # Same results as search('gdp')
```

---

## Environment Management

### Environment Configuration

The library supports multiple environments with different permissions:

```python
# Configured environments
_ENVIRONMENTS = {
    'local': EnvironmentConfig(
        name='local',
        base_path='_data/assets',
        can_write=True,
        description='Local development'
    ),
    'prod': EnvironmentConfig(
        name='prod',
        base_path='_data/assets',
        can_write=False,  # Read-only
        description='Production (read-only)'
    )
}
```

### current_env()
Get the current environment name.

```python
from pipelines import current_env

# Check current environment
env = current_env()
# Returns: 'local' or 'prod'
```

### use_env()
Switch the default environment for the session.

```python
from pipelines import use_env

# Switch to production
use_env('prod')

# All subsequent operations use prod by default
df = get('gold/economic/growth/gdp', partition='USA')  # Loads from prod
```

### env() context manager
Temporarily switch environment for a block of code.

```python
from pipelines import env, get

# Mix environments for debugging
with env('prod'):
    upstream = get('bronze/fred/all_series')

# Process locally
processed = transform(upstream)
save('test/processed_gdp', processed)  # Saves to local (current env)
```

### list_environments()
List all available environments.

```python
from pipelines import list_environments

# Get available environments
envs = list_environments()
# Returns: ['local', 'prod']
```

---

## Error Handling

The library provides helpful error messages with suggestions:

### AssetNotFoundError
```python
from pipelines import get
from pipelines.exceptions import AssetNotFoundError

try:
    df = get('gold/companies/tesla/financials')
except AssetNotFoundError as e:
    # Error includes suggestions for similar assets
    print(e)
    # AssetNotFoundError: Asset 'gold/companies/tesla/financials' not found.
    # Did you mean: gold/companies/apple/financials?
```

### PartitionNotFoundError
```python
from pipelines import get
from pipelines.exceptions import PartitionNotFoundError

try:
    df = get('bronze/world_bank/timeseries', partition='INVALID')
except PartitionNotFoundError as e:
    # Error includes list of available partitions
    print(e)
    # PartitionNotFoundError: Partition 'INVALID' not found.
    # Available partitions: USA, CHN, JPN, DEU, GBR, FRA, ...
```

### EnvironmentNotFoundError
```python
from pipelines import use_env
from pipelines.exceptions import EnvironmentNotFoundError

try:
    use_env('staging')
except EnvironmentNotFoundError as e:
    print(e)
    # EnvironmentNotFoundError: Environment 'staging' not found.
    # Available environments: local, prod
```

### EnvironmentPermissionError
```python
from pipelines import save
from pipelines.exceptions import EnvironmentPermissionError

try:
    save('test/data', df, env='prod')
except EnvironmentPermissionError as e:
    print(e)
    # EnvironmentPermissionError: Cannot write to 'prod' environment.
    # prod is read-only.
```

---

## Usage Examples

### Basic Workflow
```python
from pipelines import get, save, describe

# 1. Discover asset structure
info = describe('bronze/world_bank/timeseries')
print(f"Available partitions: {info.partitions}")

# 2. Load data
usa_data = get('bronze/world_bank/timeseries', partition='USA')

# 3. Transform
processed = transform_indicators(usa_data)

# 4. Save result
save('test/processed_usa', processed)

# 5. Verify
loaded = get('test/processed_usa')
assert loaded.equals(processed)
```

### Cross-Environment Workflow
```python
from pipelines import get, save, env

# Common pattern: prod data, local processing
raw = get('bronze/sec/form_10k', partition='AAPL', env='prod')
transformed = my_transform(raw)
save('silver/sec/form_10k_financials', transformed, partition='AAPL', env='local')

# Compare versions
with env('local'):
    local_version = get('silver/sec/form_10k_financials', partition='AAPL')
with env('prod'):
    prod_version = get('silver/sec/form_10k_financials', partition='AAPL')
```

### Bulk Operations
```python
from pipelines import get_all, get_many

# Load all World Bank country data
all_countries = get_all('bronze/world_bank/timeseries')

# Process each country
for country, df in all_countries.items():
    print(f"{country}: {len(df)} records")

# Load specific countries
selected = get_many('bronze/world_bank/timeseries', partitions=['USA', 'CHN', 'JPN'])

# Combine into single dataframe
import pandas as pd
combined = pd.concat(
    [df.assign(country=key) for key, df in selected.items()],
    ignore_index=True
)
```

### LLM Agent Pattern
```python
from pipelines import search, describe, get

# 1. Discover assets
assets_found = search('GDP growth')
# Returns: ['gold/economic/growth/gdp', 'bronze/fred/all_series', ...]

# 2. Understand structure
schema = describe('gold/economic/growth/gdp')
print(f"Schema: {schema.schema}")
print(f"Partitions: {schema.partitions}")

# 3. Load data
us_gdp = get('gold/economic/growth/gdp', partition='USA')
cn_gdp = get('gold/economic/growth/gdp', partition='CHN')

# 4. Access with known schema
us_growth = us_gdp['gdp_growth_rate'].mean()
```

---

## Current Status

**Implemented (Phases 1-4):**
- ✅ Core foundation (package structure, environment config)
- ✅ Basic asset loading (get, get_all, get_many)
- ✅ Asset discovery & metadata (describe, search, tree, list_*)
- ✅ Writing & materialization (save with permission checks)

**Test Coverage:**
- 97 tests passing (all phases)
- Exception handling tests
- Environment management tests
- IOAdapter tests
- AssetLoader tests
- Integration tests with fixtures
- Save operation tests
- Permission tests

---

## Future Work

### Phase 5: Advanced Features
- [ ] Version tracking and storage
- [ ] list_versions() method for accessing historical data
- [ ] Semantic aliases for LLM (company names → CIKs, country names → codes)
- [ ] Enhanced metadata (questions answered, data lineage)
- [ ] Performance optimization & caching with TTL

### Phase 6: Cloud Storage & Production
- [ ] S3 adapter implementation (S3IOManager integration)
- [ ] Environment configs for dev/prod S3 buckets
- [ ] Deployment to dev environment
- [ ] Performance testing at scale
- [ ] Production deployment

### Versioning (Future)
```python
# Planned API for version support

# Pin specific version
df = get(
    'gold/companies/starbucks/financials',
    partition='FY2023',
    version='2024-11-15T10:30:00Z'
)

# List versions
versions = list_versions('gold/companies/starbucks/financials', partition='FY2023')
# Returns: ['2024-11-15T10:30:00Z', '2024-11-01T08:15:00Z', ...]
```

### Cloud Storage (Future)
```python
# Planned environment configuration for cloud storage

ENVIRONMENT_CONFIG = {
    'dev': {
        'io_manager': S3IOManager(
            bucket='actbi-dev',
            prefix='assets',
            region='us-east-1'
        ),
        'can_write': True,
        'description': 'Development cloud environment'
    },
    'prod': {
        'io_manager': S3IOManager(
            bucket='actbi-prod',
            prefix='assets',
            region='us-east-1'
        ),
        'can_write': False,
        'description': 'Production environment'
    }
}
```

---

## Implementation Notes

### Design Principles

1. **Start simple**: Single module files, add more only when needed
2. **Reuse existing**: Build on FileSystemIOManager and existing infrastructure
3. **No breaking changes**: Compatible with existing Dagster assets
4. **Helpful errors**: Always suggest alternatives/fixes
5. **Environment safety**: Prevent accidental prod writes

### Storage Structure

The library uses Hive-style partitioned storage compatible with query engines:

```
_data/assets/
├── bronze/
│   ├── fred/
│   │   └── all_series/
│   │       └── data.parquet           # Unpartitioned - all series in one file
│   ├── bls/
│   │   └── all_series/
│   │       └── data.parquet           # Unpartitioned - all series in one file
│   ├── world_bank/
│   │   └── timeseries/
│   │       ├── partition=USA/
│   │       │   └── data.parquet       # Single-dimension partition (country only)
│   │       └── partition=CHN/
│   │           └── data.parquet
│   └── sec/
│       ├── form_10k/
│       │   ├── partition=AAPL/
│       │   │   └── data.parquet       # Single-dimension partition (ticker)
│       │   └── partition=MSFT/
│       │       └── data.parquet
│       └── form_13f/
│           └── partition=0001067983/  # Single-dimension partition (CIK)
│               └── data.parquet
├── silver/
│   ├── reference/
│   │   └── indicator_crosswalk/
│   │       └── data.parquet           # Unpartitioned reference data
│   └── sec/
│       └── form_10k_financials/
│           └── partition=AAPL/        # Same partition as bronze
│               └── data.parquet
└── gold/
    ├── economic/
    │   └── growth/
    │       └── gdp/
    │           ├── partition=USA/     # 3-letter country codes
    │           │   └── data.parquet
    │           └── partition=CHN/
    │               └── data.parquet
    └── companies/
        └── financials/
            └── annual_report/
                └── partition=AAPL/    # Same partition as upstream
                    └── data.parquet
```

### Type Handlers

The IOAdapter supports multiple file formats:
- **Parquet**: DataFrame storage (default for time series)
- **JSON**: Dict storage (for nested/structured data)
- Automatically inferred from file extension

### Path Resolution

Asset paths are converted to AssetKeys internally:
- String path: `'bronze/fred/all_series'`
- Converted to: `AssetKey(['bronze', 'fred', 'all_series'])`
- Maps to: `_data/assets/bronze/fred/all_series/`

### Partition Keys

The pipeline uses **simplified single-dimension partitions**:

- **Unpartitioned assets**: No partition key needed
  - Example: `get('bronze/fred/all_series')` → `data.parquet`
- **Single-dimension partitions**: Simple string keys
  - Country: `partition='USA'` → `partition=USA/data.parquet`
  - Ticker: `partition='AAPL'` → `partition=AAPL/data.parquet`
  - CIK: `partition='0001067983'` → `partition=0001067983/data.parquet`

**Note**: Multi-dimensional partitions (e.g., `'AAPL|FY2024'`) are only used for certain SEC assets where both company and time period are required. Most assets use simple single-dimension partitions or are unpartitioned.

---

## Related Documentation

- **Project setup**: See `pipelines/README.md`
- **Asset architecture**: See `pipelines/docs/ASSET_ARCHITECTURE.md`
- **Coding standards**: See `CODING_STANDARDS.md`
- **AI instructions**: See `AI_INSTRUCTIONS.md`
