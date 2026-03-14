"""Public access routes."""

from fastapi import APIRouter, HTTPException, status

from src.app.api.dashboards.schema import DashboardResponse
from src.app.api.dashboards.service import PublicDashboardService

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/dashboards/{token}", response_model=DashboardResponse)
async def get_public_dashboard(token: str):
    """Access a public dashboard by token (no auth)."""
    service = PublicDashboardService(token)
    dashboard = await service.get_by_token()
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard not found",
        )
    return dashboard
