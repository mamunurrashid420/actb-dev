"""Service for tenant assets."""

from uuid import uuid4

from fastapi import Depends
from supabase import Client

from src.lib.api.errors import raise_for_supabase_error
from src.lib.storage import get_storage_provider
from src.lib.supabase.client import get_supabase_user_client


class TenantAssetService:
    """Service for tenant assets."""

    def __init__(self, supabase: Client = Depends(get_supabase_user_client)):
        self.supabase = supabase

    async def upload_asset(
        self,
        tenant_id: str,
        asset_type: str,
        file_name: str,
        content: bytes,
        content_type: str | None,
    ) -> dict:
        file_id = uuid4().hex
        storage_path = f"tenant/{tenant_id}/{asset_type}/{file_id}-{file_name}"
        storage = get_storage_provider(self.supabase)
        storage.upload(storage_path, content, content_type)

        result = (
            self.supabase.table("tenant_assets")
            .upsert(
                {
                    "tenant_id": tenant_id,
                    "asset_type": asset_type,
                    "storage_path": storage_path,
                    "file_name": file_name,
                    "file_size": len(content),
                    "content_type": content_type,
                }
            )
            .execute()
        )
        raise_for_supabase_error(result, "Failed to save asset")
        return result.data[0]
