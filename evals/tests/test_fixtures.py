"""Tests for tool fixtures."""

from pathlib import Path

import pytest
import yaml

from evals.framework.fixtures import FixtureManager, ToolFixtures


class TestToolFixtures:
    """Tests for ToolFixtures model."""

    def test_accepts_path(self):
        """Should accept a path to a fixture file."""
        fixtures = ToolFixtures(tools=Path("fixtures/tools/example.yaml"))
        assert fixtures.tools == Path("fixtures/tools/example.yaml")

    def test_accepts_string_path(self):
        """Should accept a string path to a fixture file."""
        fixtures = ToolFixtures(tools="fixtures/tools/example.yaml")
        assert fixtures.tools == Path("fixtures/tools/example.yaml")

    def test_accepts_live_mode(self):
        """Should accept 'live' for no mocking."""
        fixtures = ToolFixtures(tools="live")
        assert fixtures.tools == "live"

    def test_rejects_extra_fields(self):
        """Should reject unknown fields."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ToolFixtures(tools="live", unknown_field="value")


class TestFixtureManager:
    """Tests for FixtureManager."""

    @pytest.fixture
    def fixture_file(self, tmp_path: Path) -> Path:
        """Create a temporary fixture file."""
        fixture_data = {
            "search": [
                {
                    "input": {"query": "gdp"},
                    "output": ["fred/gdp/usa", "worldbank/gdp"],
                },
                {"input": {"query": "employment"}, "output": ["bls/employment"]},
            ],
            "describe": [
                {
                    "input": {"asset_path": "fred/gdp/usa"},
                    "output": {"is_partitioned": False, "row_count": 1200},
                },
            ],
            "get": [
                {
                    "input": {"asset_path": "fred/gdp/usa"},
                    "output": {
                        "columns": ["date", "value"],
                        "rows": [["2024-01-01", 28.3]],
                    },
                },
                {
                    "input": {"asset_path": "fred/gdp/usa", "partition": "Q1"},
                    "output": {
                        "columns": ["date", "value"],
                        "rows": [["2024-01-01", 28.0]],
                    },
                },
            ],
        }
        fixture_path = tmp_path / "fixtures.yaml"
        fixture_path.write_text(yaml.dump(fixture_data))
        return fixture_path

    @pytest.mark.asyncio
    async def test_mock_mode_returns_canned_responses(self, fixture_file: Path):
        """FixtureManager with mock mode should return canned responses."""
        import shared.data

        fixtures = ToolFixtures(tools=fixture_file)
        manager = FixtureManager()

        async with manager.apply(fixtures):
            # Test search
            result = shared.data.search("gdp")
            assert result == ["fred/gdp/usa", "worldbank/gdp"]

            # Test describe
            result = shared.data.describe("fred/gdp/usa")
            assert result == {"is_partitioned": False, "row_count": 1200}

            # Test get
            result = shared.data.get("fred/gdp/usa")
            assert result == {
                "columns": ["date", "value"],
                "rows": [["2024-01-01", 28.3]],
            }

    @pytest.mark.asyncio
    async def test_live_mode_doesnt_patch(self):
        """FixtureManager with live mode should not patch functions."""
        import shared.data

        # Store original function references
        original_search = shared.data.search
        original_describe = shared.data.describe
        original_get = shared.data.get

        fixtures = ToolFixtures(tools="live")
        manager = FixtureManager()

        async with manager.apply(fixtures):
            # Functions should still be the originals
            assert shared.data.search is original_search
            assert shared.data.describe is original_describe
            assert shared.data.get is original_get

    @pytest.mark.asyncio
    async def test_none_fixtures_doesnt_patch(self):
        """FixtureManager with None fixtures should not patch functions."""
        import shared.data

        original_search = shared.data.search
        manager = FixtureManager()

        async with manager.apply(None):
            assert shared.data.search is original_search

    @pytest.mark.asyncio
    async def test_raises_value_error_when_no_match(self, fixture_file: Path):
        """FixtureManager should raise ValueError when no fixture match is found."""
        import shared.data

        fixtures = ToolFixtures(tools=fixture_file)
        manager = FixtureManager()

        async with manager.apply(fixtures):
            with pytest.raises(ValueError, match="No fixture match for input"):
                shared.data.search("nonexistent_query")

    @pytest.mark.asyncio
    async def test_input_matching_with_partial_matches(self, fixture_file: Path):
        """Input matching should work with partial matches (expected is subset of actual)."""
        import shared.data

        fixtures = ToolFixtures(tools=fixture_file)
        manager = FixtureManager()

        async with manager.apply(fixtures):
            # Call with extra keyword args - should still match
            result = shared.data.search(query="gdp", env="local")
            assert result == ["fred/gdp/usa", "worldbank/gdp"]

    @pytest.mark.asyncio
    async def test_input_matching_with_multiple_params(self, fixture_file: Path):
        """Should match fixtures with multiple input parameters."""
        import shared.data

        fixtures = ToolFixtures(tools=fixture_file)
        manager = FixtureManager()

        async with manager.apply(fixtures):
            # Test get with partition parameter
            result = shared.data.get(asset_path="fred/gdp/usa", partition="Q1")
            assert result == {
                "columns": ["date", "value"],
                "rows": [["2024-01-01", 28.0]],
            }

    @pytest.mark.asyncio
    async def test_file_not_found_raises_error(self, tmp_path: Path):
        """Should raise FileNotFoundError if fixture file doesn't exist."""
        fixtures = ToolFixtures(tools=tmp_path / "nonexistent.yaml")
        manager = FixtureManager()

        with pytest.raises(FileNotFoundError, match="Fixture file not found"):
            async with manager.apply(fixtures):
                pass

    @pytest.mark.asyncio
    async def test_positional_args_converted_to_kwargs(self, fixture_file: Path):
        """Should handle positional arguments by converting to keyword args."""
        import shared.data

        fixtures = ToolFixtures(tools=fixture_file)
        manager = FixtureManager()

        async with manager.apply(fixtures):
            # Call with positional arg - should be converted to query/asset_path
            result = shared.data.search("employment")
            assert result == ["bls/employment"]

    @pytest.mark.asyncio
    async def test_empty_fixture_sections(self, tmp_path: Path):
        """Should handle fixture files with missing sections."""
        fixture_data = {
            "search": [{"input": {"query": "test"}, "output": ["result"]}]
            # describe and get sections are missing
        }
        fixture_path = tmp_path / "partial.yaml"
        fixture_path.write_text(yaml.dump(fixture_data))

        import shared.data

        fixtures = ToolFixtures(tools=fixture_path)
        manager = FixtureManager()

        async with manager.apply(fixtures):
            # Search should work
            result = shared.data.search("test")
            assert result == ["result"]

            # Describe and get should raise ValueError (no fixtures defined)
            with pytest.raises(ValueError, match="No fixture match"):
                shared.data.describe("any_path")


