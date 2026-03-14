# Contributing to actBI

Thank you for your interest in contributing to the actBI data pipeline! This guide will help you get started.

## Quick Links

- [Code Standards](../../CODING_STANDARDS.md) - Python style guide and conventions
- [Architecture](ARCHITECTURE.md) - System design and patterns
- [Testing](TESTING.md) - How to write tests

## Getting Started

### 1. Set Up Your Environment

```bash
cd pipelines  # from repository root
uv sync
```

### 2. Make Sure Tests Pass

```bash
uv run pytest
```

### 3. Validate Definitions

```bash
uv run dg check defs
```

## Code Standards

We follow the coding standards defined in [`CODING_STANDARDS.md`](../../CODING_STANDARDS.md).

**Key requirements:**

- **Imports:** Use abbreviated imports (`import dagster as dg`, `import pandas as pd`)
- **Type hints:** All function parameters and return values
- **Docstrings:** Single-line preferred, Google-style for complex functions
- **Pandas:** Use method chaining
- **Testing:** Arrange-Act-Assert pattern with got/want naming

**Example:**

```python
import dagster as dg
import pandas as pd

@dg.asset(
    key_prefix=['economic', 'growth'],
    name='gdp',
)
def gdp(
    context: dg.AssetExecutionContext,
    fred_api: FredApiResource
) -> pd.DataFrame:
    """GDP data with intelligent source routing."""
    series_id = context.partition_key

    df = fred_api.get_series(series_id)

    return (
        df
        .rename(columns={'date': 'timestamp', 'value': 'gdp_value'})
        .assign(timestamp=lambda x: pd.to_datetime(x['timestamp']))
    )
```

## Contribution Workflow

### 1. Create a Feature Branch

```bash
# Make sure you're on main
git checkout main
git pull

# Create your feature branch
git branch feature/add-commodity-data
git checkout feature/add-commodity-data
```

### 2. Make Your Changes

Follow the patterns in existing code:

- **Adding data source:** See [ADDING_DATA_SOURCES.md](ADDING_DATA_SOURCES.md)
- **Modifying assets:** Follow [ARCHITECTURE.md](ARCHITECTURE.md) patterns
- **Adding tests:** Follow [TESTING.md](TESTING.md) guidelines

### 3. Test Your Changes

```bash
# Run all tests
uv run pytest

# Validate Dagster definitions
uv run dg check defs

# Test materialization
uv run dg asset materialize --select "your/new/asset"
```

### 4. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a descriptive message
git commit -m "Add commodity price data source

- Create CommodityApiResource for API integration
- Add partitioned raw asset for commodity prices
- Add published asset with rolling averages
- Include tests for transformation logic"
```

**Good commit messages:**
- Start with a verb (Add, Fix, Update, Refactor)
- Summarize the change in ~50 characters
- Optionally add bullet points for details

### 5. Push and Create PR

```bash
# Push your branch
git push -u origin feature/add-commodity-data
```

Then create a Pull Request on GitHub.

## PR Guidelines

### What to Include

- **Clear description** of what changed and why
- **Link to related issues** if applicable
- **Test results** (all tests passing)
- **Example usage** if adding new functionality

### PR Checklist

Before submitting, ensure:

- [ ] All tests pass (`uv run pytest`)
- [ ] Dagster definitions validate (`uv run dg check defs`)
- [ ] Code follows [`CODING_STANDARDS.md`](../../CODING_STANDARDS.md)
- [ ] New functions have type hints and docstrings
- [ ] New features have tests
- [ ] Documentation updated if needed

## Types of Contributions

### 1. Adding Data Sources

See [ADDING_DATA_SOURCES.md](ADDING_DATA_SOURCES.md) for detailed tutorial.

**Steps:**
1. Create resource class
2. Define partitions
3. Create raw asset
4. Create published asset
5. Add tests
6. Update documentation

### 2. Improving Documentation

Documentation lives in:
- `pipelines/docs/` - Human-facing documentation
- `CODING_STANDARDS.md` - Code style guide
- `AI_INSTRUCTIONS.md` - AI agent reference
- `README.md` - Project overview

**When updating docs:**
- Keep examples up-to-date with code
- Use real examples from the codebase
- Explain the "why" not just the "what"

### 3. Fixing Bugs

**Steps:**
1. Write a failing test that reproduces the bug
2. Fix the bug
3. Verify the test now passes
4. Add regression test if needed

### 4. Adding Tests

We always need more test coverage!

**Focus areas:**
- Edge cases (empty data, missing values, invalid inputs)
- Data transformations
- Partition handling
- Multi-dimensional partition access

### 5. Performance Improvements

**Before optimizing:**
1. Profile to identify bottleneck
2. Write benchmark test
3. Make improvement
4. Verify benchmark shows improvement
5. Ensure existing tests still pass

## Common Tasks

### Adding a Partition

Edit `src/pipelines/partitions.py`:

```python
fred_series_partitions = dg.StaticPartitionsDefinition([
    'GDP', 'UNRATE', ...,
    'NEW_SERIES',  # ← Add here
])
```

### Adding to Crosswalk

Edit `src/pipelines/assets/reference.py`:

```python
data = [
    # ... existing entries
    ('fred', 'NEW_SERIES', 'semantic_name', 'Display Name'),
]
```

### Running Specific Tests

```bash
# One test file
uv run pytest tests/test_assets/test_fred_raw.py

# One test function
uv run pytest tests/test_assets/test_fred_raw.py::test_transform_fred_data

# Tests matching a pattern
uv run pytest -k "test_fred"
```

## Questions or Issues?

- **Bug reports:** Open an issue on GitHub
- **Feature requests:** Open an issue with "Feature Request" label
- **Questions:** Check documentation first, then open a discussion

## Code of Conduct

- Be respectful and constructive
- Focus on the code, not the person
- Help others learn and grow
- Assume good intentions

## Thank You!

Every contribution, no matter how small, helps make actBI better. We appreciate your time and effort! 🎉
