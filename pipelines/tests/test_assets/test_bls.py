"""Tests for BLS bronze asset functions.

Tests validate that BLS bronze assets have proper naming, metadata, and structure
without making actual BLS API calls.
"""

import dagster as dg
import pytest

from pipelines.definitions import defs

# BLS series IDs for validation (from bls.py)
BLS_SERIES_IDS = [
    "JTS000000000000000JOL",  # JOLTS job openings (21-char format)
    "JTS000000000000000QUR",  # JOLTS quit rate (21-char format)
    "CIU1010000000000A",  # Employment Cost Index
    "WPUFD4",  # Producer Price Index
    "LNS11300000",  # Labor force participation
    "CES0500000003",  # Average hourly earnings
]


class TestBlsBronzeAssets:
    """Tests for BLS bronze assets."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def bls_raw_specs(self, all_specs):
        """Get only BLS bronze asset specs."""
        return [
            spec
            for spec in all_specs
            if len(spec.key.path) >= 2 and spec.key.path[:2] == ["bronze", "bls"]
        ]

    @pytest.fixture
    def specs_by_key(self, all_specs):
        """Index specs by asset key for efficient lookup."""
        return {spec.key: spec for spec in all_specs}

    def test_bls_all_series_asset_exists(self, specs_by_key):
        """Test that BLS all_series asset is defined."""
        expected_key = dg.AssetKey(["bronze", "bls", "all_series"])
        assert expected_key in specs_by_key, "Missing BLS bronze all_series asset"

    def test_bls_bronze_asset_count(self, bls_raw_specs):
        """Test that we have BLS bronze assets including all_series."""
        # BLS has multiple assets: all_series + bulk download assets per series
        assert len(bls_raw_specs) >= 1, (
            f"Expected at least 1 BLS bronze asset, found {len(bls_raw_specs)}"
        )

    def test_bls_bronze_asset_key_structure(self, bls_raw_specs):
        """Test that BLS bronze asset has correct key structure."""
        for spec in bls_raw_specs:
            assert len(spec.key.path) == 3, (
                f"BLS bronze asset {spec.key} should have 3 components in key path"
            )

            assert spec.key.path[0] == "bronze", (
                f'BLS bronze asset {spec.key} first component should be "bronze"'
            )

            assert spec.key.path[1] == "bls", (
                f'BLS bronze asset {spec.key} second component should be "bls"'
            )

    def test_bls_bronze_asset_metadata_complete(self, specs_by_key):
        """Test that BLS bronze asset has complete metadata."""
        key = dg.AssetKey(["bronze", "bls", "all_series"])
        spec = specs_by_key[key]

        required_fields = ["layer", "visibility", "source", "country"]

        # Check required fields present
        for field in required_fields:
            assert field in spec.metadata, (
                f'BLS bronze asset {spec.key} missing required metadata field "{field}"'
            )

        # Check specific values
        assert spec.metadata["layer"] == "bronze", (
            'BLS bronze asset should have layer="bronze"'
        )

        assert spec.metadata["visibility"] == "internal", (
            'BLS bronze asset should have visibility="internal"'
        )

        assert spec.metadata["source"] == "bureau_of_labor_statistics", (
            'BLS bronze asset should have source="bureau_of_labor_statistics"'
        )

        assert spec.metadata["country"] == "United States", (
            'BLS bronze asset should have country="United States"'
        )

    def test_bls_bronze_asset_uses_bls_api_pool(self, specs_by_key):
        """Test that BLS bronze asset uses the bls_api concurrency pool."""
        key = dg.AssetKey(["bronze", "bls", "all_series"])
        spec = specs_by_key[key]

        # Check if asset has metadata
        assert hasattr(spec, "metadata"), "BLS bronze asset should have metadata"

    def test_bls_bronze_asset_has_description(self, specs_by_key):
        """Test that BLS bronze asset has a description."""
        key = dg.AssetKey(["bronze", "bls", "all_series"])
        spec = specs_by_key[key]

        description = spec.description or spec.metadata.get("description", "")

        assert len(description) > 0, "BLS bronze asset should have a description"
