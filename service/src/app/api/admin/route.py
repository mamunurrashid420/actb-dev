from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from src.lib.auth.dependencies import require_superadmin
from src.app.api.admin.schema import (
    CreateConnectionRequest,
    CreateTenantRequest,
    CreateUserRequest,
    InviteUserRequest,
    ResendInviteRequest,
    TenantStatusRequest,
    TestConnectionRequest,
    UpdateConnectionRequest,
    UpdateTenantRequest,
    UpdateUserRequest,
)
from src.app.api.admin.service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/tenants")
async def list_tenants(
    page: int = 1,
    limit: int = 50,
    search: str | None = None,
    status_value: str | None = None,
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    return await service.list_tenants(page, limit, search, status_value)


@router.post("/tenants", status_code=status.HTTP_201_CREATED)
async def create_tenant(
    data: CreateTenantRequest,
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    return {"tenant": await service.create_tenant(data)}


@router.get("/tenants/{tenant_id}")
async def get_tenant(
    tenant_id: str,
    include_assets_content: bool = False,
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    return {
        "tenant": await service.get_tenant(
            tenant_id, include_assets_content=include_assets_content
        )
    }


@router.put("/tenants/{tenant_id}")
async def update_tenant(
    tenant_id: str,
    data: UpdateTenantRequest,
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    return {"tenant": await service.update_tenant(tenant_id, data)}


@router.put("/tenants/{tenant_id}/status")
async def update_tenant_status(
    tenant_id: str,
    data: TenantStatusRequest,
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    return {"tenant": await service.update_tenant_status(tenant_id, data.status)}


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    await service.delete_tenant(tenant_id)
    return None


@router.get("/tenants/{tenant_id}/assets")
async def list_assets(
    tenant_id: str,
    include_content: bool = False,
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    return {"assets": await service.list_assets(tenant_id, include_content)}


@router.post("/tenants/{tenant_id}/assets", status_code=status.HTTP_201_CREATED)
async def upload_asset(
    tenant_id: str,
    asset_type: str = Form(...),
    file: UploadFile = File(...),
    file_name: str | None = Form(None),
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    content = await file.read()
    resolved_name = file_name or file.filename or "upload"
    return {
        "asset": await service.upload_asset(
            tenant_id, asset_type, resolved_name, content, file.content_type
        )
    }


@router.get("/tenants/{tenant_id}/connections")
async def list_connections(
    tenant_id: str,
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    return {"connections": await service.list_connections(tenant_id)}


@router.post("/connections/test")
async def test_connection_config(
    data: TestConnectionRequest,
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    await service.test_connection_config(data)
    return {"success": True}


@router.post("/connections", status_code=status.HTTP_201_CREATED)
async def create_connection(
    data: CreateConnectionRequest,
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    return {"connection": await service.create_connection(data)}


@router.put("/connections/{connection_id}")
async def update_connection(
    connection_id: str,
    data: UpdateConnectionRequest,
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    return {"connection": await service.update_connection(connection_id, data)}


@router.delete("/connections/{connection_id}")
async def delete_connection(
    connection_id: str,
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    await service.delete_connection(connection_id)
    return {"success": True}


@router.post("/connections/{connection_id}/test")
async def test_existing_connection(
    connection_id: str,
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    await service.test_existing_connection(connection_id)
    return {"success": True}


@router.get("/tenants/{tenant_id}/members")
async def list_members(
    tenant_id: str,
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    return {"members": await service.list_members(tenant_id)}


@router.get("/users")
async def list_users(
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    return await service.list_users()


@router.post("/users/invite")
async def invite_user(
    data: InviteUserRequest,
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    return await service.invite_user(data)


@router.post("/users/resend-invite")
async def resend_invite(
    data: ResendInviteRequest,
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    return await service.resend_invite(data)


@router.post("/users")
async def create_user(
    data: CreateUserRequest,
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    return await service.create_user(data)


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    data: UpdateUserRequest,
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    return await service.update_user(user_id, data)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    _admin=Depends(require_superadmin),
    service: AdminService = Depends(),
):
    await service.delete_user(user_id)
    return {"success": True}
