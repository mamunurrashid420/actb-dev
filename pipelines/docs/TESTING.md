# Testing

This guide explains our testing philosophy and how to write effective tests for the actBI data pipeline.

## Why Testing Matters

Businesses make real decisions based on this data. A bug in GDP calculations could lead to bad strategic choices. Testing ensures:

- Data transformations work correctly
- API integrations handle edge cases
- Changes don't break existing functionality
- Code is maintainable over time

## Running Tests

### All Tests

```bash
uv run pytest
```

### Specific Test File

```bash
uv run pytest tests/test_assets/test_fred_raw.py
```

### With Verbose Output

```bash
uv run pytest -v
```

### Watch Mode (re-run on file changes)

```bash
uv run pytest-watch
```

## Test Organization

Tests live in a separate `tests/` directory:

```
tests/
├── test_definitions.py       # Dagster definitions load correctly
├── test_io_managers.py        # File storage works
├── test_assets/               # Asset-specific tests
│   ├── test_fred_raw.py
│   ├── test_bls_raw.py
│   ├── test_sec.py
│   └── ...
└── test_utils/                # Shared test fixtures and mocks
    └── ...
```

## Testing Philosophy

### The got/want Pattern

We use "got/want" naming for clarity:

- **`want`** - The expected value (what you want)
- **`got`** - The actual value (what you got)

```python
def test_calculates_growth_rate():
    """Test that growth rate calculation is correct."""
    # Arrange
    data = pd.DataFrame({'value': [100, 110]})
    want_growth = 0.10

    # Act
    result = calculate_growth(data)
    got_growth = result['growth_rate'].iloc[-1]

    # Assert
    assert got_growth == pytest.approx(want_growth, rel=0.01)
```

### Arrange-Act-Assert

Every test follows this structure:

1. **Arrange** - Set up test data and expectations
2. **Act** - Execute the function under test
3. **Assert** - Compare got vs want

```python
def test_filters_missing_values():
    """Test that missing values are removed."""
    # Arrange
    raw_data = pd.DataFrame({'value': [1, None, 3]})
    want_length = 2

    # Act
    result = filter_missing(raw_data)
    got_length = len(result)

    # Assert
    assert got_length == want_length
```

## Writing Asset Tests

### Testing Transformation Logic

Extract transformation logic into pure functions for easy testing:

```python
# In src/pipelines/assets/fred.py
def transform_fred_data(df: pd.DataFrame) -> pd.DataFrame:
    """Transform raw FRED data into standardized format."""
    return (
        df
        .rename(columns={'date': 'timestamp', 'value': 'series_value'})
        .assign(timestamp=lambda x: pd.to_datetime(x['timestamp']))
    )

# Asset uses the helper
@dg.asset
def fred_timeseries(context, fred_api):
    raw_df = fred_api.get_series(context.partition_key)
    return transform_fred_data(raw_df)
```

```python
# In tests/test_assets/test_fred_raw.py
from pipelines.assets.fred import transform_fred_data

class TestFredTransformation:
    def test_renames_columns(self):
        """Test that columns are renamed correctly."""
        # Arrange
        raw_data = pd.DataFrame({
            'date': ['2024-01-01'],
            'value': [100]
        })
        want_columns = ['timestamp', 'series_value']

        # Act
        result = transform_fred_data(raw_data)
        got_columns = list(result.columns)

        # Assert
        assert got_columns == want_columns

    def test_converts_date_to_datetime(self):
        """Test that date strings are converted to datetime."""
        # Arrange
        raw_data = pd.DataFrame({
            'date': ['2024-01-01'],
            'value': [100]
        })
        want_dtype = 'datetime64[ns]'

        # Act
        result = transform_fred_data(raw_data)
        got_dtype = str(result['timestamp'].dtype)

        # Assert
        assert got_dtype == want_dtype
```

### Mocking External APIs

Don't call real APIs in tests—use mocks:

```python
import pytest
from unittest.mock import Mock

class TestGdpAsset:
    def test_fetches_correct_series(self):
        """Test that GDP asset fetches the right series ID."""
        # Arrange
        mock_api = Mock()
        mock_api.get_series.return_value = pd.Series([100, 110], index=['2023', '2024'])
        want_series_id = 'GDP'

        # Act
        context = Mock()
        context.partition_key = 'GDP'
        result = gdp(context, mock_api)

        # Assert
        mock_api.get_series.assert_called_once_with(want_series_id)
```

