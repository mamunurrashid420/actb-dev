"""Tests for tenants API routes."""

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

TENANT_ID = "tenant-1"


def _tenant() -> dict:
    return {
        "id": TENANT_ID,
        "name": "Acme",
        "description": "Acme tenant",
        "status": "active",
        "logo_url": None,
        "document_name": None,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


def _member() -> dict:
    return {
        "id": "member-1",
        "tenant_id": TENANT_ID,
        "user_id": "user-1",
        "role": "admin",
        "status": "active",
        "invited_at": None,
        "accepted_at": None,
        "created_at": "2024-01-01T00:00:00Z",
        "email": "user@example.com",
        "full_name": "User One",
        "avatar_url": None,
    }


def test_list_tenants(client: TestClient):
    from src.app.api.tenants.route import TenantService as RouteTenantService

    mock_service = MagicMock()
    mock_service.list_for_user = AsyncMock(return_value=([_tenant()], 1))
    client.app.dependency_overrides[RouteTenantService] = lambda: mock_service

    response = client.get("/tenants")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == TENANT_ID


def test_get_tenant_not_found(client: TestClient):
    from src.app.api.tenants.route import TenantService as RouteTenantService

    mock_service = MagicMock()
    mock_service.get_for_user = AsyncMock(return_value=None)
    client.app.dependency_overrides[RouteTenantService] = lambda: mock_service

    response = client.get(f"/tenants/{TENANT_ID}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Tenant not found"


def test_get_my_permissions(client: TestClient, mock_supabase: MagicMock):
    result = (
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value
    )
    result.data = {"role": "admin"}
    result.error = None

    response = client.get(f"/tenants/{TENANT_ID}/me/permissions")

    assert response.status_code == 200
    data = response.json()
    assert data["app_role"] == "admin"
    assert isinstance(data["app_permissions"], list)


def test_list_members(client: TestClient):
    from src.app.api.tenants.route import TenantService as RouteTenantService

    mock_service = MagicMock()
    mock_service.list_members = AsyncMock(return_value=[_member()])
    client.app.dependency_overrides[RouteTenantService] = lambda: mock_service

    response = client.get(f"/tenants/{TENANT_ID}/members")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_add_member(client: TestClient):
    from src.app.api.tenants.route import TenantService as RouteTenantService

    mock_service = MagicMock()
    mock_service.add_member = AsyncMock(return_value=_member())
    client.app.dependency_overrides[RouteTenantService] = lambda: mock_service

    response = client.post(
        f"/tenants/{TENANT_ID}/members",
        json={"user_id": "user-1", "role": "admin", "status": "active"},
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == "user-1"
