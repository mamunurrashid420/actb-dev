"""Tenant API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from src.app.role_permissions import ROLE_PERMISSIONS
from src.lib.api.errors import raise_for_supabase_error
from src.lib.auth.dependencies import get_current_user, require_tenant_member
from src.lib.supabase.client import get_supabase_user_client
from src.lib.api.pagination import PaginatedResponse, PaginationParams

from .schema import (
    TenantMemberCreate,
    TenantMemberResponse,
    TenantMemberUpdate,
    TenantPermissionsResponse,
    TenantResponse,
)
from .service import TenantService

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def list_tenants(
    _user=Depends(get_current_user),
    pagination: PaginationParams = Depends(),
    search: str | None = Query(None, min_length=1, max_length=200),
    status: str | None = Query(None),
    service: TenantService = Depends(),
):
    """List all tenants accessible to the current user."""
    items, total = await service.list_for_user(
        limit=pagination.limit,
        offset=pagination.offset,
        search=search,
        status=status,
    )
    return {
        "items": items,
        "total": total,
        "limit": pagination.limit,
        "offset": pagination.offset,
    }


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    _user=Depends(get_current_user),
    service: TenantService = Depends(),
):
    """Get a tenant by ID."""
    tenant = await service.get_for_user(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    return tenant


@router.get("/{tenant_id}/me/permissions", response_model=TenantPermissionsResponse)
async def get_my_permissions(
    tenant_id: str,
    user=Depends(get_current_user),
    supabase: Client = Depends(get_supabase_user_client),
):
    """Return the current user's app role and permissions for a tenant."""
    result = (
        supabase
        .table("tenant_users")
        .select("role")
        .eq("tenant_id", tenant_id)
        .eq("user_id", user.id)
        .eq("status", "active")
        .maybe_single()
        .execute()
    )
    raise_for_supabase_error(result, "Failed to load tenant role")
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this tenant",
        )
    role = result.data.get("role")
    return {
        "app_role": role,
        "app_permissions": ROLE_PERMISSIONS.get(role, []),
    }


# Member management routes


@router.get("/{tenant_id}/members", response_model=list[TenantMemberResponse])
async def list_members(
    tenant_id: str,
    _member=Depends(require_tenant_member),
    service: TenantService = Depends(),
):
    """List all members of a tenant."""
    return await service.list_members(tenant_id)


@router.post(
    "/{tenant_id}/members",
    response_model=TenantMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    tenant_id: str,
    data: TenantMemberCreate,
    _member=Depends(require_tenant_member),
    service: TenantService = Depends(),
):
    """Add a member to a tenant."""
    return await service.add_member(tenant_id, data)


@router.put("/{tenant_id}/members/{user_id}", response_model=TenantMemberResponse)
async def update_member(
    tenant_id: str,
    user_id: str,
    data: TenantMemberUpdate,
    _member=Depends(require_tenant_member),
    service: TenantService = Depends(),
):
    """Update a tenant member."""
    return await service.update_member(tenant_id, user_id, data)


@router.delete("/{tenant_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    tenant_id: str,
    user_id: str,
    _member=Depends(require_tenant_member),
    service: TenantService = Depends(),
):
    """Remove a member from a tenant."""
    removed = await service.remove_member(tenant_id, user_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )
