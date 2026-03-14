"""Tests for agriculture indicator asset functions.

Tests validate that agriculture weather assets have proper naming, metadata, structure,
and dependencies without making actual API calls.
"""

import dagster as dg
import pytest

from pipelines.definitions import defs


class TestAgricultureWeatherAssets:
    """Tests for agriculture weather assets."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def agriculture_weather_specs(self, all_specs):
        """Get only agriculture weather asset specs."""
        return [
            spec
            for spec in all_specs
            if len(spec.key.path) >= 3
            and spec.key.path[:3] == ["gold", "agriculture", "weather"]
        ]

    @pytest.fixture
    def specs_by_key(self, all_specs):
        """Index specs by asset key for efficient lookup."""
        return {spec.key: spec for spec in all_specs}

    def test_agriculture_weather_daily_exists(self, specs_by_key):
        """Test that agriculture weather daily asset is defined."""
        expected_key = dg.AssetKey(["gold", "agriculture", "weather", "daily"])
        assert expected_key in specs_by_key, "Missing agriculture weather daily asset"

    def test_agriculture_weather_monthly_exists(self, specs_by_key):
        """Test that agriculture weather monthly asset is defined."""
        expected_key = dg.AssetKey(["gold", "agriculture", "weather", "monthly"])
        assert expected_key in specs_by_key, "Missing agriculture weather monthly asset"

    def test_agriculture_weather_asset_count(self, agriculture_weather_specs):
        """Test that we have exactly 2 agriculture weather assets (daily, monthly)."""
        assert len(agriculture_weather_specs) == 2, (
            f"Expected 2 agriculture weather assets, found {len(agriculture_weather_specs)}"
        )

    def test_agriculture_weather_daily_is_partitioned(self, specs_by_key):
        """Test that agriculture weather daily asset is partitioned."""
        key = dg.AssetKey(["gold", "agriculture", "weather", "daily"])
        spec = specs_by_key[key]

        assert spec.partitions_def is not None, (
            "Agriculture weather daily asset should be partitioned"
        )

    def test_agriculture_weather_monthly_is_partitioned(self, specs_by_key):
        """Test that agriculture weather monthly asset is partitioned."""
        key = dg.AssetKey(["gold", "agriculture", "weather", "monthly"])
        spec = specs_by_key[key]

        assert spec.partitions_def is not None, (
            "Agriculture weather monthly asset should be partitioned"
        )

    def test_agriculture_weather_asset_key_structure(self, agriculture_weather_specs):
        """Test that agriculture weather assets have correct key structure."""
        for spec in agriculture_weather_specs:
            assert len(spec.key.path) == 4, (
                f"Agriculture weather asset {spec.key} should have 4 components in key path"
            )

            assert spec.key.path[0] == "gold", (
                f'Agriculture weather asset {spec.key} first component should be "gold"'
            )

            assert spec.key.path[1] == "agriculture", (
                f'Agriculture weather asset {spec.key} second component should be "agriculture"'
            )

            assert spec.key.path[2] == "weather", (
                f'Agriculture weather asset {spec.key} third component should be "weather"'
            )

    def test_agriculture_weather_asset_metadata_complete(
        self, agriculture_weather_specs
    ):
        """Test that agriculture weather assets have complete metadata."""
        required_fields = ["layer", "visibility", "domain"]

        for spec in agriculture_weather_specs:
            # Check required fields present
            for field in required_fields:
                assert field in spec.metadata, (
                    f'Agriculture weather asset {spec.key} missing required metadata field "{field}"'
                )

            # Check specific values
            assert spec.metadata["layer"] == "gold", (
                f'Agriculture weather asset {spec.key} should have layer="gold"'
            )

            assert spec.metadata["visibility"] == "llm_accessible", (
                f'Agriculture weather asset {spec.key} should have visibility="llm_accessible"'
            )

            assert spec.metadata["domain"] == "agriculture", (
                f'Agriculture weather asset {spec.key} should have domain="agriculture"'
            )

    def test_agriculture_weather_assets_have_descriptions(
        self, agriculture_weather_specs
    ):
        """Test that agriculture weather assets have descriptions."""
        for spec in agriculture_weather_specs:
            description = spec.description or spec.metadata.get("description", "")

            assert len(description) > 0, (
                f"Agriculture weather asset {spec.key} should have a description"
            )

    def test_agriculture_weather_daily_has_nasa_power_dependency(self, specs_by_key):
        """Test that daily agriculture weather depends on NASA POWER daily bronze asset."""
        key = dg.AssetKey(["gold", "agriculture", "weather", "daily"])
        spec = specs_by_key[key]

        # Check that it has dependencies
        assert len(spec.deps) > 0, "Agriculture weather daily should have dependencies"

        # Check for NASA POWER bronze daily dependency
        nasa_power_daily_key = dg.AssetKey(["bronze", "nasa_power", "daily"])
        dep_keys = [dep.asset_key for dep in spec.deps]

        assert nasa_power_daily_key in dep_keys, (
            "Agriculture weather daily should depend on bronze/nasa_power/daily"
        )

    def test_agriculture_weather_monthly_has_nasa_power_dependency(self, specs_by_key):
        """Test that monthly agriculture weather depends on NASA POWER monthly bronze asset."""
        key = dg.AssetKey(["gold", "agriculture", "weather", "monthly"])
        spec = specs_by_key[key]

        # Check that it has dependencies
        assert len(spec.deps) > 0, (
            "Agriculture weather monthly should have dependencies"
        )

        # Check for NASA POWER bronze monthly dependency
        nasa_power_monthly_key = dg.AssetKey(["bronze", "nasa_power", "monthly"])
        dep_keys = [dep.asset_key for dep in spec.deps]

        assert nasa_power_monthly_key in dep_keys, (
            "Agriculture weather monthly should depend on bronze/nasa_power/monthly"
        )

    def test_agriculture_weather_assets_in_correct_group(
        self, agriculture_weather_specs
    ):
        """Test that agriculture weather assets are in agriculture_indicators group."""
        for spec in agriculture_weather_specs:
            assert spec.group_name == "agriculture_indicators", (
                f"Agriculture weather asset {spec.key} should be in agriculture_indicators group"
            )

    def test_agriculture_weather_daily_has_questions_answered(self, specs_by_key):
        """Test that daily agriculture weather has questions_answered metadata."""
        key = dg.AssetKey(["gold", "agriculture", "weather", "daily"])
        spec = specs_by_key[key]

        assert "questions_answered" in spec.metadata, (
            "Daily agriculture weather should have questions_answered metadata"
        )

        questions = spec.metadata["questions_answered"]
        assert isinstance(questions, list), "questions_answered should be a list"

        assert len(questions) > 0, "questions_answered should not be empty"

    def test_agriculture_weather_monthly_has_questions_answered(self, specs_by_key):
        """Test that monthly agriculture weather has questions_answered metadata."""
        key = dg.AssetKey(["gold", "agriculture", "weather", "monthly"])
        spec = specs_by_key[key]

        assert "questions_answered" in spec.metadata, (
            "Monthly agriculture weather should have questions_answered metadata"
        )

        questions = spec.metadata["questions_answered"]
        assert isinstance(questions, list), "questions_answered should be a list"

        assert len(questions) > 0, "questions_answered should not be empty"
