"""Tenant schemas for request/response validation."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class TenantResponse(BaseModel):
    """Schema for tenant response."""

    id: str
    name: str
    description: str | None
    status: Literal["active", "inactive"]
    logo_url: str | None
    document_name: str | None
    logo_signed_url: str | None = None
    document_signed_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantMemberResponse(BaseModel):
    """Schema for tenant member response."""

    id: str
    tenant_id: str
    user_id: str
    role: str
    status: Literal["active", "inactive"]
    invited_at: datetime | None
    accepted_at: datetime | None
    created_at: datetime
    email: str | None = None
    full_name: str | None = None
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TenantMemberCreate(BaseModel):
    """Schema for adding a member to a tenant."""

    user_id: str
    role: Literal["superadmin", "admin", "creator", "viewer"] = "viewer"
    status: Literal["active", "inactive"] = "active"


class TenantMemberUpdate(BaseModel):
    """Schema for updating a tenant member."""

    role: Literal["superadmin", "admin", "creator", "viewer"] | None = None
    status: Literal["active", "inactive"] | None = None


class TenantPermissionsResponse(BaseModel):
    """Schema for tenant-scoped app permissions."""

    app_role: str | None
    app_permissions: list[str]
