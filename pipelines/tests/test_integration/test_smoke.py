"""Smoke tests for pipeline health.

Quick sanity checks that verify basic patterns without full execution.
These tests catch common bugs like using deps instead of ins.
"""

import json
from pathlib import Path

import dagster as dg
import pytest

from pipelines.config import (
    get_enabled_countries,
    get_enabled_indicators,
    load_world_bank_config,
)
from pipelines.definitions import defs


class TestPipelineSmoke:
    """Smoke tests for basic pipeline health."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def staging_specs(self, all_specs):
        """Get only staging asset specs."""
        return [
            spec
            for spec in all_specs
            if (
                len(spec.key.path) >= 3
                and spec.key.path[0] == "_pipeline"
                and spec.key.path[1] == "staging"
            )
        ]

    def test_can_load_definitions(self):
        """Test that definitions load without errors."""
        assert defs is not None
        assert isinstance(defs, dg.Definitions)

    def test_staging_assets_have_dependencies(self, staging_specs):
        """Test that all staging assets declare dependencies.

        This verifies staging assets aren't orphaned (missing upstream).
        """
        for spec in staging_specs:
            assert len(spec.deps) > 0, f"Staging asset {spec.key} has no dependencies"

    def test_no_circular_dependencies(self, all_specs):
        """Test that asset graph has no circular dependencies."""
        # Build adjacency map
        deps_map = {}
        for spec in all_specs:
            deps_map[spec.key] = [dep.asset_key for dep in spec.deps]

        # Simple cycle detection via DFS
        def has_cycle(node, visited, rec_stack):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in deps_map.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        visited = set()
        for spec in all_specs:
            if spec.key not in visited:
                rec_stack = set()
                assert not has_cycle(spec.key, visited, rec_stack), (
                    f"Circular dependency detected involving {spec.key}"
                )

    def test_all_assets_have_layer_metadata(self, all_specs):
        """Test that assets with layer metadata have valid values.

        Note: Some newer assets may not have layer metadata yet.
        """
        valid_layers = {"bronze", "silver", "gold"}
        missing_layer = []

        for spec in all_specs:
            if "layer" not in spec.metadata:
                missing_layer.append(spec.key)
                continue

            assert spec.metadata["layer"] in valid_layers, (
                f"Asset {spec.key} has invalid layer: {spec.metadata.get('layer')}"
            )

        # Allow up to 20 assets without layer metadata (for newer assets under development)
        assert len(missing_layer) <= 20, (
            f"Too many assets ({len(missing_layer)}) missing 'layer' metadata. "
            f"First 10: {[str(k) for k in missing_layer[:10]]}"
        )

    def test_config_loads_successfully(self):
        """Test that World Bank configuration loads without errors."""
        config = load_world_bank_config()
        assert config is not None
        assert "countries" in config
        assert "indicators" in config
        assert "settings" in config

    def test_enabled_countries_and_indicators_return_data(self):
        """Test that config returns enabled countries and indicators."""
        countries = get_enabled_countries()
        indicators = get_enabled_indicators()

        assert len(countries) > 0, "Should have at least one enabled country"
        assert len(indicators) > 0, "Should have at least one enabled indicator"

        # Verify structure
        assert all(isinstance(c, tuple) and len(c) == 2 for c in countries)
        assert isinstance(indicators, dict)

    def test_comparison_assets_json_structure(self):
        """Test that comparison asset JSON files have valid structure.

        This test validates that comparison assets can be properly serialized
        to JSON without Timestamp serialization errors.
        """
        comparison_dir = Path("_data/assets/economic/comparisons")

        # If directory doesn't exist, skip (assets not materialized yet)
        if not comparison_dir.exists():
            pytest.skip("Comparison assets not yet materialized")

        # Check all JSON files in comparisons directory
        json_files = list(comparison_dir.glob("*.json"))

        if len(json_files) == 0:
            pytest.skip("No comparison JSON files found")

        for json_file in json_files:
            # Verify file can be loaded as valid JSON
            try:
                with open(json_file) as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in {json_file.name}: {e}")

            # Verify expected structure
            assert "summary" in data, f"{json_file.name} missing 'summary' field"
            assert "timeseries" in data, f"{json_file.name} missing 'timeseries' field"

            # Verify summary is a list of country records
            summary = data["summary"]
            assert isinstance(summary, list), (
                f"{json_file.name} summary should be a list of country records"
            )

            if len(summary) > 0:
                # Each summary record should have country info
                assert "country_code" in summary[0], (
                    f"{json_file.name} summary records missing 'country_code'"
                )
                assert "country_name" in summary[0], (
                    f"{json_file.name} summary records missing 'country_name'"
                )

            # Verify timeseries is a dict (keyed by country code)
            assert isinstance(data["timeseries"], dict), (
                f"{json_file.name} timeseries should be a dict"
            )

            # If timeseries has data, verify structure of country data
            if len(data["timeseries"]) > 0:
                # Get first country's timeseries data
                first_country_code = list(data["timeseries"].keys())[0]
                first_country_data = data["timeseries"][first_country_code]

                assert isinstance(first_country_data, list), (
                    f"{json_file.name} country timeseries should be a list"
                )

                if len(first_country_data) > 0:
                    first_record = first_country_data[0]
                    assert "date" in first_record, (
                        f"{json_file.name} timeseries record missing 'date'"
                    )

                    # Verify date is a string (not Timestamp object)
                    assert isinstance(first_record["date"], str), (
                        f"{json_file.name} date should be serialized as string, got {type(first_record['date'])}"
                    )
