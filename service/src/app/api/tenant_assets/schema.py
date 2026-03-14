"""Schemas for tenant assets."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class TenantAssetResponse(BaseModel):
    id: str
    tenant_id: str
    asset_type: Literal["logo", "markdown"]
    storage_path: str
    file_name: str | None
    file_size: int | None
    content_type: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
