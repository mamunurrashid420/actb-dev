"""Pagination helpers for list endpoints."""

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Query params for pagination."""

    limit: int = Field(25, ge=1, le=200)
    offset: int = Field(0, ge=0)


class PaginatedResponse(BaseModel):
    """Generic paginated response container."""

    items: list
    total: int
    limit: int
    offset: int
