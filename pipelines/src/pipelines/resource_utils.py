"""Shared utilities for Dagster resources.

Lightweight utilities extracted from common patterns across API resources.
Prefer composition over inheritance - use these utilities rather than
inheriting from a heavy base class.
"""

import datetime as dt
import re
from pathlib import Path


def is_cache_valid(cache_path: Path, ttl_hours: float) -> bool:
    """Check if cached file exists and is within TTL.

    Args:
        cache_path: Path to the cached file
        ttl_hours: Time-to-live in hours (e.g., 24 for daily refresh)

    Returns:
        True if file exists and was modified within ttl_hours
    """
    if not cache_path.exists():
        return False
    mtime = dt.datetime.fromtimestamp(cache_path.stat().st_mtime)
    age_hours = (dt.datetime.now() - mtime).total_seconds() / 3600
    return age_hours < ttl_hours


def to_snake_case(name: str) -> str:
    """Convert camelCase or PascalCase to snake_case.

    Args:
        name: String in camelCase or PascalCase

    Returns:
        String in snake_case
    """
    # Insert underscore before uppercase letters (except at start)
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    # Insert underscore before uppercase letters that follow lowercase
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def standardize_column_names(columns: list[str]) -> dict[str, str]:
    """Create rename mapping for standardizing column names to snake_case.

    Usage:
        df.rename(standardize_column_names(df.columns))

    Args:
        columns: List of column names

    Returns:
        Dict mapping original names to snake_case versions
    """
    return {col: to_snake_case(col).replace(" ", "_") for col in columns}
