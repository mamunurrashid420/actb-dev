from typing import Literal

from pydantic import BaseModel, EmailStr, Field

UserRole = Literal["superadmin", "admin", "creator", "viewer"]


class CreateTenantRequest(BaseModel):
    name: str
    description: str | None = None
    status: str | None = None
    branding: dict | None = None


class UpdateTenantRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    branding: dict | None = None
    context_metadata: dict | None = None


class TenantStatusRequest(BaseModel):
    status: str


class TenantResponse(BaseModel):
    id: str
    name: str
    description: str | None
    status: str
    created_at: str


class InviteUserRequest(BaseModel):
    email: EmailStr
    tenant_id: str | None = None
    role: UserRole | None = None


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str | None = None
    tenant_id: str | None = None
    role: UserRole | None = None


class UpdateUserRequest(BaseModel):
    full_name: str | None = None
    tenant_id: str | None = None
    role: UserRole | None = None


class ResendInviteRequest(BaseModel):
    email: EmailStr
    tenant_id: str | None = None


class TestConnectionRequest(BaseModel):
    type: str
    connection_config: dict


class CreateConnectionRequest(BaseModel):
    tenant_id: str
    name: str
    type: str
    connection_config: dict


class UpdateConnectionRequest(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    connection_config: dict | None = None
