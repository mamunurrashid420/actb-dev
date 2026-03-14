"""Tests for auth API routes."""

from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException, status
from fastapi.testclient import TestClient


class TestLogin:
    """Tests for POST /auth/login endpoint."""

    def test_login_successful(self, client: TestClient):
        """Test successful login."""
        mock_response = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": "user-id",
                "email": "test@example.com",
            },
        }

        from src.app.api.auth.service import AuthService

        mock_service = MagicMock(spec=AuthService)
        mock_service.login = AsyncMock(return_value=mock_response)

        from src.app.api.auth.route import AuthService as RouteAuthService

        client.app.dependency_overrides[RouteAuthService] = lambda: mock_service

        response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "test-access-token"
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 3600
        assert data["user"]["email"] == "test@example.com"

    def test_login_invalid_credentials(self, client: TestClient):
        """Test login failure with invalid credentials."""
        from src.app.api.auth.service import AuthService

        mock_service = MagicMock(spec=AuthService)
        mock_service.login = AsyncMock(
            side_effect=HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        )

        from src.app.api.auth.route import AuthService as RouteAuthService

        client.app.dependency_overrides[RouteAuthService] = lambda: mock_service

        response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"


class TestSetPassword:
    """Tests for POST /auth/set-password endpoint."""

    def test_set_password_successful(self, client: TestClient):
        """Test successful password setting."""
        from src.app.api.auth.service import AuthService

        mock_service = MagicMock(spec=AuthService)
        mock_service.set_password = AsyncMock(return_value=None)

        from src.app.api.auth.route import AuthService as RouteAuthService

        client.app.dependency_overrides[RouteAuthService] = lambda: mock_service

        response = client.post(
            "/auth/set-password",
            json={"password": "newpassword123"},
        )

        assert response.status_code == 204

    def test_set_password_unauthenticated(self, unauthenticated_client: TestClient):
        """Test that unauthenticated users cannot set password."""
        response = unauthenticated_client.post(
            "/auth/set-password",
            json={"password": "newpassword123"},
        )

        assert response.status_code == 401


class TestGetAuthContext:
    """Tests for GET /auth/me endpoint."""

    def test_get_auth_context_successful(self, client: TestClient, mock_user: MagicMock):
        """Test getting authenticated user context."""
        response = client.get("/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == mock_user.id
        assert data["email"] == mock_user.email
        assert isinstance(data["claims"], dict)

    def test_get_auth_context_unauthenticated(self, unauthenticated_client: TestClient):
        """Test that unauthenticated users get 401."""
        response = unauthenticated_client.get("/auth/me")

        assert response.status_code == 401
