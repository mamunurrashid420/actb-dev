"""Dashboard service for business logic."""

from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, status
from supabase import Client

from src.lib.api.errors import raise_for_supabase_error
from src.lib.embeddings import embed_query
from src.lib.supabase.client import create_supabase_anon_client, get_supabase_user_client

from .schema import (
    DashboardCreate,
    DashboardShareCreate,
    DashboardShareUpdate,
    DashboardUpdate,
    PublicShareUpdate,
    TenantShareUpdate,
)


class DashboardService:
    """Service for dashboard operations."""

    def __init__(self, supabase: Client = Depends(get_supabase_user_client)):
        self.supabase = supabase
        self.table = "dashboards"
        self.view = "my_dashboards"
        self.shares_table = "dashboard_user_shares"

    async def list_dashboards(self, tenant_id: str) -> list[dict]:
        result = (
            self.supabase
            .table(self.view)
            .select("*")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to list dashboards")
        return result.data or []

    async def get_dashboard(self, tenant_id: str, dashboard_id: str) -> dict | None:
        result = (
            self.supabase
            .table(self.view)
            .select("*")
            .eq("tenant_id", tenant_id)
            .eq("id", dashboard_id)
            .maybe_single()
            .execute()
        )
        raise_for_supabase_error(result, "Failed to fetch dashboard")
        return result.data

    async def create_dashboard(
        self, tenant_id: str, owner_user_id: str, data: DashboardCreate
    ) -> dict:
        result = (
            self.supabase
            .table(self.table)
            .insert(
                {
                    "tenant_id": tenant_id,
                    "owner_user_id": owner_user_id,
                    "title": data.title,
                    "description": data.description,
                }
            )
            .execute()
        )
        raise_for_supabase_error(result, "Failed to create dashboard")
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not created",
            )
        return result.data[0]

    async def update_dashboard(
        self, tenant_id: str, dashboard_id: str, data: DashboardUpdate
    ) -> dict:
        update_data = {}
        if data.title is not None:
            update_data["title"] = data.title
        if data.description is not None:
            update_data["description"] = data.description

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )

        result = (
            self.supabase
            .table(self.table)
            .update(update_data)
            .eq("tenant_id", tenant_id)
            .eq("id", dashboard_id)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to update dashboard")
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not found",
            )
        return result.data[0]

    async def delete_dashboard(self, tenant_id: str, dashboard_id: str) -> bool:
        result = (
            self.supabase
            .table(self.table)
            .delete()
            .eq("tenant_id", tenant_id)
            .eq("id", dashboard_id)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to delete dashboard")
        return bool(result.data)

    async def list_shares(self, dashboard_id: str) -> list[dict]:
        result = (
            self.supabase
            .table(self.shares_table)
            .select("user_id, role, created_at")
            .eq("dashboard_id", dashboard_id)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to list dashboard shares")
        return result.data or []

    async def get_share_state(self, tenant_id: str, dashboard_id: str) -> dict | None:
        result = (
            self.supabase
            .table(self.table)
            .select(
                "share_tenant_role, share_public_enabled, share_public_token, share_public_expires_at"
            )
            .eq("tenant_id", tenant_id)
            .eq("id", dashboard_id)
            .maybe_single()
            .execute()
        )
        raise_for_supabase_error(result, "Failed to fetch dashboard share state")
        return result.data

    async def create_share(
        self, dashboard_id: str, created_by: str, data: DashboardShareCreate
    ) -> dict:
        result = (
            self.supabase
            .table(self.shares_table)
            .insert(
                {
                    "dashboard_id": dashboard_id,
                    "user_id": data.user_id,
                    "role": data.role,
                    "created_by": created_by,
                }
            )
            .execute()
        )
        raise_for_supabase_error(result, "Failed to create dashboard share")
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Share not created",
            )
        return result.data[0]

    async def update_share(
        self, dashboard_id: str, user_id: str, data: DashboardShareUpdate
    ) -> dict:
        result = (
            self.supabase
            .table(self.shares_table)
            .update({"role": data.role})
            .eq("dashboard_id", dashboard_id)
            .eq("user_id", user_id)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to update dashboard share")
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Share not found",
            )
        return result.data[0]

    async def delete_share(self, dashboard_id: str, user_id: str) -> None:
        result = (
            self.supabase
            .table(self.shares_table)
            .delete()
            .eq("dashboard_id", dashboard_id)
            .eq("user_id", user_id)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to delete dashboard share")
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Share not found",
            )

    async def set_tenant_share(
        self, tenant_id: str, dashboard_id: str, data: TenantShareUpdate
    ) -> dict:
        result = (
            self.supabase
            .table(self.table)
            .update({"share_tenant_role": data.role})
            .eq("tenant_id", tenant_id)
            .eq("id", dashboard_id)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to update tenant share")
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not found",
            )
        return result.data[0]

    async def clear_tenant_share(self, tenant_id: str, dashboard_id: str) -> dict:
        result = (
            self.supabase
            .table(self.table)
            .update({"share_tenant_role": None})
            .eq("tenant_id", tenant_id)
            .eq("id", dashboard_id)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to clear tenant share")
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not found",
            )
        return result.data[0]

    async def enable_public_share(
        self, tenant_id: str, dashboard_id: str, data: PublicShareUpdate
    ) -> dict:
        token = data.token or secrets.token_urlsafe(18)
        result = (
            self.supabase
            .table(self.table)
            .update(
                {
                    "share_public_enabled": True,
                    "share_public_token": token,
                    "share_public_expires_at": data.expires_at,
                }
            )
            .eq("tenant_id", tenant_id)
            .eq("id", dashboard_id)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to enable public sharing")
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not found",
            )
        return result.data[0]

    async def disable_public_share(self, tenant_id: str, dashboard_id: str) -> dict:
        result = (
            self.supabase
            .table(self.table)
            .update(
                {
                    "share_public_enabled": False,
                    "share_public_token": None,
                    "share_public_expires_at": None,
                }
            )
            .eq("tenant_id", tenant_id)
            .eq("id", dashboard_id)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to disable public sharing")
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not found",
            )
        return result.data[0]

    async def search(
        self,
        tenant_id: str,
        query: str,
        mode: str,
        limit: int,
    ) -> list[dict]:
        params: dict[str, object] = {
            "p_tenant_id": tenant_id,
            "p_query": query,
            "p_mode": mode,
            "p_limit": limit,
        }
        if mode in {"semantic", "hybrid"}:
            params["p_query_embedding"] = await embed_query(query)
        result = self.supabase.rpc("search_my_dashboards", params).execute()
        raise_for_supabase_error(result, "Failed to search dashboards")
        return result.data or []


class PublicDashboardService:
    """Service for public dashboard access."""

    def __init__(self, public_token: str):
        self.supabase = create_supabase_anon_client({"x-public-token": public_token})
        self.public_token = public_token

    async def get_by_token(self) -> dict | None:
        result = (
            self.supabase
            .table("dashboards")
            .select(
                "id, tenant_id, owner_user_id, title, description, created_at, updated_at"
            )
            .eq("share_public_enabled", True)
            .eq("share_public_token", self.public_token)
            .maybe_single()
            .execute()
        )
        raise_for_supabase_error(result, "Failed to load public dashboard")
        return result.data
