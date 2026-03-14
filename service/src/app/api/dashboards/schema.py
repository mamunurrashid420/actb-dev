"""Dashboard schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, Field


class DashboardCreate(BaseModel):
    """Schema for creating a dashboard."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class DashboardUpdate(BaseModel):
    """Schema for updating a dashboard."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class DashboardResponse(BaseModel):
    """Schema for dashboard response."""

    id: str
    tenant_id: str | None = None
    owner_user_id: str | None = None
    title: str
    description: str | None = None
    share_tenant_role: str | None = None
    share_public_enabled: bool | None = None
    share_public_token: str | None = None
    share_public_expires_at: datetime | None = None
    effective_role: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DashboardShareCreate(BaseModel):
    """Schema for creating a dashboard share."""

    user_id: str
    role: str


class DashboardShareUpdate(BaseModel):
    """Schema for updating a dashboard share."""

    role: str


class DashboardShareResponse(BaseModel):
    """Schema for dashboard share response."""

    user_id: str
    role: str
    created_at: datetime | None = None


class TenantShareUpdate(BaseModel):
    """Schema for tenant-wide dashboard sharing."""

    role: str


class PublicShareUpdate(BaseModel):
    """Schema for public sharing updates."""

    expires_at: datetime | None = None
    token: str | None = None


class DashboardSharesResponse(BaseModel):
    """Schema for dashboard share details."""

    user_shares: list[DashboardShareResponse]
    tenant_share: dict | None
    public_share: dict | None


class DashboardSearchResponse(BaseModel):
    """Schema for dashboard search response."""

    id: str
    title: str
    description: str | None = None
    effective_role: str | None = None
    score: float | None = None
