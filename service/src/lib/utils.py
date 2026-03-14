"""Shared utility functions."""

from datetime import UTC, datetime
from uuid import uuid4


def generate_id() -> str:
    """Generate a new UUID string."""
    return str(uuid4())


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(UTC)
