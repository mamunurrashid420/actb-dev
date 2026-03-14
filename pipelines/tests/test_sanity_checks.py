"""Sanity tests to catch common refactoring errors.

These tests ensure that refactoring changes don't break critical conventions:
- Asset group assignments are consistent
- Modules export ALL_ASSETS correctly
- No assets are accidentally dropped during refactoring
"""

import pytest

from pipelines.assets import bls, sec, world_bank
from pipelines.definitions import defs


class TestAssetGroupAssignments:
    """Ensure all assets have proper group assignments."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    def test_all_world_bank_assets_have_group(self, all_specs):
        """All World Bank assets should have group_name='world_bank'."""
        wb_specs = [
            spec
            for spec in all_specs
            if any(part == "world_bank" for part in spec.key.path)
        ]

        assert len(wb_specs) > 0, "Should have World Bank assets"

        for spec in wb_specs:
            assert spec.group_name == "world_bank", (
                f"{spec.key} missing group_name='world_bank', has '{spec.group_name}'"
            )

    def test_all_sec_assets_have_group(self, all_specs):
        """All SEC assets should have group_name='sec_filings' or 'reference'."""
        sec_specs = [
            spec
            for spec in all_specs
            if (
                any(part == "sec" for part in spec.key.path)
                or any(part == "companies" for part in spec.key.path)
            )
        ]

        assert len(sec_specs) > 0, "Should have SEC assets"

        for spec in sec_specs:
            # Reference assets (like silver/reference/indicator_id_crosswalk) have group_name='reference'
            # Other SEC assets have group_name='sec_filings'
            if "reference" in spec.key.path:
                assert spec.group_name == "reference", (
                    f'{spec.key} is a reference asset, expected group_name="reference", has "{spec.group_name}"'
                )
            else:
                assert spec.group_name == "sec_filings", (
                    f'{spec.key} missing group_name="sec_filings", has "{spec.group_name}"'
                )

    def test_all_fred_assets_have_group(self, all_specs):
        """All FRED assets should have group_name='fred'."""
        fred_specs = [
            spec for spec in all_specs if any(part == "fred" for part in spec.key.path)
        ]

        assert len(fred_specs) > 0, "Should have FRED assets"

        for spec in fred_specs:
            assert spec.group_name == "fred", (
                f"{spec.key} missing group_name='fred', has '{spec.group_name}'"
            )

    def test_all_bls_raw_assets_have_group(self, all_specs):
        """All BLS raw assets should have group_name='bls'."""
        bls_raw_specs = [
            spec for spec in all_specs if any(part == "bls" for part in spec.key.path)
        ]

        assert len(bls_raw_specs) > 0, "Should have BLS raw assets"

        for spec in bls_raw_specs:
            assert spec.group_name == "bls", (
                f"{spec.key} missing group_name='bls', has '{spec.group_name}'"
            )


class TestModuleExports:
    """Ensure modules export assets correctly (partitioned structure)."""

    def test_world_bank_exports_assets(self):
        """world_bank module should export partitioned timeseries asset."""
        # New partitioned structure exports single timeseries asset via __all__
        assert hasattr(world_bank, "__all__"), "world_bank module should export __all__"
        assert isinstance(world_bank.__all__, list), (
            "world_bank.__all__ should be a list"
        )
        assert len(world_bank.__all__) > 0, "world_bank.__all__ should not be empty"

        # Check for partitioned timeseries asset
        assert "worldbank_timeseries" in world_bank.__all__, (
            "world_bank should export worldbank_timeseries"
        )

    def test_sec_exports_assets(self):
        """sec module should export partitioned assets."""
        # New modular structure exports individual assets via __all__
        assert hasattr(sec, "__all__"), "sec module should export __all__"
        assert isinstance(sec.__all__, list), "sec.__all__ should be a list"
        assert len(sec.__all__) > 0, "sec.__all__ should not be empty"

        # Check for key assets (new time-based structure)
        # Registry assets
        assert "sec_filer_registry" in sec.__all__, (
            "sec should export sec_filer_registry"
        )
        assert "company_registry" in sec.__all__, "sec should export company_registry"
        # Form assets (new naming convention)
        assert "bronze_form_10k_text" in sec.__all__, (
            "sec should export bronze_form_10k_text"
        )
        assert "bronze_form_4" in sec.__all__, "sec should export bronze_form_4"

    def test_bls_exports_assets(self):
        """bls module should export all_series asset."""
        # Exports single all_series asset via __all__
        assert hasattr(bls, "__all__"), "bls module should export __all__"
        assert isinstance(bls.__all__, list), "bls.__all__ should be a list"
        assert len(bls.__all__) > 0, "bls.__all__ should not be empty"

        # Check for all_series asset
        assert "all_series" in bls.__all__, "bls should export all_series"


class TestAssetCounts:
    """Ensure asset counts are reasonable after refactoring (partitioned structure)."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    def test_total_asset_count_is_reasonable(self, all_specs):
        """Total number of assets should be > 10 (partitioned structure has fewer definitions)."""
        assert len(all_specs) > 10, (
            f"Expected > 10 total assets, found {len(all_specs)}. Did refactoring drop assets?"
        )

    def test_world_bank_asset_count_is_reasonable(self, all_specs):
        """World Bank should have partitioned assets (fewer definitions, many partition instances)."""
        wb_specs = [spec for spec in all_specs if spec.group_name == "world_bank"]
        # New partitioned structure: 1 partitioned timeseries asset (creates many partition instances)
        assert len(wb_specs) >= 1, (
            f"Expected >= 1 World Bank asset (partitioned timeseries), found {len(wb_specs)}"
        )

    def test_sec_asset_count_is_reasonable(self, all_specs):
        """SEC should have partitioned assets (fewer definitions, many partition instances)."""
        sec_specs = [spec for spec in all_specs if spec.group_name == "sec_filings"]
        # New partitioned structure: ~4-8 asset definitions (each creates many partition instances)
        assert len(sec_specs) >= 4, (
            f"Expected >= 4 SEC assets (partitioned), found {len(sec_specs)}"
        )

    def test_bls_asset_count_is_reasonable(self, all_specs):
        """BLS should have partitioned timeseries asset."""
        bls_specs = [spec for spec in all_specs if spec.group_name == "bls"]
        # New partitioned structure: 1 partitioned timeseries asset (creates 6 partition instances)
        assert len(bls_specs) >= 1, (
            f"Expected >= 1 BLS asset (partitioned timeseries), found {len(bls_specs)}"
        )


class TestDefinitionsLoadSuccessfully:
    """Ensure definitions can be loaded without errors."""

    def test_definitions_load(self):
        """Definitions should load successfully."""
        assert defs is not None
        assert hasattr(defs, "get_all_asset_specs")

    def test_all_assets_have_valid_keys(self):
        """All assets should have valid asset keys."""
        specs = list(defs.resolve_all_asset_specs())

        for spec in specs:
            assert spec.key is not None, "Asset should have a key"
            assert len(spec.key.path) > 0, f"Asset {spec.key} has empty path"
