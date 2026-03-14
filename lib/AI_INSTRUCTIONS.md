# Shared Python Packages - AI Reference

## Purpose

The `lib/` directory contains reusable Python packages for the data platform. These packages use namespace packaging under `shared.*` for clean imports.

## Current Packages

| Package | Description |
|---------|-------------|
| `io/` | File I/O utilities (handlers, paths, streaming) |
| `data/` | Asset loading, environment management, SEC utilities |
| `prompts/` | Versioned prompt storage (scaffold) |

## Adding a New Package

1. Create directory: `lib/<package-name>/`
2. Create `pyproject.toml` with `name = "shared-<package-name>"`
3. Create source in `src/shared/<package-name>/` (namespace package pattern)
4. Create `tests/` directory
5. Add to root `pyproject.toml` workspace members

**Namespace package pattern**: Python packages use the `shared.*` namespace. This allows imports like `from shared.io import store` and `from shared.data import assets` to work seamlessly.

Example structure:
```
lib/mypackage/
├── pyproject.toml          # name = "shared-mypackage"
├── src/
│   └── shared/
│       └── mypackage/      # Note: shared/ has no __init__.py (namespace)
│           ├── __init__.py
│           └── module.py
└── tests/
    └── test_module.py
```

## Import Patterns

```python
# IO utilities
from shared.io import AssetStore
from shared.io.handlers import ParquetHandler
from shared.io.paths import resolve_asset_path

# Data utilities
import shared.data as data
data.use_env("local")
df = data.get("gold/economic/gdp", partition="USA")

# Or direct imports
from shared.data.assets import get_environment
```

## Design Principles

1. **No Dagster dependencies**: Shared packages should be Dagster-free so they can be used in non-pipeline contexts
2. **Minimal dependencies**: Keep package dependencies minimal and well-justified
3. **Type hints**: All Python code should have type hints
4. **Tests**: Every package should have tests

## Workspace Configuration

Python packages are configured in the root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = [
    "lib/io",
    "lib/data",
    "lib/prompts",
    # ... other packages
]
```
