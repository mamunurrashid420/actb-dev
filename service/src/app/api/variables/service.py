"""Variable service for business logic."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from supabase import Client

from src.lib.supabase.client import get_supabase_user_client

from .schema import VariableCreate, VariableUpdate


class VariableService:
    """Service for managing variables."""

    def __init__(self, supabase: Client = Depends(get_supabase_user_client)):
        self.supabase = supabase
        self.table = "variables"

    async def list(self) -> list[dict]:
        """List all variables."""
        result = self.supabase.table(self.table).select("*").execute()
        return result.data

    async def get_by_id(self, variable_id: str) -> dict | None:
        """Get a variable by ID."""
        result = (
            self.supabase
            .table(self.table)
            .select("*")
            .eq("id", variable_id)
            .maybe_single()
            .execute()
        )
        return result.data

    async def create(self, data: VariableCreate) -> dict:
        """Create a new variable."""
        result = (
            self.supabase
            .table(self.table)
            .insert({
                "name": data.name,
                "type": data.type.value,
                "default_value": data.default_value,
                "description": data.description,
                "tags": data.tags,
            })
            .execute()
        )
        return result.data[0]

    async def update(self, data: VariableUpdate) -> dict:
        """Update an existing variable."""
        # Build update dict with only provided fields
        update_data = {}
        if data.name is not None:
            update_data["name"] = data.name
        if data.type is not None:
            update_data["type"] = data.type.value
        if data.default_value is not None:
            update_data["default_value"] = data.default_value
        if data.description is not None:
            update_data["description"] = data.description
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
                detail="Variable not found",
            )

        return result.data[0]

    async def delete(self, variable_id: str) -> bool:
        """Delete a variable by ID."""
        result = (
            self.supabase.table(self.table).delete().eq("id", variable_id).execute()
        )
        return len(result.data) > 0
