"""Hive-standard path resolution for asset storage.

This module provides the canonical path resolution logic used by both
the Dagster IO manager (pipelines) and the standalone AssetStore (shared).

Hive-standard patterns:
- Unpartitioned: {base}/{asset_path}/data.parquet
- Partitioned:   {base}/{asset_path}/{partition=value}/data.parquet

Shard file patterns:
- Sharded parquet: part-NNNN.parquet (4-digit zero-padded)
"""

from upath import UPath

# Shard file naming pattern
SHARD_FILENAME_PATTERN = "part-{:04d}.parquet"
SHARD_GLOB_PATTERN = "part-*.parquet"


def build_shard_filename(shard_idx: int) -> str:
    """Build shard filename for sharded parquet datasets.

    Args:
        shard_idx: Zero-based shard index

    Returns:
        Filename like 'part-0000.parquet', 'part-0001.parquet', etc.
    """
    return SHARD_FILENAME_PATTERN.format(shard_idx)


def build_hive_partition_path(partition_key: str | dict) -> str:
    """Build Hive-style partition path from partition key.

    Args:
        partition_key: String for single-dim ('USA') or dict for multi-dim
                      ({'country': 'USA', 'indicator': 'GDP'})

    Returns:
        Hive-style path like 'partition=USA' or 'country=USA/indicator=GDP'
    """
    if isinstance(partition_key, dict):
        sorted_dims = sorted(partition_key.items())
        return "/".join(f"{dim}={val}" for dim, val in sorted_dims)
    return f"partition={partition_key}"


def resolve_asset_path(
    base_path: str | UPath,
    asset_path: str | list | tuple,
    partition_key: str | dict | None = None,
) -> UPath:
    """Resolve asset to Hive-standard file path (without extension).

    Hive-standard patterns:
    - Unpartitioned: {base}/{asset_path}/data
    - Partitioned:   {base}/{asset_path}/{partition=value}/data

    Args:
        base_path: Root directory for assets
        asset_path: Asset path as string ('bronze/fred/all_series') or
                   list/tuple (['bronze', 'fred', 'all_series'])
        partition_key: Optional partition key (str or dict)

    Returns:
        UPath to data file (without extension)
    """
    if isinstance(base_path, str):
        base_path = UPath(base_path)

    # Normalize asset_path to list
    if isinstance(asset_path, str):
        asset_path = asset_path.strip("/")
        asset_parts = [p for p in asset_path.split("/") if p]
    else:
        asset_parts = list(asset_path)

    if not asset_parts:
        raise ValueError("Asset path must contain at least one component")

    # Build base path to asset directory
    asset_dir = base_path / "/".join(asset_parts)

    # Add partition path if partitioned
    if partition_key:
        partition_path = build_hive_partition_path(partition_key)
        return asset_dir / partition_path / "data"

    # Unpartitioned: asset directory + data file (Hive-standard)
    return asset_dir / "data"


def parse_hive_partition_path(partition_path: str) -> str | dict:
    """Parse Hive-style partition path back to partition key.

    Inverse of build_hive_partition_path().

    Args:
        partition_path: Hive-style path like 'partition=USA' or
                       'country=USA/indicator=GDP'

    Returns:
        For single-dimension (partition=X): returns the value as string
        For multi-dimension (key1=val1/key2=val2): returns dict

    Examples:
        'partition=USA' → 'USA'
        'country=USA/indicator=GDP' → {'country': 'USA', 'indicator': 'GDP'}
    """
    parts = partition_path.split("/")

    if len(parts) == 1:
        # Single dimension: partition=value
        key, value = parts[0].split("=", 1)
        if key == "partition":
            return value
        # Single named dimension still returns dict
        return {key: value}

    # Multi-dimensional: key1=val1/key2=val2/...
    result = {}
    for part in parts:
        key, value = part.split("=", 1)
        result[key] = value
    return result


def parse_data_file_path(
    file_path: str | UPath,
    base_path: str | UPath,
) -> tuple[str, str | dict | None]:
    """Parse a data file path back to (asset_path, partition_key).

    Inverse of resolve_asset_path() - extracts the asset path and partition
    key from a Hive-standard file path.

    Args:
        file_path: Full path to data file (with or without extension)
        base_path: Base directory for assets

    Returns:
        Tuple of (asset_path, partition_key) where partition_key is:
        - None for unpartitioned assets
        - str for single-dimension partitions
        - dict for multi-dimension partitions

    Examples:
        'bronze/bls/all_series/data.parquet'
            → ('bronze/bls/all_series', None)
        'bronze/sec/form_10k/partition=AAPL/data.parquet'
            → ('bronze/sec/form_10k', 'AAPL')
        'bronze/multi/asset/country=USA/year=2024/data.parquet'
            → ('bronze/multi/asset', {'country': 'USA', 'year': '2024'})
    """
    # Normalize paths
    if isinstance(file_path, str):
        file_path = UPath(file_path)
    if isinstance(base_path, str):
        base_path = UPath(base_path)

    # Get path relative to base
    try:
        rel_path = file_path.relative_to(base_path)
    except ValueError:
        # file_path doesn't start with base_path, use as-is
        rel_path = file_path

    parts = list(rel_path.parts)

    # Remove filename (data.parquet, data.json, etc.)
    if parts and parts[-1].startswith("data"):
        parts = parts[:-1]

    # Find partition directories (contain '=')
    partition_parts = []
    asset_parts = []

    for part in parts:
        if "=" in part:
            partition_parts.append(part)
        elif not partition_parts:
            # Only add to asset path if we haven't hit partitions yet
            asset_parts.append(part)

    asset_path = "/".join(asset_parts)

    if not partition_parts:
        return (asset_path, None)

    # Parse partition path
    partition_path = "/".join(partition_parts)
    partition_key = parse_hive_partition_path(partition_path)

    return (asset_path, partition_key)
