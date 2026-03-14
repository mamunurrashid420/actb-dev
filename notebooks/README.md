# Notebooks

Jupyter notebook environment for actBI data exploration. This project provides a dedicated kernel with access to all monorepo libraries.

## Setup

From the `notebooks/` directory:

```bash
# Install dependencies
uv sync

# Install the actBI kernel
uv run python scripts/install_kernel.py
```

This registers a Jupyter kernel that automatically:
- Sets `ACTBI_DATA_PATH` to the pipelines data directory
- Imports `pandas`, `numpy`, `duckdb` with standard aliases
- Imports `from shared import data` for data access
- Sets `data.use_env('local')` for local development

## Usage

### VS Code (Recommended)

1. Install the [Jupyter extension](https://marketplace.visualstudio.com/items?itemName=ms-toolsai.jupyter)
2. Open a notebook in VS Code
3. Select **"actBI"** from the kernel picker (top-right)

### Jupyter Lab (Alternative)

```bash
cd notebooks
./start.sh
# Or: uv run jupyter lab
```

Select **"actBI"** kernel when creating or opening notebooks.

### Using the Kernel

The kernel auto-initializes with `data` available:

```python
# These are already available - no imports needed!
data.list_assets()
data.get('gold/economic/growth/gdp', partition='USA')
```

## Available Imports

The kernel auto-imports these on startup:

```python
# Auto-imported and ready to use:
import pandas as pd
import numpy as np
import duckdb
from shared import data  # Use as data.get(), data.list_assets(), etc.
```

Additional monorepo packages are available:

```python
# Pipeline definitions
from pipelines.partitions import semantic_countries, company_partitions
from pipelines.resources import FredApiResource

# Shared IO
from shared.io import AssetStore
```

### Loading Data

```python
# List available assets
data.list_assets()

# Load a gold asset with partition
df = data.get('gold/economic/growth/gdp', partition='USA')

# Load all partitions
all_gdp = data.get_all('gold/economic/growth/gdp')

# Get asset metadata
data.describe('gold/economic/growth/gdp')
```

### Direct Parquet Access

```python
import pandas as pd

# Read materialized assets directly
df = pd.read_parquet('pipelines/_data/assets/bronze/fred/all_series/data.parquet')
```

### SQL with DuckDB

```python
import duckdb

# Query across multiple assets
result = duckdb.query("""
    SELECT * FROM read_parquet('pipelines/_data/assets/gold/economic/*/data.parquet')
    WHERE country = 'USA'
""").to_df()
```

## Project Structure

```
notebooks/
├── notebooks/              # Notebook files (.ipynb)
├── pyproject.toml          # Dependencies
├── README.md               # This file
├── AI_INSTRUCTIONS.md      # AI agent instructions
├── start.sh                # Jupyter Lab launch script
├── startup/
│   └── 00-init.py          # Auto-imports pd, np, duckdb, data
├── scripts/
│   └── install_kernel.py   # Kernel installation
├── src/notebooks/          # Package utilities
└── tests/                  # Tests
```

### Reinstalling the Kernel

If you modify `kernel_launcher.py`, reinstall with:
```bash
uv run python scripts/install_kernel.py
```

Changes to `startup/00-init.py` take effect on kernel restart (no reinstall needed).

## Adding Notebooks

Place notebooks in the `notebooks/` subdirectory. They will have access to all workspace packages.

## Development

```bash
# Run tests
uv run pytest tests

# Lint
uv run ruff check .

# Format
uv run ruff format .
```
