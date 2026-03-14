"""Stable public functions exposed by XLake."""

from __future__ import annotations

from .. import __version__


def get_version() -> str:
    """Return the XLake package version."""
    return __version__
