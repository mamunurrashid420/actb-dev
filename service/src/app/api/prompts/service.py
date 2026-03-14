"""Prompt service for business logic."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from supabase import Client

from src.lib.supabase.client import get_supabase_user_client

from .schema import PromptCreate, PromptUpdate


class PromptService:
    """Service for managing prompts."""

    def __init__(self, supabase: Client = Depends(get_supabase_user_client)):
        self.supabase = supabase
        self.table = "prompts"

    async def list(self) -> list[dict]:
        """List all prompts."""
        result = self.supabase.table(self.table).select("*").execute()
        return result.data

    async def get_by_id(self, prompt_id: str) -> dict | None:
        """Get a prompt by ID."""
        result = (
            self.supabase
            .table(self.table)
            .select("*")
            .eq("id", prompt_id)
            .maybe_single()
            .execute()
        )
        return result.data

    async def create(self, data: PromptCreate) -> dict:
        """Create a new prompt."""
        # Convert blocks to serializable format
        blocks = [block.model_dump(by_alias=True) for block in data.blocks]

        result = (
            self.supabase
            .table(self.table)
            .insert({
                "name": data.name,
                "tags": data.tags,
                "blocks": blocks,
            })
            .execute()
        )
        return result.data[0]

    async def update(self, data: PromptUpdate) -> dict:
        """Update an existing prompt."""
        update_data = {}
        if data.name is not None:
            update_data["name"] = data.name
        if data.tags is not None:
            update_data["tags"] = data.tags
        if data.blocks is not None:
            update_data["blocks"] = [
                block.model_dump(by_alias=True) for block in data.blocks
            ]

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
                detail="Prompt not found",
            )

        return result.data[0]

    async def delete(self, prompt_id: str) -> bool:
        """Delete a prompt by ID."""
        result = self.supabase.table(self.table).delete().eq("id", prompt_id).execute()
        return len(result.data) > 0