class TestInputsMatch:
    """Tests for FixtureManager._inputs_match method."""

    def test_exact_match(self):
        """Should match when expected equals actual."""
        manager = FixtureManager()
        assert manager._inputs_match({"query": "gdp"}, {"query": "gdp"}) is True

    def test_partial_match_subset(self):
        """Should match when expected is subset of actual."""
        manager = FixtureManager()
        assert (
            manager._inputs_match(
                {"query": "gdp"}, {"query": "gdp", "env": "local", "limit": 10}
            )
            is True
        )

    def test_no_match_different_value(self):
        """Should not match when values differ."""
        manager = FixtureManager()
        assert (
            manager._inputs_match({"query": "gdp"}, {"query": "unemployment"}) is False
        )

    def test_no_match_missing_key(self):
        """Should not match when expected key is missing from actual."""
        manager = FixtureManager()
        assert manager._inputs_match({"query": "gdp"}, {"other": "value"}) is False

    def test_empty_expected_matches_anything(self):
        """Empty expected should match any actual inputs."""
        manager = FixtureManager()
        assert manager._inputs_match({}, {"query": "gdp", "env": "local"}) is True

    def test_multiple_keys_must_all_match(self):
        """All expected keys must match."""
        manager = FixtureManager()
        assert (
            manager._inputs_match(
                {"asset_path": "fred/gdp", "partition": "Q1"},
                {"asset_path": "fred/gdp", "partition": "Q1", "env": "local"},
            )
            is True
        )

        assert (
            manager._inputs_match(
                {"asset_path": "fred/gdp", "partition": "Q1"},
                {"asset_path": "fred/gdp", "partition": "Q2"},
            )
            is False
        )
