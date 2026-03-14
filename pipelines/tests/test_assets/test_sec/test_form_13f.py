"""Tests for Form 13-F institutional holdings assets.

Tests validate that Form 13-F assets have proper structure, metadata, partitions,
and dependencies without making actual SEC API calls.
"""

import dagster as dg
import pytest

from pipelines.definitions import defs
from pipelines.partitions import sec_quarterly_partitions


class TestForm13FBronzeAsset:
    """Tests for bronze/sec/form_13f asset."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def bronze_form_13f_spec(self, all_specs):
        """Get bronze/sec/form_13f asset spec."""
        key = dg.AssetKey(["bronze", "sec", "form_13f"])
        specs = [spec for spec in all_specs if spec.key == key]
        assert len(specs) == 1, f"Expected 1 spec for {key}, found {len(specs)}"
        return specs[0]

    def test_asset_key_exists(self, all_specs):
        """Test that bronze/sec/form_13f asset exists."""
        keys = [spec.key for spec in all_specs]
        expected_key = dg.AssetKey(["bronze", "sec", "form_13f"])
        assert expected_key in keys, f"Missing {expected_key} asset"

    def test_has_correct_key_prefix(self, bronze_form_13f_spec):
        """Test that asset has correct key prefix."""
        assert bronze_form_13f_spec.key.path[:2] == [
            "bronze",
            "sec",
        ], 'Asset should have key_prefix ["bronze", "sec"]'

    def test_has_quarterly_partitions(self, bronze_form_13f_spec):
        """Test that asset uses sec_quarterly_partitions."""
        assert bronze_form_13f_spec.partitions_def is not None, (
            "Bronze form_13f should be partitioned"
        )

        assert bronze_form_13f_spec.partitions_def == sec_quarterly_partitions, (
            "Bronze form_13f should use sec_quarterly_partitions"
        )

        # Verify partition keys exist (spot check)
        partition_keys = bronze_form_13f_spec.partitions_def.get_partition_keys()
        assert "2020-Q1" in partition_keys, "Should include 2020-Q1 partition"
        assert "2020-Q4" in partition_keys, (
            "Should include 2020-Q4 partition (13F files Q4)"
        )
        assert "2025-Q4" in partition_keys, "Should include 2025-Q4 partition"

    def test_has_required_metadata(self, bronze_form_13f_spec):
        """Test that bronze asset has required metadata fields."""
        required_fields = ["layer", "source", "form_type", "visibility"]

        for field in required_fields:
            assert field in bronze_form_13f_spec.metadata, (
                f'Bronze form_13f missing required metadata field "{field}"'
            )

    def test_metadata_values(self, bronze_form_13f_spec):
        """Test that bronze asset has correct metadata values."""
        metadata = bronze_form_13f_spec.metadata

        assert metadata["layer"] == "bronze", 'Should have layer="bronze"'
        assert metadata["source"] == "sec_edgar", 'Should have source="sec_edgar"'
        assert metadata["form_type"] == "13-F", 'Should have form_type="13-F"'
        assert metadata["visibility"] == "internal", 'Should have visibility="internal"'

    def test_asset_group(self, bronze_form_13f_spec):
        """Test that bronze asset is in correct group."""
        assert bronze_form_13f_spec.group_name == "sec_filings", (
            'Bronze form_13f should be in "sec_filings" group'
        )


class TestForm13FSilverAsset:
    """Tests for silver/sec/form_13f_holdings asset."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def silver_form_13f_spec(self, all_specs):
        """Get silver/sec/form_13f_holdings asset spec."""
        key = dg.AssetKey(["silver", "sec", "form_13f_holdings"])
        specs = [spec for spec in all_specs if spec.key == key]
        assert len(specs) == 1, f"Expected 1 spec for {key}, found {len(specs)}"
        return specs[0]

    def test_asset_key_exists(self, all_specs):
        """Test that silver/sec/form_13f_holdings asset exists."""
        keys = [spec.key for spec in all_specs]
        expected_key = dg.AssetKey(["silver", "sec", "form_13f_holdings"])
        assert expected_key in keys, f"Missing {expected_key} asset"

    def test_has_correct_key_prefix(self, silver_form_13f_spec):
        """Test that asset has correct key prefix."""
        assert silver_form_13f_spec.key.path[:2] == [
            "silver",
            "sec",
        ], 'Asset should have key_prefix ["silver", "sec"]'

    def test_has_quarterly_partitions(self, silver_form_13f_spec):
        """Test that asset uses sec_quarterly_partitions."""
        assert silver_form_13f_spec.partitions_def is not None, (
            "Silver form_13f_holdings should be partitioned"
        )

        assert silver_form_13f_spec.partitions_def == sec_quarterly_partitions, (
            "Silver form_13f_holdings should use sec_quarterly_partitions"
        )

    def test_has_required_metadata(self, silver_form_13f_spec):
        """Test that silver asset has required metadata fields."""
        required_fields = ["layer", "visibility"]

        for field in required_fields:
            assert field in silver_form_13f_spec.metadata, (
                f'Silver form_13f_holdings missing required metadata field "{field}"'
            )

    def test_metadata_values(self, silver_form_13f_spec):
        """Test that silver asset has correct metadata values."""
        metadata = silver_form_13f_spec.metadata

        assert metadata["layer"] == "silver", 'Should have layer="silver"'
        assert metadata["visibility"] == "internal", 'Should have visibility="internal"'

    def test_depends_on_bronze(self, silver_form_13f_spec):
        """Test that silver asset depends on bronze asset."""
        # Get dependency keys
        dep_keys = [dep.asset_key for dep in silver_form_13f_spec.deps]

        expected_bronze_key = dg.AssetKey(["bronze", "sec", "form_13f"])
        assert expected_bronze_key in dep_keys, (
            f"Silver asset should depend on {expected_bronze_key}"
        )

    def test_asset_group(self, silver_form_13f_spec):
        """Test that silver asset is in correct group."""
        assert silver_form_13f_spec.group_name == "sec_filings", (
            'Silver form_13f_holdings should be in "sec_filings" group'
        )


