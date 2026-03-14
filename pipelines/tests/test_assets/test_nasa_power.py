"""Tests for NASA POWER asset functions.

Tests validate that NASA POWER assets have proper naming, metadata, and structure
without making actual NASA POWER API calls.
"""

import dagster as dg
import pytest

from pipelines.definitions import defs


class TestNasaPowerRawAssets:
    """Tests for NASA POWER bronze layer assets."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def nasa_power_raw_specs(self, all_specs):
        """Get only NASA POWER bronze layer asset specs."""
        return [
            spec
            for spec in all_specs
            if len(spec.key.path) >= 2 and spec.key.path[:2] == ["bronze", "nasa_power"]
        ]

    @pytest.fixture
    def nasa_power_reference_specs(self, all_specs):
        """Get only NASA POWER silver reference asset specs."""
        return [
            spec
            for spec in all_specs
            if len(spec.key.path) >= 3
            and spec.key.path[:2] == ["silver", "reference"]
            and "nasa_power" in spec.key.path[2]
        ]

    @pytest.fixture
    def specs_by_key(self, all_specs):
        """Index specs by asset key for efficient lookup."""
        return {spec.key: spec for spec in all_specs}

    def test_nasa_power_daily_asset_exists(self, specs_by_key):
        """Test that NASA POWER daily asset is defined."""
        expected_key = dg.AssetKey(["bronze", "nasa_power", "daily"])
        assert expected_key in specs_by_key, "Missing NASA POWER bronze daily asset"

    def test_nasa_power_monthly_asset_exists(self, specs_by_key):
        """Test that NASA POWER monthly asset is defined."""
        expected_key = dg.AssetKey(["bronze", "nasa_power", "monthly"])
        assert expected_key in specs_by_key, "Missing NASA POWER bronze monthly asset"

    def test_nasa_power_raw_asset_count(self, nasa_power_raw_specs):
        """Test that we have exactly 2 NASA POWER bronze assets (daily, monthly)."""
        assert len(nasa_power_raw_specs) == 2, (
            f"Expected 2 NASA POWER bronze assets, found {len(nasa_power_raw_specs)}"
        )

    def test_nasa_power_daily_is_partitioned(self, specs_by_key):
        """Test that NASA POWER daily asset is partitioned by agricultural location."""
        key = dg.AssetKey(["bronze", "nasa_power", "daily"])
        spec = specs_by_key[key]

        assert spec.partitions_def is not None, (
            "NASA POWER daily asset should be partitioned"
        )

    def test_nasa_power_monthly_is_partitioned(self, specs_by_key):
        """Test that NASA POWER monthly asset is partitioned by agricultural location."""
        key = dg.AssetKey(["bronze", "nasa_power", "monthly"])
        spec = specs_by_key[key]

        assert spec.partitions_def is not None, (
            "NASA POWER monthly asset should be partitioned"
        )

    def test_nasa_power_raw_asset_key_structure(self, nasa_power_raw_specs):
        """Test that NASA POWER bronze assets have correct key structure."""
        for spec in nasa_power_raw_specs:
            assert len(spec.key.path) == 3, (
                f"NASA POWER bronze asset {spec.key} should have 3 components in key path"
            )

            assert spec.key.path[0] == "bronze", (
                f'NASA POWER bronze asset {spec.key} first component should be "bronze"'
            )

            assert spec.key.path[1] == "nasa_power", (
                f'NASA POWER bronze asset {spec.key} second component should be "nasa_power"'
            )

    def test_nasa_power_raw_asset_metadata_complete(self, nasa_power_raw_specs):
        """Test that NASA POWER bronze assets have complete metadata."""
        required_fields = [
            "layer",
            "visibility",
            "source",
            "temporal_resolution",
            "spatial_resolution",
        ]

        for spec in nasa_power_raw_specs:
            # Check required fields present
            for field in required_fields:
                assert field in spec.metadata, (
                    f'NASA POWER bronze asset {spec.key} missing required metadata field "{field}"'
                )

            # Check specific values
            assert spec.metadata["layer"] == "bronze", (
                f'NASA POWER bronze asset {spec.key} should have layer="bronze"'
            )

            assert spec.metadata["visibility"] == "internal", (
                f'NASA POWER bronze asset {spec.key} should have visibility="internal"'
            )

            assert spec.metadata["source"] == "nasa_power", (
                f'NASA POWER bronze asset {spec.key} should have source="nasa_power"'
            )

            assert spec.metadata["spatial_resolution"] == "50km", (
                f'NASA POWER bronze asset {spec.key} should have spatial_resolution="50km"'
            )

    def test_nasa_power_daily_temporal_resolution(self, specs_by_key):
        """Test that NASA POWER daily asset has correct temporal resolution metadata."""
        key = dg.AssetKey(["bronze", "nasa_power", "daily"])
        spec = specs_by_key[key]

        assert spec.metadata["temporal_resolution"] == "daily", (
            'NASA POWER daily asset should have temporal_resolution="daily"'
        )

    def test_nasa_power_monthly_temporal_resolution(self, specs_by_key):
        """Test that NASA POWER monthly asset has correct temporal resolution metadata."""
        key = dg.AssetKey(["bronze", "nasa_power", "monthly"])
        spec = specs_by_key[key]

        assert spec.metadata["temporal_resolution"] == "monthly", (
            'NASA POWER monthly asset should have temporal_resolution="monthly"'
        )

    def test_nasa_power_raw_assets_have_descriptions(self, nasa_power_raw_specs):
        """Test that NASA POWER bronze assets have descriptions."""
        for spec in nasa_power_raw_specs:
            description = spec.description or spec.metadata.get("description", "")

            assert len(description) > 0, (
                f"NASA POWER bronze asset {spec.key} should have a description"
            )


class TestNasaPowerReferenceAssets:
    """Tests for NASA POWER silver reference assets."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def nasa_power_reference_specs(self, all_specs):
        """Get only NASA POWER silver reference asset specs."""
        return [
            spec
            for spec in all_specs
            if len(spec.key.path) >= 3
            and spec.key.path[:2] == ["silver", "reference"]
            and "nasa_power" in spec.key.path[2]
        ]

    @pytest.fixture
    def specs_by_key(self, all_specs):
        """Index specs by asset key for efficient lookup."""
        return {spec.key: spec for spec in all_specs}

    def test_nasa_power_location_registry_exists(self, specs_by_key):
        """Test that NASA POWER location registry asset is defined."""
        expected_key = dg.AssetKey([
            "silver",
            "reference",
            "nasa_power_location_registry",
        ])
        assert expected_key in specs_by_key, (
            "Missing NASA POWER location registry asset"
        )

    def test_nasa_power_variable_crosswalk_exists(self, specs_by_key):
        """Test that NASA POWER variable crosswalk asset is defined."""
        expected_key = dg.AssetKey([
            "silver",
            "reference",
            "nasa_power_variable_crosswalk",
        ])
        assert expected_key in specs_by_key, (
            "Missing NASA POWER variable crosswalk asset"
        )

    def test_nasa_power_reference_asset_count(self, nasa_power_reference_specs):
        """Test that we have exactly 2 NASA POWER silver reference assets."""
        assert len(nasa_power_reference_specs) == 2, (
            f"Expected 2 NASA POWER silver reference assets, found {len(nasa_power_reference_specs)}"
        )

    def test_nasa_power_reference_assets_not_partitioned(
        self, nasa_power_reference_specs
    ):
        """Test that NASA POWER silver reference assets are not partitioned."""
        for spec in nasa_power_reference_specs:
            assert spec.partitions_def is None, (
                f"NASA POWER silver reference asset {spec.key} should not be partitioned"
            )

    def test_nasa_power_reference_asset_metadata(self, nasa_power_reference_specs):
        """Test that NASA POWER silver reference assets have correct metadata."""
        for spec in nasa_power_reference_specs:
            assert spec.metadata["layer"] == "silver", (
                f'NASA POWER silver reference asset {spec.key} should have layer="silver"'
            )

            assert spec.metadata["visibility"] == "internal", (
                f'NASA POWER silver reference asset {spec.key} should have visibility="internal"'
            )

    def test_nasa_power_reference_assets_have_descriptions(
        self, nasa_power_reference_specs
    ):
        """Test that NASA POWER silver reference assets have descriptions."""
        for spec in nasa_power_reference_specs:
            description = spec.description or spec.metadata.get("description", "")

            assert len(description) > 0, (
                f"NASA POWER silver reference asset {spec.key} should have a description"
            )
