"""Tests for tenant connections API routes."""

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

TENANT_ID = "tenant-1"


def _connection() -> dict:
    return {
        "id": "conn-1",
        "tenant_id": TENANT_ID,
        "name": "primary-postgres",
        "type": "postgres",
        "is_active": True,
        "config": {"host": "localhost", "port": 5432, "database": "db"},
        "last_test_status": "success",
        "last_tested_at": "2024-01-01T00:00:00Z",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


def test_list_connections(client: TestClient):
    from src.app.api.tenant_connections.route import (
        TenantConnectionService as RouteTenantConnectionService,
    )

    mock_service = MagicMock()
    mock_service.list_connections = AsyncMock(return_value=([_connection()], 1))
    client.app.dependency_overrides[RouteTenantConnectionService] = lambda: mock_service

    response = client.get(f"/tenants/{TENANT_ID}/connections")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


def test_get_connection_not_found(client: TestClient):
    from src.app.api.tenant_connections.route import (
        TenantConnectionService as RouteTenantConnectionService,
    )

    mock_service = MagicMock()
    mock_service.get = AsyncMock(return_value=None)
    client.app.dependency_overrides[RouteTenantConnectionService] = lambda: mock_service

    response = client.get(f"/tenants/{TENANT_ID}/connections/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Connection not found"


def test_create_connection(client: TestClient):
    from src.app.api.tenant_connections.route import (
        TenantConnectionService as RouteTenantConnectionService,
    )

    mock_service = MagicMock()
    mock_service.create = AsyncMock(return_value=_connection())
    client.app.dependency_overrides[RouteTenantConnectionService] = lambda: mock_service

    response = client.post(
        f"/tenants/{TENANT_ID}/connections",
        json={
            "name": "primary-postgres",
            "type": "postgres",
            "config": {"host": "localhost", "port": 5432, "database": "db"},
            "is_active": True,
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == "conn-1"


def test_update_connection(client: TestClient):
    from src.app.api.tenant_connections.route import (
        TenantConnectionService as RouteTenantConnectionService,
    )

    mock_service = MagicMock()
    mock_service.get = AsyncMock(return_value=_connection())
    mock_service.update = AsyncMock(return_value={**_connection(), "name": "updated"})
    client.app.dependency_overrides[RouteTenantConnectionService] = lambda: mock_service

    response = client.put(
        f"/tenants/{TENANT_ID}/connections/conn-1",
        json={"name": "updated"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "updated"


def test_test_connection(client: TestClient):
    from src.app.api.tenant_connections.route import (
        TenantConnectionService as RouteTenantConnectionService,
    )

    mock_service = MagicMock()
    mock_service.get = AsyncMock(return_value=_connection())
    mock_service.test_connection = AsyncMock(
        return_value={"status": "success", "details": {"latency_ms": 5}}
    )
    client.app.dependency_overrides[RouteTenantConnectionService] = lambda: mock_service

    response = client.post(f"/tenants/{TENANT_ID}/connections/conn-1/test")

    assert response.status_code == 200
    assert response.json()["status"] == "success"

