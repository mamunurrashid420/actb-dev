"""Tests for tenant assets API routes."""

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

TENANT_ID = "tenant-1"


def _asset(asset_type: str, file_name: str) -> dict:
    return {
        "id": "asset-1",
        "tenant_id": TENANT_ID,
        "asset_type": asset_type,
        "storage_path": f"{asset_type}/{file_name}",
        "file_name": file_name,
        "file_size": 10,
        "content_type": "text/plain" if asset_type == "markdown" else "image/png",
        "created_at": "2024-01-01T00:00:00Z",
    }


def test_upload_logo(client: TestClient):
    from src.app.api.tenant_assets.route import TenantAssetService as RouteTenantAssetService

    mock_service = MagicMock()
    mock_service.upload_asset = AsyncMock(return_value=_asset("logo", "logo.png"))
    client.app.dependency_overrides[RouteTenantAssetService] = lambda: mock_service

    response = client.post(
        f"/tenants/{TENANT_ID}/assets/logo",
        files={"file": ("logo.png", b"png-bytes", "image/png")},
    )

    assert response.status_code == 201
    assert response.json()["asset_type"] == "logo"


def test_upload_logo_requires_filename(client: TestClient):
    response = client.post(
        f"/tenants/{TENANT_ID}/assets/logo",
        files={"file": ("", b"png-bytes", "image/png")},
    )

    assert response.status_code == 422


def test_upload_markdown(client: TestClient):
    from src.app.api.tenant_assets.route import TenantAssetService as RouteTenantAssetService

    mock_service = MagicMock()
    mock_service.upload_asset = AsyncMock(return_value=_asset("markdown", "notes.md"))
    client.app.dependency_overrides[RouteTenantAssetService] = lambda: mock_service

    response = client.post(
        f"/tenants/{TENANT_ID}/assets/markdown",
        files={"file": ("notes.md", b"# hello", "text/markdown")},
    )

    assert response.status_code == 201
    assert response.json()["asset_type"] == "markdown"
