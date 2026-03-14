"""Tests for conversation API routes."""

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

TENANT_ID = "tenant-1"


def _conversation() -> dict:
    return {
        "id": "conv-1",
        "tenant_id": TENANT_ID,
        "owner_user_id": "test-user-id",
        "title": "Q4 review",
        "share_tenant_role": None,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


def _message() -> dict:
    return {
        "id": "msg-1",
        "conversation_id": "conv-1",
        "sender": "user",
        "content": "hello",
        "timestamp": "2024-01-01T00:00:00Z",
    }


def test_list_conversations(client: TestClient):
    from src.app.api.conversations.route import ConversationService as RouteConversationService

    mock_service = MagicMock()
    mock_service.list_for_user = AsyncMock(return_value=[_conversation()])
    client.app.dependency_overrides[RouteConversationService] = lambda: mock_service

    response = client.get(f"/tenants/{TENANT_ID}/conversations")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "conv-1"


def test_get_conversation_not_found(client: TestClient):
    from src.app.api.conversations.route import ConversationService as RouteConversationService

    mock_service = MagicMock()
    mock_service.get_with_messages = AsyncMock(return_value=None)
    client.app.dependency_overrides[RouteConversationService] = lambda: mock_service

    response = client.get(f"/tenants/{TENANT_ID}/conversations/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


def test_create_conversation(client: TestClient):
    from src.app.api.conversations.route import ConversationService as RouteConversationService

    mock_service = MagicMock()
    mock_service.create = AsyncMock(return_value=_conversation())
    client.app.dependency_overrides[RouteConversationService] = lambda: mock_service

    response = client.post(
        f"/tenants/{TENANT_ID}/conversations",
        json={"title": "Q4 review"},
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Q4 review"


def test_add_message_requires_existing_conversation(client: TestClient):
    from src.app.api.conversations.route import ConversationService as RouteConversationService

    mock_service = MagicMock()
    mock_service.get_by_id = AsyncMock(return_value=None)
    client.app.dependency_overrides[RouteConversationService] = lambda: mock_service

    response = client.post(
        f"/tenants/{TENANT_ID}/conversations/missing/messages",
        json={"sender": "user", "content": "hello"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


def test_add_message(client: TestClient):
    from src.app.api.conversations.route import ConversationService as RouteConversationService

    mock_service = MagicMock()
    mock_service.get_by_id = AsyncMock(return_value=_conversation())
    mock_service.add_message = AsyncMock(return_value=_message())
    client.app.dependency_overrides[RouteConversationService] = lambda: mock_service

    response = client.post(
        f"/tenants/{TENANT_ID}/conversations/conv-1/messages",
        json={"sender": "user", "content": "hello"},
    )

    assert response.status_code == 201
    assert response.json()["id"] == "msg-1"

