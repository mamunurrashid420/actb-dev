# Notebooks - Agent Reference

**For detailed explanations, see notebooks/README.md (human docs)**

## Current State

Jupyter notebook environment with access to all monorepo libraries via dedicated kernel.

## Auto-Imported on Kernel Start

The actBI kernel automatically imports these when it starts:

```python
import pandas as pd
import numpy as np
import duckdb
from shared import data  # Use as data.get(), data.list_assets(), etc.
```

## Additional Imports

```python
# Pipeline access
from pipelines.partitions import semantic_countries, company_partitions
from pipelines.resources import FredApiResource

# Shared IO
from shared.io import AssetStore

# Visualization
import matplotlib.pyplot as plt
import plotly.express as px
```

## Data Access Patterns

### Using data module (Recommended)

```python
# Already available - no import needed!
data.list_assets()
df = data.get('gold/economic/growth/gdp', partition='USA')
```

### Direct Parquet Access

```python
import pandas as pd
df = pd.read_parquet('pipelines/_data/assets/bronze/fred/all_series/data.parquet')
```

### SQL Queries

```python
import duckdb
result = duckdb.query("""
    SELECT * FROM read_parquet('pipelines/_data/assets/gold/economic/*/data.parquet')
""").to_df()
```

## Project Structure

```
notebooks/
├── notebooks/              # Notebook files (.ipynb)
├── pyproject.toml          # Dependencies
├── scripts/                # Installation scripts
├── src/notebooks/          # Package utilities
├── startup/                # Kernel initialization scripts
└── tests/                  # Test files
```

## Commands

```bash
# Install kernel
uv run python scripts/install_kernel.py

# Launch Jupyter
uv run jupyter lab

# Run tests
uv run pytest tests

# Lint & format
uv run ruff check .
uv run ruff format .
```

## Kernel

- **Name**: `actbi`
- **Display Name**: "actBI"
- **Install**: `uv run python scripts/install_kernel.py`
- **Startup script**: `startup/00-init.py` (edit to customize auto-imports)

## Guidelines

1. Place notebooks in the `notebooks/` subdirectory
2. Use `shared.data` for loading materialized assets
3. Follow coding standards from `CODING_STANDARDS.md`
4. Keep notebooks focused on exploration
