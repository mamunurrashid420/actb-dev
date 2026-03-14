"""Tests for NOAA asset functions.

Tests validate that NOAA assets have proper naming, metadata, and structure
without making actual NOAA API calls. Tests cover both bronze (raw) and silver
(reference) layer assets.
"""

import dagster as dg
import pytest

from pipelines.definitions import defs


class TestNoaaRawAssets:
    """Tests for NOAA bronze layer (raw) assets."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def noaa_raw_specs(self, all_specs):
        """Get only NOAA bronze layer asset specs."""
        return [
            spec
            for spec in all_specs
            if len(spec.key.path) >= 2 and spec.key.path[:2] == ["bronze", "noaa"]
        ]

    @pytest.fixture
    def noaa_reference_specs(self, all_specs):
        """Get only NOAA silver layer reference asset specs."""
        return [
            spec
            for spec in all_specs
            if len(spec.key.path) >= 2
            and spec.key.path[:2] == ["silver", "reference"]
            and "noaa" in spec.key.path[2]  # Filter for NOAA reference assets
        ]

    @pytest.fixture
    def specs_by_key(self, all_specs):
        """Index specs by asset key for efficient lookup."""
        return {spec.key: spec for spec in all_specs}

    def test_noaa_daily_asset_exists(self, specs_by_key):
        """Test that NOAA daily asset is defined."""
        expected_key = dg.AssetKey(["bronze", "noaa", "daily"])
        assert expected_key in specs_by_key, "Missing NOAA bronze daily asset"

    def test_noaa_monthly_asset_exists(self, specs_by_key):
        """Test that NOAA monthly asset is defined."""
        expected_key = dg.AssetKey(["bronze", "noaa", "monthly"])
        assert expected_key in specs_by_key, "Missing NOAA bronze monthly asset"

    def test_noaa_annual_asset_exists(self, specs_by_key):
        """Test that NOAA annual asset is defined."""
        expected_key = dg.AssetKey(["bronze", "noaa", "annual"])
        assert expected_key in specs_by_key, "Missing NOAA bronze annual asset"

    def test_noaa_raw_asset_count(self, noaa_raw_specs):
        """Test that we have exactly 3 NOAA bronze assets (daily, monthly, annual)."""
        assert len(noaa_raw_specs) == 3, (
            f"Expected 3 NOAA bronze assets, found {len(noaa_raw_specs)}"
        )

    def test_noaa_daily_is_partitioned(self, specs_by_key):
        """Test that NOAA daily asset is partitioned by station ID."""
        key = dg.AssetKey(["bronze", "noaa", "daily"])
        spec = specs_by_key[key]

        assert spec.partitions_def is not None, "NOAA daily asset should be partitioned"

    def test_noaa_monthly_is_partitioned(self, specs_by_key):
        """Test that NOAA monthly asset is partitioned by station ID."""
        key = dg.AssetKey(["bronze", "noaa", "monthly"])
        spec = specs_by_key[key]

        assert spec.partitions_def is not None, (
            "NOAA monthly asset should be partitioned"
        )

    def test_noaa_annual_is_partitioned(self, specs_by_key):
        """Test that NOAA annual asset is partitioned by station ID."""
        key = dg.AssetKey(["bronze", "noaa", "annual"])
        spec = specs_by_key[key]

        assert spec.partitions_def is not None, (
            "NOAA annual asset should be partitioned"
        )

    def test_noaa_raw_asset_key_structure(self, noaa_raw_specs):
        """Test that NOAA bronze assets have correct key structure."""
        for spec in noaa_raw_specs:
            assert len(spec.key.path) == 3, (
                f"NOAA bronze asset {spec.key} should have 3 components in key path"
            )

            assert spec.key.path[0] == "bronze", (
                f'NOAA bronze asset {spec.key} first component should be "bronze"'
            )

            assert spec.key.path[1] == "noaa", (
                f'NOAA bronze asset {spec.key} second component should be "noaa"'
            )

    def test_noaa_raw_asset_metadata_complete(self, noaa_raw_specs):
        """Test that NOAA bronze assets have complete metadata."""
        required_fields = ["layer", "visibility", "source", "dataset"]

        for spec in noaa_raw_specs:
            # Check required fields present
            for field in required_fields:
                assert field in spec.metadata, (
                    f'NOAA bronze asset {spec.key} missing required metadata field "{field}"'
                )

            # Check specific values
            assert spec.metadata["layer"] == "bronze", (
                f'NOAA bronze asset {spec.key} should have layer="bronze"'
            )

            assert spec.metadata["visibility"] == "internal", (
                f'NOAA bronze asset {spec.key} should have visibility="internal"'
            )

            assert spec.metadata["source"] == "noaa", (
                f'NOAA bronze asset {spec.key} should have source="noaa"'
            )

    def test_noaa_daily_dataset_metadata(self, specs_by_key):
        """Test that NOAA daily asset has correct dataset metadata."""
        key = dg.AssetKey(["bronze", "noaa", "daily"])
        spec = specs_by_key[key]

        assert spec.metadata["dataset"] == "ghcn_daily", (
            'NOAA daily asset should have dataset="ghcn_daily"'
        )

    def test_noaa_monthly_dataset_metadata(self, specs_by_key):
        """Test that NOAA monthly asset has correct dataset metadata."""
        key = dg.AssetKey(["bronze", "noaa", "monthly"])
        spec = specs_by_key[key]

        assert spec.metadata["dataset"] == "gsom", (
            'NOAA monthly asset should have dataset="gsom"'
        )

    def test_noaa_annual_dataset_metadata(self, specs_by_key):
        """Test that NOAA annual asset has correct dataset metadata."""
        key = dg.AssetKey(["bronze", "noaa", "annual"])
        spec = specs_by_key[key]

        assert spec.metadata["dataset"] == "gsoy", (
            'NOAA annual asset should have dataset="gsoy"'
        )

    def test_noaa_raw_assets_have_descriptions(self, noaa_raw_specs):
        """Test that NOAA bronze assets have descriptions."""
        for spec in noaa_raw_specs:
            description = spec.description or spec.metadata.get("description", "")

            assert len(description) > 0, (
                f"NOAA bronze asset {spec.key} should have a description"
            )


class TestNoaaReferenceAssets:
    """Tests for NOAA silver layer reference assets."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def noaa_reference_specs(self, all_specs):
        """Get only NOAA silver layer reference asset specs."""
        return [
            spec
            for spec in all_specs
            if len(spec.key.path) >= 3
            and spec.key.path[:2] == ["silver", "reference"]
            and spec.key.path[2].startswith("noaa_")
        ]

    @pytest.fixture
    def specs_by_key(self, all_specs):
        """Index specs by asset key for efficient lookup."""
        return {spec.key: spec for spec in all_specs}

    def test_noaa_station_registry_exists(self, specs_by_key):
        """Test that NOAA station registry asset is defined."""
        expected_key = dg.AssetKey(["silver", "reference", "noaa_stations"])
        assert expected_key in specs_by_key, "Missing NOAA station registry asset"

    def test_noaa_variable_crosswalk_exists(self, specs_by_key):
        """Test that NOAA variable crosswalk asset is defined."""
        expected_key = dg.AssetKey(["silver", "reference", "noaa_variables"])
        assert expected_key in specs_by_key, "Missing NOAA variable crosswalk asset"

    def test_noaa_location_crosswalk_exists(self, specs_by_key):
        """Test that NOAA location crosswalk asset is defined."""
        expected_key = dg.AssetKey(["silver", "reference", "noaa_locations"])
        assert expected_key in specs_by_key, "Missing NOAA location crosswalk asset"

    def test_noaa_reference_asset_count(self, noaa_reference_specs):
        """Test that we have exactly 3 NOAA silver reference assets."""
        assert len(noaa_reference_specs) == 3, (
            f"Expected 3 NOAA silver reference assets, found {len(noaa_reference_specs)}"
        )

    def test_noaa_reference_assets_not_partitioned(self, noaa_reference_specs):
        """Test that NOAA silver reference assets are not partitioned."""
        for spec in noaa_reference_specs:
            assert spec.partitions_def is None, (
                f"NOAA silver reference asset {spec.key} should not be partitioned"
            )

    def test_noaa_reference_asset_metadata(self, noaa_reference_specs):
        """Test that NOAA silver reference assets have correct metadata."""
        for spec in noaa_reference_specs:
            assert spec.metadata["layer"] == "silver", (
                f'NOAA silver reference asset {spec.key} should have layer="silver"'
            )

            assert spec.metadata["visibility"] == "internal", (
                f'NOAA silver reference asset {spec.key} should have visibility="internal"'
            )

    def test_noaa_reference_assets_have_descriptions(self, noaa_reference_specs):
        """Test that NOAA silver reference assets have descriptions."""
        for spec in noaa_reference_specs:
            description = spec.description or spec.metadata.get("description", "")

            assert len(description) > 0, (
                f"NOAA silver reference asset {spec.key} should have a description"
            )
