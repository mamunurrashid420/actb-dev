"""Tests for Form 10-K asset structure and metadata.

Tests validate that Form 10-K assets have proper naming, metadata, partition
configuration, and dependencies without making actual SEC API calls.
"""

import dagster as dg
import pytest

from pipelines.definitions import defs
from pipelines.partitions import sec_yearly_partitions


class TestForm10kBronzeAssets:
    """Tests for Form 10-K bronze layer assets."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def specs_by_key(self, all_specs):
        """Index specs by asset key for efficient lookup."""
        return {spec.key: spec for spec in all_specs}

    def test_bronze_form_10k_text_exists(self, specs_by_key):
        """Test that bronze form_10k_text asset is defined."""
        expected_key = dg.AssetKey(["bronze", "sec", "form_10k_text"])
        assert expected_key in specs_by_key, "Missing bronze/sec/form_10k_text asset"

    def test_bronze_form_10k_text_has_correct_prefix(self, specs_by_key):
        """Test that bronze form_10k_text has correct key prefix."""
        key = dg.AssetKey(["bronze", "sec", "form_10k_text"])
        spec = specs_by_key[key]

        assert spec.key.path[:2] == [
            "bronze",
            "sec",
        ], 'Bronze form_10k_text should have prefix ["bronze", "sec"]'

    def test_bronze_form_10k_text_is_partitioned(self, specs_by_key):
        """Test that bronze form_10k_text uses sec_yearly_partitions."""
        key = dg.AssetKey(["bronze", "sec", "form_10k_text"])
        spec = specs_by_key[key]

        assert spec.partitions_def is not None, (
            "Bronze form_10k_text should be partitioned"
        )

        # Verify it's using yearly partitions (2020-2025)
        expected_keys = sec_yearly_partitions.get_partition_keys()
        actual_keys = spec.partitions_def.get_partition_keys()

        assert actual_keys == expected_keys, (
            f"Bronze form_10k_text partitions {actual_keys} do not match expected {expected_keys}"
        )

    def test_bronze_form_10k_text_has_required_metadata(self, specs_by_key):
        """Test that bronze form_10k_text has required metadata fields."""
        key = dg.AssetKey(["bronze", "sec", "form_10k_text"])
        spec = specs_by_key[key]

        required_fields = ["layer", "visibility", "source", "form_type"]

        for field in required_fields:
            assert field in spec.metadata, (
                f'Bronze form_10k_text missing required metadata field "{field}"'
            )

        assert spec.metadata["layer"] == "bronze", 'Should have layer="bronze"'
        assert spec.metadata["visibility"] == "internal", (
            'Should have visibility="internal"'
        )
        assert spec.metadata["source"] == "sec_edgar", 'Should have source="sec_edgar"'
        assert spec.metadata["form_type"] == "10-K", 'Should have form_type="10-K"'


class TestForm10kSilverAssets:
    """Tests for Form 10-K silver layer assets."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def specs_by_key(self, all_specs):
        """Index specs by asset key for efficient lookup."""
        return {spec.key: spec for spec in all_specs}

    def test_silver_form_10k_sections_exists(self, specs_by_key):
        """Test that silver form_10k_sections asset is defined."""
        expected_key = dg.AssetKey(["silver", "sec", "form_10k_sections"])
        assert expected_key in specs_by_key, (
            "Missing silver/sec/form_10k_sections asset"
        )

    def test_silver_form_10k_sections_has_correct_prefix(self, specs_by_key):
        """Test that silver form_10k_sections has correct key prefix."""
        key = dg.AssetKey(["silver", "sec", "form_10k_sections"])
        spec = specs_by_key[key]

        assert spec.key.path[:2] == [
            "silver",
            "sec",
        ], 'Silver form_10k_sections should have prefix ["silver", "sec"]'

    def test_silver_form_10k_sections_is_partitioned(self, specs_by_key):
        """Test that silver form_10k_sections uses sec_yearly_partitions."""
        key = dg.AssetKey(["silver", "sec", "form_10k_sections"])
        spec = specs_by_key[key]

        assert spec.partitions_def is not None, (
            "Silver form_10k_sections should be partitioned"
        )

        # Verify it's using yearly partitions (2020-2025)
        expected_keys = sec_yearly_partitions.get_partition_keys()
        actual_keys = spec.partitions_def.get_partition_keys()

        assert actual_keys == expected_keys, (
            f"Silver form_10k_sections partitions {actual_keys} do not match expected {expected_keys}"
        )

    def test_silver_form_10k_sections_has_required_metadata(self, specs_by_key):
        """Test that silver form_10k_sections has required metadata fields."""
        key = dg.AssetKey(["silver", "sec", "form_10k_sections"])
        spec = specs_by_key[key]

        required_fields = ["layer", "visibility"]

        for field in required_fields:
            assert field in spec.metadata, (
                f'Silver form_10k_sections missing required metadata field "{field}"'
            )

        assert spec.metadata["layer"] == "silver", 'Should have layer="silver"'
        assert spec.metadata["visibility"] == "internal", (
            'Should have visibility="internal"'
        )

    def test_silver_form_10k_sections_depends_on_bronze(self, specs_by_key):
        """Test that silver form_10k_sections depends on bronze form_10k_text."""
        key = dg.AssetKey(["silver", "sec", "form_10k_sections"])
        spec = specs_by_key[key]

        # Check that the asset has dependencies
        assert hasattr(spec, "deps"), (
            "Silver form_10k_sections should have dependencies"
        )

        # Extract dependency keys
        dep_keys = [dep.asset_key for dep in spec.deps]

        # Check for bronze dependency
        expected_dep = dg.AssetKey(["bronze", "sec", "form_10k_text"])
        assert expected_dep in dep_keys, (
            f"Silver form_10k_sections should depend on {expected_dep}"
        )


