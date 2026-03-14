# Python Coding Standards

This document defines the coding standards for the actBI project.

## Style Guide Foundation

Follow [PEP 8](https://peps.python.org/pep-0008/) with the project-specific modifications documented below.

## Automated Tooling

This project uses **Ruff** for both linting and formatting:

- **Linting**: Catches errors, enforces style, auto-fixes issues
- **Formatting**: Consistent code style with fluent method chain support

### Pre-commit Hooks

Hooks run automatically on `git commit`. To set up:

```bash
cd pipelines && uv sync --group dev  # Install dev dependencies
uv run pre-commit install            # Install hooks
```

### Manual Commands

```bash
uv run ruff check src/           # Check for lint errors
uv run ruff check --fix src/     # Auto-fix lint errors
uv run ruff format src/          # Format code
uv run pre-commit run --all-files  # Run all hooks
```

## String Conventions

- **Double quotes** (`"`) for all strings (Python community standard)
- **Triple double-quotes** (`"""`) for docstrings

```python
# Correct
name = "fred_connector"
query = "SELECT * FROM series"

def fetch_data():
    """Fetch data from external API."""
    pass
```

## Naming Conventions

- `snake_case` for functions and variables
- `CapWords` for classes
- `UPPER_CASE` for constants

```python
# Correct
MAX_RETRIES = 3
api_key = "abc123"

class FredConnector:
    pass

def fetch_series_data():
    pass
```

## Import Style

Use direct imports - import what you need from each module.

### Standard Aliases

A few libraries have universally accepted aliases:

```python
import pandas as pd
import numpy as np
import polars as pl
import datetime as dt
```

### Direct Imports

For most libraries, import specific items directly:

```python
from dagster import asset, AssetExecutionContext, MaterializeResult
from pathlib import Path
from collections import defaultdict
from typing import Any
```

### Organizing Imports

Ruff handles import sorting automatically. Group imports in this order:
1. Standard library
2. Third-party packages
3. Local/project imports

```python
from datetime import datetime
from pathlib import Path

import pandas as pd
from dagster import asset, AssetExecutionContext

from pipelines.resources import FredClient
from shared.io import read_parquet
```

## Pandas Method Chaining

Always prefer method chaining for pandas operations. This improves readability and makes data transformations explicit.

### Formatting Rules

1. Opening parenthesis on the same line as assignment
2. Start chain with the dataframe variable
3. Each method call on its own line, starting with the dot
4. Closing parenthesis at the end of the last method

```python
# Correct
df = (
    df
    .rename(columns={"old_name": "new_name"})
    .drop(columns=["unnecessary_column"])
    .sort_values("date")
    .reset_index(drop=True)
)

# Also correct - complex transformations
processed_df = (
    raw_df
    .pipe(validate_schema)
    .assign(
        year=lambda x: pd.to_datetime(x["date"]).dt.year,
        normalized_value=lambda x: x["value"] / x["value"].max()
    )
    .query("year >= 2020")
    .groupby("category")
    .agg({"value": ["mean", "std"]})
)
```

### Avoid

```python
# Incorrect - no chaining
df = df.rename(columns={"old_name": "new_name"})
df = df.drop(columns=["unnecessary_column"])
df = df.sort_values("date")

# Incorrect - improper formatting
df = df.rename(columns={"old_name": "new_name"}).drop(columns=["unnecessary_column"]).sort_values("date")
```

### Pandas Performance Best Practices

**Avoid unnecessary `.copy()` calls**: Most pandas methods (`.rename()`, `.assign()`, `.drop()`, `.query()`, etc.) already return new DataFrames. Explicit `.copy()` is only needed when modifying a slice in-place.

```python
# Unnecessary - rename() already returns a copy
df = original_df[original_df["x"] > 0].copy()
df = df.rename(columns={"old": "new"})

# Correct - chain methods that return copies
df = (
    original_df[original_df["x"] > 0]
    .rename(columns={"old": "new"})
)
```

**Avoid `iterrows()`**: It's slow due to Python overhead. Use vectorized operations or `.itertuples()` when iteration is necessary.

```python
# Slow - iterrows creates Series for each row
for idx, row in df.iterrows():
    results.append(row["a"] + row["b"])

# Fast - vectorized operation
results = df["a"] + df["b"]

# If iteration is needed, use itertuples (10-100x faster than iterrows)
for row in df.itertuples():
    process(row.a, row.b)
```

## Type Hints

Include type hints for function parameters and return values. This improves code clarity and enables better IDE support.

```python
import pandas as pd
from dagster import AssetKey

def process_series_data(
    raw_data: pd.DataFrame,
    series_id: str,
    normalize: bool = True
) -> pd.DataFrame:
    """Process raw series data into standardized format."""
    pass

def get_asset_key(series_id: str) -> AssetKey:
    """Generate Dagster asset key for the given series."""
    return AssetKey(["fred", "raw", series_id])
```

## Line Length

Maximum 88 characters per line (Ruff default). This balances readability with modern wide displays.

For long method chains, function calls, or complex expressions, break across multiple lines using the patterns shown in this document.

## Indentation

Use 4 spaces for indentation. Never use tabs.

## Project-Specific Patterns

### Dagster Assets

Use modern asset-based patterns (`@asset`) rather than ops-based approaches (`@op`). Follow the dual-layer architecture (pipeline vs published layers).

**See [`pipelines/docs/ASSET_ARCHITECTURE.md`](pipelines/docs/ASSET_ARCHITECTURE.md)** for complete Dagster patterns, asset naming, metadata standards, and best practices.

#### Logging and Metadata

**Use `context.log.info()` for status updates only:**
- Asset start/end messages
- Progress updates for long-running operations (e.g., "Batch 1/5 complete")

**Use `context.add_output_metadata()` for detailed information:**
- Record counts, date ranges, validation results
- Calculated metrics (growth rates, percentages)
- Key takeaways and summaries

```python
from dagster import asset, AssetExecutionContext
import pandas as pd

@asset
def data_asset(context: AssetExecutionContext) -> pd.DataFrame:
    context.log.info("Fetching data...")  # Status update

    df = fetch_and_process_data()

    # Record details in metadata, not logs
    context.add_output_metadata({
        "num_records": len(df),
        "date_range_start": str(df["date"].min()),
        "date_range_end": str(df["date"].max()),
    })
    context.log.info("Data fetch complete")  # Status update

    return df
```

### Error Handling

Be explicit about error handling, especially for external API calls and data validation:

```python
import logging

import requests

logger = logging.getLogger(__name__)

def fetch_data(api_key: str, series_id: str) -> pd.DataFrame:
    """Fetch data with proper error handling."""
    try:
        response = make_api_call(api_key, series_id)
        response.raise_for_status()
        return parse_response(response)
    except requests.HTTPError as e:
        logger.error(f"HTTP error fetching {series_id}: {e}")
        raise
    except ValueError as e:
        logger.error(f"Invalid response for {series_id}: {e}")
        raise
```

### Configuration and Secrets

**Pattern**: Each module that needs secrets must provide its own abstraction function. Never call `os.getenv()` directly from multiple places.

```python
import os

from fredapi import Fred

def get_fred_client() -> Fred:
    """Get FRED API client with API key from environment."""
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise ValueError("FRED_API_KEY environment variable not set")
    return Fred(api_key=api_key)
```

This centralizes secret access and makes it easy to change the implementation later.

## Documentation

- All public functions and classes must have docstrings
- **Prefer single-line docstrings** that describe what the function does
- Rely on type hints and self-documenting code for parameter and return information
- **Use multi-line docstrings** only for complex functions where the signature isn't sufficient

```python
# Simple functions - single-line docstring
def fetch_series_data(
    series_id: str,
    start_date: dt.datetime | None = None,
    end_date: dt.datetime | None = None
) -> pd.DataFrame:
    """Fetch time series data from FRED API for the specified series."""
    pass

def process_gdp_data(raw_data: pd.DataFrame) -> pd.DataFrame:
    """Process raw GDP data into standardized format."""
    pass

# Complex functions - multi-line when truly needed
def aggregate_economic_indicators(
    gdp: pd.DataFrame,
    unemployment: pd.DataFrame,
    inflation: pd.DataFrame,
    context: AssetExecutionContext
) -> dict[str, float]:
    """Aggregate multiple economic indicators into a summary dictionary.

    Combines data from multiple sources and calculates summary statistics
    for each indicator.

    Args:
        gdp: GDP data with 'value' column
        unemployment: Unemployment rate data with 'value' column
        inflation: Inflation rate data with 'value' column
        context: Dagster execution context for logging

    Returns:
        Dictionary with latest values and metadata for each indicator

    Raises:
        ValueError: If any dataframe is empty or missing required columns
    """
    pass
```

## Comments

- Write self-documenting code where possible
- Use comments to explain *why*, not *what*
- Keep comments concise and up-to-date

```python
# Correct - explains why
# Use local cache to avoid hitting API rate limits during development
cached_data = load_from_cache(series_id)

# Incorrect - states the obvious
# Load data from cache
cached_data = load_from_cache(series_id)
```

## Testing

All tests should follow the Arrange-Act-Assert pattern with the "got/want" naming convention for clarity.

For detailed testing strategy including test organization and Dagster-specific patterns, see [`pipelines/docs/TESTING_STRATEGY.md`](pipelines/docs/TESTING_STRATEGY.md).

### Test Framework

Use **pytest** with class-based organization. Tests live alongside source files with `*_test.py` suffix:

```python
import pytest
import pandas as pd

class TestProcessSeriesData:
    """Tests for process_series_data function."""

    def test_normalizes_values(self):
        """Test that process_series_data correctly normalizes values."""
        # Arrange - set up test data and expectations
        raw_data = pd.DataFrame({"value": [10, 20, 30]})
        want_max = 1.0
        want_min = 0.333

        # Act - execute the function under test
        result = process_series_data(raw_data, normalize=True)
        got_max = result["normalized_value"].max()
        got_min = result["normalized_value"].min()

        # Assert - compare got vs want
        assert got_max == want_max
        assert abs(got_min - want_min) < 0.01  # Approximate equality
```

### Got/Want Convention

Use consistent variable names for test assertions:

- **`want`** - The expected value (what you want the result to be)
- **`got`** - The actual value returned by the code being tested

This convention makes test assertions explicit and easy to understand.

### Common Assertion Patterns

Use clear pytest assertions:

```python
# Equality
assert got == want

# Approximate equality for floats
assert abs(got - want) < 0.01
# Or use pytest.approx
assert got == pytest.approx(want, rel=0.01)

# Boolean checks
assert got
assert not got

# Containment
assert item in collection
assert item not in collection

# None checks
assert got is None
assert got is not None

# Type checks
assert isinstance(got, ExpectedType)

# Comparisons
assert got > threshold
assert got < threshold
assert got >= threshold
assert got <= threshold

# Exceptions
with pytest.raises(ValueError):
    function_that_should_raise()
```

### Guidelines

1. **Always define `want` before `got`** to establish expectations upfront
2. **Use descriptive suffixes** when testing multiple values:
   ```python
   want_status = 200
   want_length = 5
   got_status = response.status_code
   got_length = len(response.data)
   assert got_status == want_status
   assert got_length == want_length
   ```
3. **Custom failure messages** can be added with comma:
   ```python
   assert got == want, f"Expected {want}, but got {got}"
   ```
4. **Use pytest markers** to categorize tests:
   ```python
   @pytest.mark.unit
   def test_fast_operation(self):
       """Fast unit test."""
       pass

   @pytest.mark.integration
   def test_external_api(self):
       """Integration test with external service."""
       pass
   ```

### Test Structure

- Test files use `*_test.py` suffix and live alongside source files
- Test classes group related tests (no base class required)
- Clear test method names that describe what is being tested (start with `test_`)
- Arrange-Act-Assert pattern with comments
- Type hints in test methods
- One logical assertion per test (or closely related assertions)
- Use `test_utils/` for shared mocks and fixtures

## Code Quality Principles

### Data Quality First

Since businesses will make real decisions based on this data:

- Validate data at ingestion boundaries
- Log data quality issues explicitly
- Fail fast on invalid data rather than propagating errors
- Include data lineage and provenance information

### Pragmatic Engineering

- Follow standard Python patterns
- Avoid premature optimization
- Build for the current use case, design for future extensibility
- Favor clarity over cleverness
