"""Tenant database connection routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.lib.api.pagination import PaginatedResponse, PaginationParams
from src.lib.auth.dependencies import require_tenant_member

from .schema import (
    TenantConnectionCreate,
    TenantConnectionResponse,
    TenantConnectionTestResponse,
    TenantConnectionUpdate,
)
from .service import TenantConnectionService

router = APIRouter(prefix="/tenants/{tenant_id}/connections", tags=["tenant-connections"])


@router.get("", response_model=PaginatedResponse)
async def list_connections(
    tenant_id: str,
    pagination: PaginationParams = Depends(),
    _member=Depends(require_tenant_member),
    service: TenantConnectionService = Depends(),
):
    items, total = await service.list_connections(
        tenant_id, pagination.limit, pagination.offset
    )
    return {
        "items": items,
        "total": total,
        "limit": pagination.limit,
        "offset": pagination.offset,
    }


@router.get("/{connection_id}", response_model=TenantConnectionResponse)
async def get_connection(
    tenant_id: str,
    connection_id: str,
    _member=Depends(require_tenant_member),
    service: TenantConnectionService = Depends(),
):
    connection = await service.get(connection_id)
    if not connection or connection["tenant_id"] != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )
    return connection


@router.post("", response_model=TenantConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    tenant_id: str,
    data: TenantConnectionCreate,
    _member=Depends(require_tenant_member),
    service: TenantConnectionService = Depends(),
):
    return await service.create(tenant_id, data)


@router.put("/{connection_id}", response_model=TenantConnectionResponse)
async def update_connection(
    tenant_id: str,
    connection_id: str,
    data: TenantConnectionUpdate,
    _member=Depends(require_tenant_member),
    service: TenantConnectionService = Depends(),
):
    connection = await service.get(connection_id)
    if not connection or connection["tenant_id"] != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )
    return await service.update(connection_id, data)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    tenant_id: str,
    connection_id: str,
    _member=Depends(require_tenant_member),
    service: TenantConnectionService = Depends(),
):
    connection = await service.get(connection_id)
    if not connection or connection["tenant_id"] != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )
    await service.delete(connection_id)
    return None


@router.post(
    "/{connection_id}/test",
    response_model=TenantConnectionTestResponse,
)
async def test_connection(
    tenant_id: str,
    connection_id: str,
    _member=Depends(require_tenant_member),
    service: TenantConnectionService = Depends(),
):
    connection = await service.get(connection_id)
    if not connection or connection["tenant_id"] != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )
    return await service.test_connection(connection_id)
