"""Tenant service for business logic."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from supabase import Client

from src.app.config import get_settings
from src.lib.api.errors import raise_for_supabase_error
from src.lib.supabase.client import get_supabase_user_client

from .schema import (
    TenantMemberCreate,
    TenantMemberUpdate,
)


class TenantService:
    """Service for managing tenants."""

    def __init__(self, supabase: Client = Depends(get_supabase_user_client)):
        self.supabase = supabase

    async def list_for_user(
        self,
        limit: int = 25,
        offset: int = 0,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[dict], int]:
        """List tenants visible to the current user via RLS."""
        query = (
            self.supabase
            .table("tenants")
            .select(
                "id, name, description, status, logo_url, document_name, created_at, updated_at",
                count="exact",
            )
        )
        if status:
            query = query.eq("status", status)
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.or_(f"name.ilike.{term},description.ilike.{term}")

        result = (
            query
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to list tenants")
        tenants = result.data or []
        if tenants:
            self._attach_signed_urls(tenants)
        total = result.count or 0
        return tenants, total

    async def get_for_user(self, tenant_id: str) -> dict | None:
        """Get a tenant by ID via RLS."""
        result = (
            self.supabase
            .table("tenants")
            .select(
                "id, name, description, status, logo_url, document_name, created_at, updated_at"
            )
            .eq("id", tenant_id)
            .maybe_single()
            .execute()
        )
        raise_for_supabase_error(result, "Failed to load tenant")
        tenant = result.data
        if not tenant:
            return None

        self._attach_signed_urls([tenant])
        return tenant

    def _attach_signed_urls(self, tenants: list[dict]) -> None:
        """Attach signed URLs for logo and knowledge base assets."""
        settings = get_settings()
        tenant_ids = [tenant["id"] for tenant in tenants]
        assets = (
            self.supabase
            .table("tenant_assets")
            .select("tenant_id, asset_type, storage_path")
            .in_("tenant_id", tenant_ids)
            .execute()
        )
        raise_for_supabase_error(assets, "Failed to load tenant assets")
        asset_map: dict[str, dict[str, str]] = {}
        for row in assets.data or []:
            asset_map.setdefault(row["tenant_id"], {})[row["asset_type"]] = row[
                "storage_path"
            ]

        for tenant in tenants:
            tenant_assets = asset_map.get(tenant["id"], {})
            logo_path = tenant.get("logo_url") or tenant_assets.get("logo")
            doc_path = tenant_assets.get("markdown")

            tenant["logo_signed_url"] = self._create_signed_url(logo_path, settings)
            tenant["document_signed_url"] = self._create_signed_url(doc_path, settings)

    def _create_signed_url(self, path: str | None, settings) -> str | None:
        if not path:
            return None
        try:
            result = (
                self.supabase
                .storage.from_(settings.storage_bucket)
                .create_signed_url(path, settings.storage_signed_url_ttl_seconds)
            )
            if isinstance(result, dict):
                return result.get("signedURL") or result.get("signedUrl")
            return getattr(result, "signed_url", None)
        except Exception:
            return None

    async def list_members(self, tenant_id: str) -> list[dict]:
        """List all members of a tenant."""
        result = (
            self.supabase
            .table("tenant_users")
            .select("id, tenant_id, user_id, role, status, invited_at, accepted_at, created_at")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to list tenant members")
        user_ids = [row["user_id"] for row in (result.data or [])]
        profiles = {}
        if user_ids:
            profile_result = (
                self.supabase
                .table("user_profiles")
                .select("id, email, full_name, avatar_url")
                .in_("id", user_ids)
                .execute()
            )
            raise_for_supabase_error(profile_result, "Failed to load user profiles")
            profiles = {row["id"]: row for row in (profile_result.data or [])}
        members = []
        for row in result.data or []:
            profile = profiles.get(row["user_id"], {})
            row["email"] = profile.get("email")
            row["full_name"] = profile.get("full_name")
            row["avatar_url"] = profile.get("avatar_url")
            members.append(row)
        return members

    async def add_member(self, tenant_id: str, data: TenantMemberCreate) -> dict:
        """Add a member to a tenant."""
        result = (
            self.supabase
            .table("tenant_users")
            .insert(
                {
                    "tenant_id": tenant_id,
                    "user_id": data.user_id,
                    "role": data.role,
                    "status": data.status,
                }
            )
            .execute()
        )
        raise_for_supabase_error(result, "Failed to add tenant member")
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not added",
            )
        return result.data[0]

    async def update_member(
        self, tenant_id: str, user_id: str, data: TenantMemberUpdate
    ) -> dict:
        """Update a tenant member."""
        update_data = {}
        if data.role is not None:
            update_data["role"] = data.role
        if data.status is not None:
            update_data["status"] = data.status

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )

        result = (
            self.supabase
            .table("tenant_users")
            .update(update_data)
            .eq("tenant_id", tenant_id)
            .eq("user_id", user_id)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to update tenant member")
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found",
            )
        return result.data[0]

    async def remove_member(self, tenant_id: str, user_id: str) -> bool:
        """Remove a member from a tenant."""
        result = (
            self.supabase
            .table("tenant_users")
            .delete()
            .eq("tenant_id", tenant_id)
            .eq("user_id", user_id)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to remove tenant member")
        return bool(result.data)
