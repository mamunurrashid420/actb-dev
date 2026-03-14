# shared-io

File I/O utilities for the actBI monorepo.

## Usage

```python
from shared.io import AssetStore
from shared.io.handlers import ParquetHandler
from shared.io.paths import resolve_asset_path
```

## Modules

- **store.py** - AssetStore abstraction for reading/writing data assets
- **handlers.py** - Format handlers (Parquet, JSON)
- **paths.py** - Path resolution utilities
- **streaming.py** - Streaming data utilities
