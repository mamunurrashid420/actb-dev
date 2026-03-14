# shared-data

Data asset loading utilities for the actBI monorepo.

## Usage

```python
import shared.data as data

# Set environment
data.use_env("local")

# Load an asset
df = data.get("gold/economic/gdp", partition="USA")

# List available assets
data.list_assets()
```

## Modules

- **assets.py** - Asset loading and environment management
- **themes.py** - Theme definitions
- **sec.py** - SEC-specific utilities
- **exceptions.py** - Custom exceptions
