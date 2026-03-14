"""Tests for prompts API routes."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient


class TestListPrompts:
    """Tests for GET /prompts endpoint."""

    def test_returns_list_of_prompts(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that endpoint returns list of prompts."""
        mock_prompts = [
            {
                "id": "prompt-1",
                "name": "First Prompt",
                "tags": ["tag1", "tag2"],
                "blocks": [{"type": "text", "text": "Hello"}],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
            {
                "id": "prompt-2",
                "name": "Second Prompt",
                "tags": [],
                "blocks": [],
                "created_at": "2024-01-02T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
            },
        ]
        mock_supabase.table.return_value.select.return_value.execute.return_value.data = mock_prompts

        response = client.get("/prompts")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "First Prompt"


class TestGetPrompt:
    """Tests for GET /prompts/{prompt_id} endpoint."""

    def test_returns_prompt_when_exists(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that endpoint returns prompt by ID."""
        mock_prompt = {
            "id": "prompt-1",
            "name": "Test Prompt",
            "tags": ["test"],
            "blocks": [
                {"type": "text", "text": "Hello"},
                {"type": "snippet", "snippetId": "snippet-1"},
            ],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = mock_prompt

        response = client.get("/prompts/prompt-1")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Prompt"
        assert len(data["blocks"]) == 2

    def test_returns_404_when_not_found(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that endpoint returns 404 when prompt doesn't exist."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None

        response = client.get("/prompts/nonexistent")

        assert response.status_code == 404


class TestCreatePrompt:
    """Tests for POST /prompts endpoint."""

    def test_creates_prompt_successfully(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that prompt is created successfully."""
        created_prompt = {
            "id": "new-prompt-id",
            "name": "New Prompt",
            "tags": ["new", "test"],
            "blocks": [{"type": "text", "text": "Content"}],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            created_prompt
        ]

        response = client.post(
            "/prompts",
            json={
                "name": "New Prompt",
                "tags": ["new", "test"],
                "blocks": [{"type": "text", "text": "Content"}],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Prompt"
        assert data["id"] == "new-prompt-id"

    def test_creates_prompt_with_snippet_block(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that prompt with snippet block is created successfully."""
        created_prompt = {
            "id": "new-prompt-id",
            "name": "Prompt with Snippet",
            "tags": [],
            "blocks": [{"type": "snippet", "snippetId": "snippet-1"}],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            created_prompt
        ]

        response = client.post(
            "/prompts",
            json={
                "name": "Prompt with Snippet",
                "blocks": [{"type": "snippet", "snippetId": "snippet-1"}],
            },
        )

        assert response.status_code == 201


class TestUpdatePrompt:
    """Tests for PUT /prompts/{prompt_id} endpoint."""

    def test_updates_prompt_successfully(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that prompt is updated successfully."""
        updated_prompt = {
            "id": "prompt-1",
            "name": "Updated Prompt",
            "tags": ["updated"],
            "blocks": [{"type": "text", "text": "Updated content"}],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
        }
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            updated_prompt
        ]

        response = client.put(
            "/prompts/prompt-1",
            json={"id": "prompt-1", "name": "Updated Prompt", "tags": ["updated"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Prompt"


class TestDeletePrompt:
    """Tests for DELETE /prompts/{prompt_id} endpoint."""

    def test_deletes_prompt_successfully(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that prompt is deleted successfully."""
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = [
            {"id": "prompt-1"}
        ]

        response = client.delete("/prompts/prompt-1")

        assert response.status_code == 204

    def test_returns_404_when_not_found(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that endpoint returns 404 when prompt doesn't exist."""
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []

        response = client.delete("/prompts/nonexistent")

        assert response.status_code == 404
