"""Tests for variables API routes."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient


class TestListVariables:
    """Tests for GET /variables endpoint."""

    def test_returns_list_of_variables(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that endpoint returns list of variables."""
        mock_variables = [
            {
                "id": "var-1",
                "name": "text_variable",
                "type": "text",
                "default_value": "default text",
                "description": "A text variable",
                "tags": ["tag1"],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
            {
                "id": "var-2",
                "name": "number_variable",
                "type": "number",
                "default_value": 42,
                "description": "A number variable",
                "tags": [],
                "created_at": "2024-01-02T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
            },
        ]
        mock_supabase.table.return_value.select.return_value.execute.return_value.data = mock_variables

        response = client.get("/variables")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "text_variable"


class TestGetVariable:
    """Tests for GET /variables/{variable_id} endpoint."""

    def test_returns_variable_when_exists(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that endpoint returns variable by ID."""
        mock_variable = {
            "id": "var-1",
            "name": "test_variable",
            "type": "boolean",
            "default_value": True,
            "description": "A test boolean variable",
            "tags": ["test"],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = mock_variable

        response = client.get("/variables/var-1")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_variable"
        assert data["type"] == "boolean"
        assert data["defaultValue"] is True

    def test_returns_404_when_not_found(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that endpoint returns 404 when variable doesn't exist."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None

        response = client.get("/variables/nonexistent")

        assert response.status_code == 404


class TestCreateVariable:
    """Tests for POST /variables endpoint."""

    def test_creates_text_variable_successfully(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that text variable is created successfully."""
        created_variable = {
            "id": "new-var-id",
            "name": "new_text_var",
            "type": "text",
            "default_value": "hello",
            "description": "A new text variable",
            "tags": ["new"],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            created_variable
        ]

        response = client.post(
            "/variables",
            json={
                "name": "new_text_var",
                "type": "text",
                "defaultValue": "hello",
                "description": "A new text variable",
                "tags": ["new"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "new_text_var"
        assert data["id"] == "new-var-id"

    def test_creates_enum_variable_successfully(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that enum variable is created successfully."""
        created_variable = {
            "id": "new-var-id",
            "name": "enum_var",
            "type": "enum",
            "default_value": "option1",
            "description": "An enum variable",
            "tags": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            created_variable
        ]

        response = client.post(
            "/variables",
            json={
                "name": "enum_var",
                "type": "enum",
                "defaultValue": "option1",
                "description": "An enum variable",
            },
        )

        assert response.status_code == 201

    def test_creates_boolean_variable_successfully(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that boolean variable is created successfully."""
        created_variable = {
            "id": "new-var-id",
            "name": "bool_var",
            "type": "boolean",
            "default_value": False,
            "description": "A boolean variable",
            "tags": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            created_variable
        ]

        response = client.post(
            "/variables",
            json={
                "name": "bool_var",
                "type": "boolean",
                "defaultValue": False,
                "description": "A boolean variable",
            },
        )

        assert response.status_code == 201

    def test_creates_number_variable_successfully(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that number variable is created successfully."""
        created_variable = {
            "id": "new-var-id",
            "name": "num_var",
            "type": "number",
            "default_value": 3.14,
            "description": "A number variable",
            "tags": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            created_variable
        ]

        response = client.post(
            "/variables",
            json={
                "name": "num_var",
                "type": "number",
                "defaultValue": 3.14,
                "description": "A number variable",
            },
        )

        assert response.status_code == 201


class TestUpdateVariable:
    """Tests for PUT /variables/{variable_id} endpoint."""

    def test_updates_variable_successfully(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that variable is updated successfully."""
        updated_variable = {
            "id": "var-1",
            "name": "updated_variable",
            "type": "text",
            "default_value": "updated value",
            "description": "Updated description",
            "tags": ["updated"],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
        }
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            updated_variable
        ]

        response = client.put(
            "/variables/var-1",
            json={
                "id": "var-1",
                "name": "updated_variable",
                "defaultValue": "updated value",
                "description": "Updated description",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "updated_variable"


class TestDeleteVariable:
    """Tests for DELETE /variables/{variable_id} endpoint."""

    def test_deletes_variable_successfully(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that variable is deleted successfully."""
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = [
            {"id": "var-1"}
        ]

        response = client.delete("/variables/var-1")

        assert response.status_code == 204

    def test_returns_404_when_not_found(
        self, client: TestClient, mock_supabase: MagicMock
    ):
        """Test that endpoint returns 404 when variable doesn't exist."""
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []

        response = client.delete("/variables/nonexistent")

        assert response.status_code == 404
