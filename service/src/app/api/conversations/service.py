"""Conversation service for business logic."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from supabase import Client

from src.lib.supabase.client import get_supabase_user_client

from .schema import ConversationCreate, ConversationUpdate, MessageCreate


class ConversationService:
    """Service for managing conversations."""

    def __init__(self, supabase: Client = Depends(get_supabase_user_client)):
        self.supabase = supabase

    async def list_for_user(self, tenant_id: str) -> list[dict]:
        """List all conversations visible to the current user via RLS."""
        result = (
            self.supabase
            .table("conversations")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("updated_at", desc=True)
            .execute()
        )
        return result.data

    async def get_by_id(self, tenant_id: str, conversation_id: str) -> dict | None:
        """Get a conversation by ID."""
        result = (
            self.supabase
            .table("conversations")
            .select("*")
            .eq("tenant_id", tenant_id)
            .eq("id", conversation_id)
            .maybe_single()
            .execute()
        )
        return result.data

    async def get_with_messages(self, tenant_id: str, conversation_id: str) -> dict | None:
        """Get a conversation with all its messages."""
        result = (
            self.supabase
            .table("conversations")
            .select("*, messages(*)")
            .eq("tenant_id", tenant_id)
            .eq("id", conversation_id)
            .maybe_single()
            .execute()
        )
        return result.data

    async def create(self, tenant_id: str, data: ConversationCreate, user_id: str) -> dict:
        """Create a new conversation."""
        result = (
            self.supabase
            .table("conversations")
            .insert({
                "title": data.title,
                "tenant_id": tenant_id,
                "owner_user_id": user_id,
            })
            .execute()
        )
        return result.data[0]

    async def update(self, tenant_id: str, conversation_id: str, data: ConversationUpdate) -> dict:
        """Update an existing conversation."""
        update_data = {}
        if data.title is not None:
            update_data["title"] = data.title

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )

        result = (
            self.supabase
            .table("conversations")
            .update(update_data)
            .eq("tenant_id", tenant_id)
            .eq("id", conversation_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        return result.data[0]

    async def delete(self, tenant_id: str, conversation_id: str) -> bool:
        """Delete a conversation by ID."""
        result = (
            self.supabase
            .table("conversations")
            .delete()
            .eq("tenant_id", tenant_id)
            .eq("id", conversation_id)
            .execute()
        )
        return len(result.data) > 0

    async def add_message(self, conversation_id: str, data: MessageCreate) -> dict:
        """Add a message to a conversation."""
        result = (
            self.supabase
            .table("messages")
            .insert({
                "conversation_id": conversation_id,
                "sender": data.sender,
                "content": data.content,
            })
            .execute()
        )
        return result.data[0]

    async def get_messages(self, conversation_id: str) -> list[dict]:
        """Get all messages for a conversation."""
        result = (
            self.supabase
            .table("messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("timestamp")
            .execute()
        )
        return result.data
