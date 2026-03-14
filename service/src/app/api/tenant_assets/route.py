"""Tenant asset routes."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from src.lib.auth.dependencies import require_tenant_member

from .schema import TenantAssetResponse
from .service import TenantAssetService

router = APIRouter(prefix="/tenants/{tenant_id}/assets", tags=["tenant-assets"])


@router.post("/logo", response_model=TenantAssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_logo(
    tenant_id: str,
    file: UploadFile = File(...),
    _member=Depends(require_tenant_member),
    service: TenantAssetService = Depends(),
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )
    content = await file.read()
    return await service.upload_asset(
        tenant_id, "logo", file.filename, content, file.content_type
    )


@router.post(
    "/markdown",
    response_model=TenantAssetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_markdown(
    tenant_id: str,
    file: UploadFile = File(...),
    _member=Depends(require_tenant_member),
    service: TenantAssetService = Depends(),
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )
    content = await file.read()
    return await service.upload_asset(
        tenant_id, "markdown", file.filename, content, file.content_type
    )
