"""Dashboard API routes."""

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from src.lib.auth.dependencies import get_current_user

from .schema import (
    DashboardCreate,
    DashboardResponse,
    DashboardSearchResponse,
    DashboardShareCreate,
    DashboardShareResponse,
    DashboardShareUpdate,
    DashboardSharesResponse,
    DashboardUpdate,
    PublicShareUpdate,
    TenantShareUpdate,
)
from .service import DashboardService

router = APIRouter(prefix="/tenants/{tenant_id}/dashboards", tags=["dashboards"])


@router.get("/search", response_model=list[DashboardSearchResponse])
async def search_dashboards(
    tenant_id: str,
    q: str = Query(..., min_length=1, max_length=500),
    mode: str = Query("keyword", pattern="^(keyword|semantic|hybrid)$"),
    limit: int = Query(20, ge=1, le=200),
    _user=Depends(get_current_user),
    service: DashboardService = Depends(),
):
    """Search dashboards via RPC (RLS enforced)."""
    return await service.search(tenant_id, q, mode, limit)


@router.get("", response_model=list[DashboardResponse])
async def list_dashboards(
    tenant_id: str,
    _user=Depends(get_current_user),
    service: DashboardService = Depends(),
):
    """List dashboards visible to the current user."""
    return await service.list_dashboards(tenant_id)


@router.post("", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard(
    tenant_id: str,
    data: DashboardCreate,
    user=Depends(get_current_user),
    service: DashboardService = Depends(),
):
    """Create a new dashboard."""
    return await service.create_dashboard(tenant_id, user.id, data)


@router.get("/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    tenant_id: str,
    dashboard_id: str,
    _user=Depends(get_current_user),
    service: DashboardService = Depends(),
):
    """Get a dashboard by ID."""
    dashboard = await service.get_dashboard(tenant_id, dashboard_id)
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard not found",
        )
    return dashboard


@router.put("/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(
    tenant_id: str,
    dashboard_id: str,
    data: DashboardUpdate,
    _user=Depends(get_current_user),
    service: DashboardService = Depends(),
):
    """Update an existing dashboard."""
    return await service.update_dashboard(tenant_id, dashboard_id, data)


@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard(
    tenant_id: str,
    dashboard_id: str,
    _user=Depends(get_current_user),
    service: DashboardService = Depends(),
):
    """Delete a dashboard."""
    deleted = await service.delete_dashboard(tenant_id, dashboard_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard not found",
        )
    return None


@router.get("/{dashboard_id}/shares", response_model=DashboardSharesResponse)
async def list_dashboard_shares(
    tenant_id: str,
    dashboard_id: str,
    _user=Depends(get_current_user),
    service: DashboardService = Depends(),
):
    """List shares for a dashboard."""
    user_shares = await service.list_shares(dashboard_id)
    share_state = await service.get_share_state(tenant_id, dashboard_id)
    if not share_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard not found",
        )
    tenant_share = None
    if share_state.get("share_tenant_role"):
        tenant_share = {"role": share_state.get("share_tenant_role")}
    public_share = {
        "enabled": bool(share_state.get("share_public_enabled")),
        "token": share_state.get("share_public_token"),
        "expires_at": share_state.get("share_public_expires_at"),
    }
    return {
        "user_shares": user_shares,
        "tenant_share": tenant_share,
        "public_share": public_share,
    }


@router.post(
    "/{dashboard_id}/shares",
    response_model=DashboardShareResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_dashboard_share(
    tenant_id: str,
    dashboard_id: str,
    data: DashboardShareCreate,
    user=Depends(get_current_user),
    service: DashboardService = Depends(),
):
    """Add a user share to a dashboard."""
    return await service.create_share(dashboard_id, user.id, data)


@router.put("/{dashboard_id}/shares/{user_id}", response_model=DashboardShareResponse)
async def update_dashboard_share(
    tenant_id: str,
    dashboard_id: str,
    user_id: str,
    data: DashboardShareUpdate,
    _user=Depends(get_current_user),
    service: DashboardService = Depends(),
):
    """Update a user's share role."""
    return await service.update_share(dashboard_id, user_id, data)


@router.delete("/{dashboard_id}/shares/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard_share(
    tenant_id: str,
    dashboard_id: str,
    user_id: str,
    _user=Depends(get_current_user),
    service: DashboardService = Depends(),
):
    """Remove a user's share."""
    await service.delete_share(dashboard_id, user_id)
    return None


@router.put("/{dashboard_id}/tenant-share", response_model=DashboardResponse)
async def set_tenant_share(
    tenant_id: str,
    dashboard_id: str,
    data: TenantShareUpdate,
    _user=Depends(get_current_user),
    service: DashboardService = Depends(),
):
    """Set tenant-wide share role."""
    return await service.set_tenant_share(tenant_id, dashboard_id, data)


@router.delete("/{dashboard_id}/tenant-share", response_model=DashboardResponse)
async def clear_tenant_share(
    tenant_id: str,
    dashboard_id: str,
    _user=Depends(get_current_user),
    service: DashboardService = Depends(),
):
    """Remove tenant-wide sharing."""
    return await service.clear_tenant_share(tenant_id, dashboard_id)


@router.post("/{dashboard_id}/public-link", response_model=DashboardResponse)
async def enable_public_share(
    tenant_id: str,
    dashboard_id: str,
    data: PublicShareUpdate | None = Body(default=None),
    _user=Depends(get_current_user),
    service: DashboardService = Depends(),
):
    """Enable public sharing for a dashboard."""
    return await service.enable_public_share(
        tenant_id, dashboard_id, data or PublicShareUpdate()
    )


@router.delete("/{dashboard_id}/public-link", response_model=DashboardResponse)
async def disable_public_share(
    tenant_id: str,
    dashboard_id: str,
    _user=Depends(get_current_user),
    service: DashboardService = Depends(),
):
    """Disable public sharing for a dashboard."""
    return await service.disable_public_share(tenant_id, dashboard_id)