class TestForm13FGoldAsset:
    """Tests for gold/institutions/portfolio/holdings asset."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def gold_holdings_spec(self, all_specs):
        """Get gold/institutions/portfolio/holdings asset spec."""
        key = dg.AssetKey(["gold", "institutions", "portfolio", "holdings"])
        specs = [spec for spec in all_specs if spec.key == key]
        assert len(specs) == 1, f"Expected 1 spec for {key}, found {len(specs)}"
        return specs[0]

    def test_asset_key_exists(self, all_specs):
        """Test that gold/institutions/portfolio/holdings asset exists."""
        keys = [spec.key for spec in all_specs]
        expected_key = dg.AssetKey(["gold", "institutions", "portfolio", "holdings"])
        assert expected_key in keys, f"Missing {expected_key} asset"

    def test_has_correct_key_prefix(self, gold_holdings_spec):
        """Test that asset has correct key prefix."""
        assert gold_holdings_spec.key.path[:2] == [
            "gold",
            "institutions",
        ], 'Asset should have key starting with ["gold", "institutions"]'

    def test_is_unpartitioned(self, gold_holdings_spec):
        """Test that gold asset is unpartitioned (aggregates all quarters)."""
        assert gold_holdings_spec.partitions_def is None, (
            "Gold holdings should be unpartitioned (uses AllPartitionMapping from silver)"
        )

    def test_has_required_metadata(self, gold_holdings_spec):
        """Test that gold asset has required metadata fields."""
        required_fields = ["layer", "visibility"]

        for field in required_fields:
            assert field in gold_holdings_spec.metadata, (
                f'Gold holdings missing required metadata field "{field}"'
            )

    def test_metadata_values(self, gold_holdings_spec):
        """Test that gold asset has correct metadata values."""
        metadata = gold_holdings_spec.metadata

        assert metadata["layer"] == "gold", 'Should have layer="gold"'
        assert metadata["visibility"] == "llm_accessible", (
            'Should have visibility="llm_accessible"'
        )

    def test_depends_on_silver_and_registry(self, gold_holdings_spec):
        """Test that gold asset depends on silver holdings and institution registry."""
        # Get dependency keys
        dep_keys = [dep.asset_key for dep in gold_holdings_spec.deps]

        expected_silver_key = dg.AssetKey(["silver", "sec", "form_13f_holdings"])
        expected_registry_key = dg.AssetKey(["silver", "sec", "institution_registry"])

        assert expected_silver_key in dep_keys, (
            f"Gold asset should depend on {expected_silver_key}"
        )
        assert expected_registry_key in dep_keys, (
            f"Gold asset should depend on {expected_registry_key}"
        )

    def test_uses_all_partition_mapping(self, gold_holdings_spec):
        """Test that gold asset uses AllPartitionMapping for silver dependency."""
        # Find the silver dependency
        silver_deps = [
            dep
            for dep in gold_holdings_spec.deps
            if dep.asset_key == dg.AssetKey(["silver", "sec", "form_13f_holdings"])
        ]

        assert len(silver_deps) == 1, "Should have exactly one silver dependency"
        silver_dep = silver_deps[0]

        # Check partition mapping
        assert isinstance(silver_dep.partition_mapping, dg.AllPartitionMapping), (
            "Silver dependency should use AllPartitionMapping"
        )

    def test_asset_group(self, gold_holdings_spec):
        """Test that gold asset is in correct group."""
        assert gold_holdings_spec.group_name == "sec_filings", (
            'Gold holdings should be in "sec_filings" group'
        )


class TestForm13FMedallionArchitecture:
    """Tests for Form 13-F medallion architecture (bronze → silver → gold)."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    def test_all_layers_exist(self, all_specs):
        """Test that all three medallion layers exist for Form 13-F."""
        keys = [spec.key for spec in all_specs]

        bronze_key = dg.AssetKey(["bronze", "sec", "form_13f"])
        silver_key = dg.AssetKey(["silver", "sec", "form_13f_holdings"])
        gold_key = dg.AssetKey(["gold", "institutions", "portfolio", "holdings"])

        assert bronze_key in keys, f"Missing bronze layer: {bronze_key}"
        assert silver_key in keys, f"Missing silver layer: {silver_key}"
        assert gold_key in keys, f"Missing gold layer: {gold_key}"

    def test_partition_flow(self, all_specs):
        """Test partition definitions flow correctly through layers."""
        # Get specs
        bronze_spec = [
            s for s in all_specs if s.key == dg.AssetKey(["bronze", "sec", "form_13f"])
        ][0]
        silver_spec = [
            s
            for s in all_specs
            if s.key == dg.AssetKey(["silver", "sec", "form_13f_holdings"])
        ][0]
        gold_spec = [
            s
            for s in all_specs
            if s.key == dg.AssetKey(["gold", "institutions", "portfolio", "holdings"])
        ][0]

        # Bronze and silver should both use sec_quarterly_partitions
        assert bronze_spec.partitions_def == sec_quarterly_partitions, (
            "Bronze should use sec_quarterly_partitions"
        )
        assert silver_spec.partitions_def == sec_quarterly_partitions, (
            "Silver should use sec_quarterly_partitions"
        )

        # Gold should be unpartitioned (aggregates all quarters)
        assert gold_spec.partitions_def is None, (
            "Gold should be unpartitioned (aggregates via AllPartitionMapping)"
        )

    def test_dependency_chain(self, all_specs):
        """Test dependency chain flows correctly: bronze → silver → gold."""
        # Get specs
        silver_spec = [
            s
            for s in all_specs
            if s.key == dg.AssetKey(["silver", "sec", "form_13f_holdings"])
        ][0]
        gold_spec = [
            s
            for s in all_specs
            if s.key == dg.AssetKey(["gold", "institutions", "portfolio", "holdings"])
        ][0]

        # Silver depends on bronze
        silver_dep_keys = [dep.asset_key for dep in silver_spec.deps]
        assert dg.AssetKey(["bronze", "sec", "form_13f"]) in silver_dep_keys

        # Gold depends on silver
        gold_dep_keys = [dep.asset_key for dep in gold_spec.deps]
        assert dg.AssetKey(["silver", "sec", "form_13f_holdings"]) in gold_dep_keys

    def test_metadata_progression(self, all_specs):
        """Test metadata progresses correctly through layers."""
        # Get specs
        bronze_spec = [
            s for s in all_specs if s.key == dg.AssetKey(["bronze", "sec", "form_13f"])
        ][0]
        silver_spec = [
            s
            for s in all_specs
            if s.key == dg.AssetKey(["silver", "sec", "form_13f_holdings"])
        ][0]
        gold_spec = [
            s
            for s in all_specs
            if s.key == dg.AssetKey(["gold", "institutions", "portfolio", "holdings"])
        ][0]

        # Check layer metadata
        assert bronze_spec.metadata["layer"] == "bronze"
        assert silver_spec.metadata["layer"] == "silver"
        assert gold_spec.metadata["layer"] == "gold"

        # Check visibility metadata
        assert bronze_spec.metadata["visibility"] == "internal"
        assert silver_spec.metadata["visibility"] == "internal"
        assert gold_spec.metadata["visibility"] == "llm_accessible"