class TestForm10kGoldAssets:
    """Tests for Form 10-K gold layer assets."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def specs_by_key(self, all_specs):
        """Index specs by asset key for efficient lookup."""
        return {spec.key: spec for spec in all_specs}

    def test_gold_annual_reports_exists(self, specs_by_key):
        """Test that gold annual_reports asset is defined."""
        expected_key = dg.AssetKey([
            "gold",
            "companies",
            "financials",
            "annual_reports",
        ])
        assert expected_key in specs_by_key, (
            "Missing gold/companies/financials/annual_reports asset"
        )

    def test_gold_annual_reports_has_correct_prefix(self, specs_by_key):
        """Test that gold annual_reports has correct key prefix."""
        key = dg.AssetKey(["gold", "companies", "financials", "annual_reports"])
        spec = specs_by_key[key]

        assert spec.key.path[:3] == [
            "gold",
            "companies",
            "financials",
        ], 'Gold annual_reports should have prefix ["gold", "companies", "financials"]'

    def test_gold_annual_reports_is_unpartitioned(self, specs_by_key):
        """Test that gold annual_reports is unpartitioned."""
        key = dg.AssetKey(["gold", "companies", "financials", "annual_reports"])
        spec = specs_by_key[key]

        assert spec.partitions_def is None, (
            "Gold annual_reports should be unpartitioned (uses AllPartitionMapping from silver)"
        )

    def test_gold_annual_reports_has_required_metadata(self, specs_by_key):
        """Test that gold annual_reports has required metadata fields."""
        key = dg.AssetKey(["gold", "companies", "financials", "annual_reports"])
        spec = specs_by_key[key]

        required_fields = ["layer", "visibility", "questions_answered"]

        for field in required_fields:
            assert field in spec.metadata, (
                f'Gold annual_reports missing required metadata field "{field}"'
            )

        assert spec.metadata["layer"] == "gold", 'Should have layer="gold"'
        assert spec.metadata["visibility"] == "llm_accessible", (
            'Should have visibility="llm_accessible"'
        )

    def test_gold_annual_reports_has_questions_answered(self, specs_by_key):
        """Test that gold annual_reports has non-empty questions_answered list."""
        key = dg.AssetKey(["gold", "companies", "financials", "annual_reports"])
        spec = specs_by_key[key]

        questions = spec.metadata.get("questions_answered", [])

        assert isinstance(questions, list), (
            "Gold annual_reports questions_answered should be a list"
        )

        assert len(questions) > 0, (
            "Gold annual_reports should have at least one question"
        )

    def test_gold_annual_reports_depends_on_silver(self, specs_by_key):
        """Test that gold annual_reports depends on silver form_10k_sections."""
        key = dg.AssetKey(["gold", "companies", "financials", "annual_reports"])
        spec = specs_by_key[key]

        # Check that the asset has dependencies
        assert hasattr(spec, "deps"), "Gold annual_reports should have dependencies"

        # Extract dependency keys
        dep_keys = [dep.asset_key for dep in spec.deps]

        # Check for silver dependency
        expected_dep = dg.AssetKey(["silver", "sec", "form_10k_sections"])
        assert expected_dep in dep_keys, (
            f"Gold annual_reports should depend on {expected_dep}"
        )

    def test_gold_annual_reports_depends_on_registry(self, specs_by_key):
        """Test that gold annual_reports depends on company_registry."""
        key = dg.AssetKey(["gold", "companies", "financials", "annual_reports"])
        spec = specs_by_key[key]

        # Check that the asset has dependencies
        assert hasattr(spec, "deps"), "Gold annual_reports should have dependencies"

        # Extract dependency keys
        dep_keys = [dep.asset_key for dep in spec.deps]

        # Check for registry dependency
        expected_dep = dg.AssetKey(["silver", "sec", "company_registry"])
        assert expected_dep in dep_keys, (
            f"Gold annual_reports should depend on {expected_dep}"
        )


class TestForm10kAssetLayering:
    """Tests for Form 10-K asset layer structure and dependencies."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    def test_form_10k_medallion_layers_exist(self, all_specs):
        """Test that all 3 medallion layers exist for Form 10-K."""
        keys = [spec.key for spec in all_specs]

        assert dg.AssetKey(["bronze", "sec", "form_10k_text"]) in keys
        assert dg.AssetKey(["silver", "sec", "form_10k_sections"]) in keys
        assert (
            dg.AssetKey(["gold", "companies", "financials", "annual_reports"]) in keys
        )

    def test_form_10k_partition_consistency(self, all_specs):
        """Test that bronze and silver use same partition definition."""
        specs_by_key = {spec.key: spec for spec in all_specs}

        bronze_spec = specs_by_key[dg.AssetKey(["bronze", "sec", "form_10k_text"])]
        silver_spec = specs_by_key[dg.AssetKey(["silver", "sec", "form_10k_sections"])]

        # Both should have partitions
        assert bronze_spec.partitions_def is not None
        assert silver_spec.partitions_def is not None

        # Both should have same partition keys
        bronze_keys = bronze_spec.partitions_def.get_partition_keys()
        silver_keys = silver_spec.partitions_def.get_partition_keys()

        assert bronze_keys == silver_keys, (
            "Bronze and silver should use same partition definition"
        )

    def test_form_10k_dependency_chain(self, all_specs):
        """Test that dependencies flow correctly: bronze → silver → gold."""
        specs_by_key = {spec.key: spec for spec in all_specs}

        # Silver depends on bronze
        silver_spec = specs_by_key[dg.AssetKey(["silver", "sec", "form_10k_sections"])]
        silver_deps = [dep.asset_key for dep in silver_spec.deps]
        assert dg.AssetKey(["bronze", "sec", "form_10k_text"]) in silver_deps

        # Gold depends on silver
        gold_spec = specs_by_key[
            dg.AssetKey(["gold", "companies", "financials", "annual_reports"])
        ]
        gold_deps = [dep.asset_key for dep in gold_spec.deps]
        assert dg.AssetKey(["silver", "sec", "form_10k_sections"]) in gold_deps
