"""Auth models used across API dependencies."""

from typing import Any

from pydantic import BaseModel, Field


class AuthContext(BaseModel):
    """User context derived from JWT and Supabase profile data."""

    id: str
    email: str | None = None
    claims: dict[str, Any] = Field(default_factory=dict)
