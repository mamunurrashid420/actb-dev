"""Tests for users API routes."""

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from src.app.api.users.service import UserService


def _profile() -> dict:
    return {
        "id": "profile-1",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "full_name": "Test User",
        "company_email": "test@company.com",
        "notes": "notes",
        "avatar_url": None,
        "department": None,
        "position": None,
        "phone": None,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


def test_get_current_user_info(client: TestClient):
    mock_service = MagicMock()
    mock_service.get_current_user_info = AsyncMock(
        return_value={
            "id": "test-user-id",
            "email": "test@example.com",
            "created_at": "2024-01-01T00:00:00Z",
        }
    )
    client.app.dependency_overrides[UserService] = lambda: mock_service

    response = client.get("/users/me")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-user-id"
    assert data["email"] == "test@example.com"


def test_get_my_profile_not_found(client: TestClient):
    mock_service = MagicMock()
    mock_service.get_profile_self = AsyncMock(return_value=None)
    client.app.dependency_overrides[UserService] = lambda: mock_service

    response = client.get("/users/me/profile")

    assert response.status_code == 404
    assert response.json()["detail"] == "Profile not found"


def test_get_my_profile(client: TestClient):
    mock_service = MagicMock()
    mock_service.get_profile_self = AsyncMock(return_value=_profile())
    client.app.dependency_overrides[UserService] = lambda: mock_service

    response = client.get("/users/me/profile")

    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


def test_update_my_profile(client: TestClient):
    updated = {**_profile(), "first_name": "Updated"}
    mock_service = MagicMock()
    mock_service.update_profile_self = AsyncMock(return_value=updated)
    client.app.dependency_overrides[UserService] = lambda: mock_service

    response = client.put("/users/me/profile", json={"first_name": "Updated"})

    assert response.status_code == 200
    assert response.json()["first_name"] == "Updated"

