"""Data Asset Library - Unified asset access across environments.

This library provides a simple interface for loading, saving, and discovering
data assets across different environments (local, dev, prod).

Basic usage:
    from shared.data import get, save, current_env

    # Load an asset
    df = get('gold/economic/growth/gdp', partition='US')

    # Check current environment
    env = current_env()  # Returns: 'local' or 'prod'

    # Switch environments
    use_env('prod')

For more details, see ASSET_DISCOVERY.md
"""

# Domain-specific modules
from shared.data import sec, themes
from shared.data.assets import (
    AssetMetadata,
    current_env,
    describe,
    env,
    get,
    get_all,
    get_many,
    list_assets,
    list_environments,
    list_partitions,
    save,
    search,
    tree,
    use_env,
)
from shared.data.exceptions import (
    AssetNotFoundError,
    DataLibraryError,
    EnvironmentNotFoundError,
    EnvironmentPermissionError,
    PartitionNotFoundError,
)
from shared.data.types import ChartType, DataShape

__version__ = "0.1.0"

__all__ = [
    # Exceptions
    "DataLibraryError",
    "AssetNotFoundError",
    "PartitionNotFoundError",
    "EnvironmentNotFoundError",
    "EnvironmentPermissionError",
    # Environment management
    "current_env",
    "use_env",
    "list_environments",
    "env",
    # Asset loading
    "get",
    "get_all",
    "get_many",
    # Asset writing
    "save",
    # Asset discovery
    "list_assets",
    "list_partitions",
    "describe",
    "tree",
    "search",
    "AssetMetadata",
    # Domain-specific modules
    "sec",
    "themes",
    # Shared types
    "ChartType",
    "DataShape",
]