## Testing Patterns

### Pattern 1: Testing Data Transformations

```python
def test_normalizes_values():
    """Test value normalization."""
    # Arrange
    data = pd.DataFrame({'value': [10, 20, 30]})
    want_max = 1.0
    want_min = pytest.approx(0.333, rel=0.01)

    # Act
    result = normalize_values(data)
    got_max = result['normalized'].max()
    got_min = result['normalized'].min()

    # Assert
    assert got_max == want_max
    assert got_min == want_min
```

### Pattern 2: Testing Edge Cases

```python
def test_handles_empty_dataframe():
    """Test that empty DataFrame is handled gracefully."""
    # Arrange
    empty_df = pd.DataFrame()
    want_length = 0

    # Act
    result = process_data(empty_df)
    got_length = len(result)

    # Assert
    assert got_length == want_length

def test_handles_all_missing_values():
    """Test behavior when all values are missing."""
    # Arrange
    data = pd.DataFrame({'value': [None, None, None]})

    # Act & Assert
    with pytest.raises(ValueError, match="No valid data"):
        validate_data(data)
```

### Pattern 3: Testing Calculations

```python
def test_calculates_financial_ratios():
    """Test ROE calculation."""
    # Arrange
    financials = {
        'net_income': 1000,
        'equity': 5000,
    }
    want_roe = 0.20  # 20%

    # Act
    ratios = calculate_financial_ratios(financials)
    got_roe = ratios['roe']

    # Assert
    assert got_roe == pytest.approx(want_roe, rel=0.01)
```

## Testing Checklist

Before committing code, ensure:

- [ ] All tests pass (`uv run pytest`)
- [ ] New functions have tests
- [ ] Edge cases are covered (empty data, missing values, etc.)
- [ ] Tests use got/want naming
- [ ] Tests follow Arrange-Act-Assert pattern
- [ ] External APIs are mocked (not called in tests)
- [ ] Test names describe what is being tested

## Common Test Scenarios

### Testing Partitioned Assets

```python
def test_partition_key_is_used():
    """Test that partition key determines which data is fetched."""
    # Arrange
    mock_context = Mock()
    mock_context.partition_key = 'UNRATE'
    mock_api = Mock()
    want_series = 'UNRATE'

    # Act
    result = fred_timeseries(mock_context, mock_api)

    # Assert
    mock_api.get_series.assert_called_with(want_series)
```

### Testing Multi-Dimensional Partitions

```python
def test_multi_dim_partition_access():
    """Test accessing multi-dimensional partition keys."""
    # Arrange
    mock_context = Mock()
    mock_context.partition_key.keys_by_dimension = {
        'country': 'USA',
        'indicator': 'NY.GDP.MKTP.CD'
    }
    want_country = 'USA'
    want_indicator = 'NY.GDP.MKTP.CD'

    # Act
    country, indicator = extract_partition_keys(mock_context)

    # Assert
    assert country == want_country
    assert indicator == want_indicator
```

### Testing Data Quality

```python
def test_rejects_invalid_data():
    """Test that invalid data raises an error."""
    # Arrange
    invalid_data = pd.DataFrame({'value': [-999]})  # Invalid GDP value

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid GDP value"):
        validate_gdp_data(invalid_data)
```

## Debugging Failed Tests

### Read the Failure Message

```
FAILED tests/test_assets/test_fred_raw.py::test_normalizes_values
AssertionError: assert 0.5 == 1.0
```

This tells you:
- Which test failed (`test_normalizes_values`)
- What the assertion was (`0.5 == 1.0`)
- File and line number

### Add Print Statements

```python
def test_normalizes_values():
    # ...
    result = normalize_values(data)
    print(f"Result: {result}")  # Debug output
    print(f"Max: {result['normalized'].max()}")
    # ...
```

Run with `-s` to see print output:
```bash
uv run pytest -s tests/test_assets/test_fred_raw.py::test_normalizes_values
```

### Use pytest's Built-in Debugger

```bash
uv run pytest --pdb
```

When a test fails, you'll drop into an interactive debugger.

## Next Steps

- [Run the pipeline](OPERATIONS.md)
- [Add new data sources](ADDING_DATA_SOURCES.md)
- [Contribute](CONTRIBUTING.md)

Remember: Good tests give you confidence to change code. Write tests you'd want to see when debugging at 2 AM!
