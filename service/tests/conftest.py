"""Pytest configuration and fixtures."""

import os
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest

# Set environment variables before importing app
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")

from fastapi.testclient import TestClient

from src.app.main import app
from src.lib.auth.dependencies import get_current_user
from src.lib.supabase.client import (
    get_supabase_admin_client,
    get_supabase_client,
    get_supabase_service_client,
    get_supabase_user_client,
    get_supabase_user_client_optional,
)


@pytest.fixture
def mock_user() -> MagicMock:
    """Create a mock authenticated user."""
    user = MagicMock()
    user.id = "test-user-id"
    user.email = "test@example.com"
    user.created_at = "2024-01-01T00:00:00Z"
    user.user_metadata = {"tenant_id": "test-tenant-id"}
    user.claims = {
        "sub": "test-user-id",
        "role": "app_admin",
        "is_app_admin": True,
    }
    return user


@pytest.fixture
def mock_supabase() -> MagicMock:
    """Create a mock Supabase client."""
    return MagicMock()


@pytest.fixture
def client(
    mock_user: MagicMock, mock_supabase: MagicMock
) -> Generator[TestClient, None, None]:
    """Create a test client with mocked dependencies."""

    async def override_get_current_user():
        return mock_user

    def override_get_supabase_client():
        return mock_supabase
    def override_get_supabase_admin_client():
        return mock_supabase
    def override_get_supabase_service_client():
        return None
    def override_get_supabase_user_client():
        return mock_supabase
    def override_get_supabase_user_client_optional():
        return mock_supabase

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_supabase_client] = override_get_supabase_client
    app.dependency_overrides[get_supabase_admin_client] = (
        override_get_supabase_admin_client
    )
    app.dependency_overrides[get_supabase_service_client] = (
        override_get_supabase_service_client
    )
    app.dependency_overrides[get_supabase_user_client] = (
        override_get_supabase_user_client
    )
    app.dependency_overrides[get_supabase_user_client_optional] = (
        override_get_supabase_user_client_optional
    )

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client() -> TestClient:
    """Create a test client without authentication override."""
    return TestClient(app)
