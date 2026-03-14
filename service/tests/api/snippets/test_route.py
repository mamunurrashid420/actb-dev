"""Tests for snippets API routes."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient


class TestListSnippets:
    """Tests for GET /snippets endpoint."""

    def test_returns_list_of_snippets(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that endpoint returns list of snippets."""
        mock_snippets = [
            {
                "id": "snippet-1",
                "name": "First Snippet",
                "body": "This is the first snippet content.",
                "tags": ["tag1"],
                "word_count": 6,
                "used_in_prompts": 2,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
            {
                "id": "snippet-2",
                "name": "Second Snippet",
                "body": "Second snippet.",
                "tags": [],
                "word_count": 2,
                "used_in_prompts": 0,
                "created_at": "2024-01-02T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
            },
        ]
        mock_supabase.table.return_value.select.return_value.execute.return_value.data = mock_snippets

        response = client.get("/snippets")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "First Snippet"


class TestGetSnippet:
    """Tests for GET /snippets/{snippet_id} endpoint."""

    def test_returns_snippet_when_exists(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that endpoint returns snippet by ID."""
        mock_snippet = {
            "id": "snippet-1",
            "name": "Test Snippet",
            "body": "This is the test snippet body content.",
            "tags": ["test", "example"],
            "word_count": 7,
            "used_in_prompts": 1,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = mock_snippet

        response = client.get("/snippets/snippet-1")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Snippet"
        assert data["wordCount"] == 7

    def test_returns_404_when_not_found(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that endpoint returns 404 when snippet doesn't exist."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None

        response = client.get("/snippets/nonexistent")

        assert response.status_code == 404


class TestCreateSnippet:
    """Tests for POST /snippets endpoint."""

    def test_creates_snippet_successfully(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that snippet is created successfully."""
        created_snippet = {
            "id": "new-snippet-id",
            "name": "New Snippet",
            "body": "This is the new snippet content.",
            "tags": ["new"],
            "word_count": 6,
            "used_in_prompts": 0,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            created_snippet
        ]

        response = client.post(
            "/snippets",
            json={
                "name": "New Snippet",
                "body": "This is the new snippet content.",
                "tags": ["new"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Snippet"
        assert data["id"] == "new-snippet-id"

    def test_creates_snippet_with_empty_tags(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that snippet can be created without tags."""
        created_snippet = {
            "id": "new-snippet-id",
            "name": "Minimal Snippet",
            "body": "Content",
            "tags": [],
            "word_count": 1,
            "used_in_prompts": 0,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            created_snippet
        ]

        response = client.post(
            "/snippets",
            json={"name": "Minimal Snippet", "body": "Content"},
        )

        assert response.status_code == 201


class TestUpdateSnippet:
    """Tests for PUT /snippets/{snippet_id} endpoint."""

    def test_updates_snippet_successfully(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that snippet is updated successfully."""
        updated_snippet = {
            "id": "snippet-1",
            "name": "Updated Snippet",
            "body": "Updated content here.",
            "tags": ["updated"],
            "word_count": 3,
            "used_in_prompts": 1,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
        }
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            updated_snippet
        ]

        response = client.put(
            "/snippets/snippet-1",
            json={
                "id": "snippet-1",
                "name": "Updated Snippet",
                "body": "Updated content here.",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Snippet"


class TestDeleteSnippet:
    """Tests for DELETE /snippets/{snippet_id} endpoint."""

    def test_deletes_snippet_successfully(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that snippet is deleted successfully."""
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = [
            {"id": "snippet-1"}
        ]

        response = client.delete("/snippets/snippet-1")

        assert response.status_code == 204

    def test_returns_404_when_not_found(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that endpoint returns 404 when snippet doesn't exist."""
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []

        response = client.delete("/snippets/nonexistent")

        assert response.status_code == 404
