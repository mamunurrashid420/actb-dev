"""Embedding utilities for semantic search."""

from fastapi import HTTPException, status


async def embed_query(query: str) -> list[float]:
    """Generate an embedding for a query string."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Semantic search is not configured",
    )
