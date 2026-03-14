"""User service for business logic."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from supabase import Client

from src.lib.auth.models import AuthContext
from src.lib.supabase.client import get_supabase_user_client

from .schema import UserProfileUpdate


class UserService:
    """Service for managing users."""

    def __init__(self, supabase: Client = Depends(get_supabase_user_client)):
        self.supabase = supabase

    async def get_current_user_info(self, user: AuthContext) -> dict:
        """Get current authenticated user info."""
        result = (
            self.supabase
            .table("user_profiles")
            .select("id, email, created_at")
            .eq("id", user.id)
            .maybe_single()
            .execute()
        )
        if result.data:
            return result.data
        return {"id": user.id, "email": user.email, "created_at": None}

    async def get_profile_self(self, user_id: str) -> dict | None:
        """Get current user's profile via RLS."""
        result = (
            self.supabase
            .table("user_profiles")
            .select("*")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        return result.data

    async def update_profile_self(self, user_id: str, data: UserProfileUpdate) -> dict:
        """Update current user's profile via RLS."""
        update_data = {}
        if data.first_name is not None:
            update_data["first_name"] = data.first_name
        if data.last_name is not None:
            update_data["last_name"] = data.last_name
        if data.full_name is not None:
            update_data["full_name"] = data.full_name
        if data.company_email is not None:
            update_data["company_email"] = data.company_email
        if data.notes is not None:
            update_data["notes"] = data.notes
        if data.avatar_url is not None:
            update_data["avatar_url"] = data.avatar_url
        if data.department is not None:
            update_data["department"] = data.department
        if data.position is not None:
            update_data["position"] = data.position
        if data.phone is not None:
            update_data["phone"] = data.phone
        if data.email is not None:
            update_data["email"] = data.email

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )

        result = (
            self.supabase
            .table("user_profiles")
            .update(update_data)
            .eq("id", user_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found",
            )

        return result.data[0]
