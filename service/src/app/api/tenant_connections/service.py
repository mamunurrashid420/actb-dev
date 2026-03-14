"""Service for tenant database connections."""

from fastapi import Depends, HTTPException, status
from supabase import Client

from src.lib.api.errors import raise_for_supabase_error
from src.lib.db.connection_test import test_connection
from src.lib.security.encryption import decrypt_payload, encrypt_payload
from src.lib.supabase.client import get_supabase_user_client

from .schema import TenantConnectionCreate, TenantConnectionUpdate


class TenantConnectionService:
    """Service for tenant database connection operations."""

    def __init__(self, supabase: Client = Depends(get_supabase_user_client)):
        self.supabase = supabase

    def _serialize_config(self, config: dict) -> dict:
        metadata = {k: v for k, v in config.items() if k != "password"}
        encrypted = encrypt_payload(config)
        return {"encrypted": True, "ciphertext": encrypted, "metadata": metadata}

    def _deserialize_config(self, stored: dict) -> dict:
        if stored.get("encrypted"):
            metadata = stored.get("metadata") or {}
            return metadata
        return stored

    def _decrypt_config(self, stored: dict) -> dict:
        if stored.get("encrypted"):
            return decrypt_payload(stored.get("ciphertext", ""))
        return stored

    async def list_connections(
        self, tenant_id: str, limit: int, offset: int
    ) -> tuple[list[dict], int]:
        result = (
            self.supabase.table("tenant_database_connections")
            .select("*", count="exact")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to list connections")
        for row in result.data or []:
            row["config"] = self._deserialize_config(row.get("connection_config") or {})
            row.pop("connection_config", None)
        total = result.count or 0
        return result.data, total

    async def get(self, connection_id: str) -> dict | None:
        result = (
            self.supabase.table("tenant_database_connections")
            .select("*")
            .eq("id", connection_id)
            .maybe_single()
            .execute()
        )
        raise_for_supabase_error(result, "Failed to fetch connection")
        if result.data:
            result.data["config"] = self._deserialize_config(
                result.data.get("connection_config") or {}
            )
            result.data.pop("connection_config", None)
        return result.data

    async def create(self, tenant_id: str, data: TenantConnectionCreate) -> dict:
        stored_config = self._serialize_config(data.config.model_dump())
        result = (
            self.supabase.table("tenant_database_connections")
            .insert(
                {
                    "tenant_id": tenant_id,
                    "name": data.name,
                    "type": data.type,
                    "connection_config": stored_config,
                    "is_active": data.is_active,
                }
            )
            .execute()
        )
        raise_for_supabase_error(result, "Failed to create connection")
        created = result.data[0]
        created["config"] = self._deserialize_config(
            created.get("connection_config") or {}
        )
        created.pop("connection_config", None)
        return created

    async def update(self, connection_id: str, data: TenantConnectionUpdate) -> dict:
        update_data = {}
        if data.name is not None:
            update_data["name"] = data.name
        if data.is_active is not None:
            update_data["is_active"] = data.is_active
        if data.config is not None:
            update_data["connection_config"] = self._serialize_config(
                data.config.model_dump()
            )
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )
        result = (
            self.supabase.table("tenant_database_connections")
            .update(update_data)
            .eq("id", connection_id)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to update connection")
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connection not found",
            )
        updated = result.data[0]
        updated["config"] = self._deserialize_config(
            updated.get("connection_config") or {}
        )
        updated.pop("connection_config", None)
        return updated

    async def delete(self, connection_id: str) -> None:
        result = (
            self.supabase.table("tenant_database_connections")
            .delete()
            .eq("id", connection_id)
            .execute()
        )
        raise_for_supabase_error(result, "Failed to delete connection")
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connection not found",
            )

    async def test_connection(self, connection_id: str) -> dict:
        result = (
            self.supabase.table("tenant_database_connections")
            .select("id, type, connection_config")
            .eq("id", connection_id)
            .maybe_single()
            .execute()
        )
        raise_for_supabase_error(result, "Failed to load connection")
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connection not found",
            )

        stored_config = result.data.get("connection_config") or {}
        config = self._decrypt_config(stored_config)
        status_value = "success"
        details = None
        try:
            test_connection(result.data["type"], config)
        except Exception as exc:
            status_value = "failed"
            details = {"error": str(exc)}

        update_result = self.supabase.rpc(
            "update_connection_test_status",
            {"connection_id": connection_id, "status": status_value, "details": details},
        ).execute()
        raise_for_supabase_error(update_result, "Failed to update test status")
        return {"status": status_value, "details": details}
