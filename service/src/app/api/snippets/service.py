"""Snippet service for business logic."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from supabase import Client

from src.lib.supabase.client import get_supabase_user_client

from .schema import SnippetCreate, SnippetUpdate


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


class SnippetService:
    """Service for managing snippets."""

    def __init__(self, supabase: Client = Depends(get_supabase_user_client)):
        self.supabase = supabase
        self.table = "snippets"

    async def list(self) -> list[dict]:
        """List all snippets."""
        result = self.supabase.table(self.table).select("*").execute()
        return result.data

    async def get_by_id(self, snippet_id: str) -> dict | None:
        """Get a snippet by ID."""
        result = (
            self.supabase
            .table(self.table)
            .select("*")
            .eq("id", snippet_id)
            .maybe_single()
            .execute()
        )
        return result.data

    async def create(self, data: SnippetCreate) -> dict:
        """Create a new snippet."""
        result = (
            self.supabase
            .table(self.table)
            .insert({
                "name": data.name,
                "body": data.body,
                "tags": data.tags,
                "word_count": count_words(data.body),
            })
            .execute()
        )
        return result.data[0]

    async def update(self, data: SnippetUpdate) -> dict:
        """Update an existing snippet."""
        update_data = {}
        if data.name is not None:
            update_data["name"] = data.name
        if data.body is not None:
            update_data["body"] = data.body
            update_data["word_count"] = count_words(data.body)
        if data.tags is not None:
            update_data["tags"] = data.tags

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )

        result = (
            self.supabase
            .table(self.table)
            .update(update_data)
            .eq("id", data.id)
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Snippet not found",
            )

        return result.data[0]

    async def delete(self, snippet_id: str) -> bool:
        """Delete a snippet by ID."""
        result = self.supabase.table(self.table).delete().eq("id", snippet_id).execute()
        return len(result.data) > 0
