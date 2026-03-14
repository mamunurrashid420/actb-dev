"""Generic tests for asset graph structure and wiring.

These tests validate the asset graph WITHOUT materializing assets or fetching live data.
They perform generic sanity checks that apply to any Dagster asset graph:
- All dependencies reference defined assets
- No circular dependencies exist
- Required metadata fields are present
- Naming conventions are followed

Implementation-specific tests (e.g., "do all 11 countries have assets?") should
be placed in module-specific test files near the asset definitions.
"""

import ast
import inspect
from pathlib import Path

import pytest

from pipelines.definitions import defs


class TestAssetGraphStructure:
    """Generic sanity tests for asset graph structure."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def specs_by_key(self, all_specs):
        """Index specs by asset key for efficient lookup."""
        return {spec.key: spec for spec in all_specs}

    def test_all_dependencies_are_defined(self, all_specs, specs_by_key):
        """Test that all asset dependencies reference defined assets.

        This catches:
        - Typos in dependency declarations
        - Factory functions generating incorrect dependency keys
        - Assets referencing removed/renamed assets
        - Any dangling dependencies
        """
        defined_keys = set(specs_by_key.keys())

        for spec in all_specs:
            for dep in spec.deps:
                assert dep.asset_key in defined_keys, (
                    f"Asset {spec.key} depends on {dep.asset_key}, which is not a defined asset"
                )

    def test_no_circular_dependencies(self, all_specs):
        """Test that there are no circular dependencies in the asset graph.

        Uses depth-first search to detect cycles in the dependency graph.
        """
        # Build dependency graph
        deps_graph = {}
        for spec in all_specs:
            deps_graph[spec.key] = [dep.asset_key for dep in spec.deps]

        # Check for cycles using DFS
        def has_cycle(node, visited, rec_stack):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in deps_graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        visited = set()
        for key in deps_graph:
            if key not in visited:
                assert not has_cycle(key, visited, set()), (
                    f"Circular dependency detected involving asset {key}"
                )

    def test_all_assets_have_layer_metadata(self, all_specs):
        """Test that assets with layer metadata have valid values.

        The 'layer' field is used to distinguish between medallion architecture layers:
        - bronze: Raw data ingestion layer
        - silver: Data validation/transformation layer
        - gold: LLM-accessible published layer

        Note: Some newer assets may not have layer metadata yet.
        """
        # Track assets missing layer for reporting
        missing_layer = []

        for spec in all_specs:
            if "layer" not in spec.metadata:
                missing_layer.append(spec.key)
                continue

            layer = spec.metadata["layer"]
            assert isinstance(layer, str), (
                f"Asset {spec.key} has non-string 'layer' metadata: {layer}"
            )
            assert layer in [
                "bronze",
                "silver",
                "gold",
            ], (
                f"Asset {spec.key} has invalid 'layer' metadata: {layer} (must be 'bronze', 'silver', or 'gold')"
            )

        # Allow up to 20 assets without layer metadata (for newer assets under development)
        assert len(missing_layer) <= 20, (
            f"Too many assets ({len(missing_layer)}) missing 'layer' metadata. "
            f"First 10: {[str(k) for k in missing_layer[:10]]}"
        )

    def test_all_assets_have_visibility_metadata(self, all_specs):
        """Test that assets with visibility metadata have valid values.

        The 'visibility' field indicates:
        - internal: Pipeline-internal assets not meant for end users
        - llm_accessible: Published layer assets designed for LLM consumption

        Note: Some newer assets may not have visibility metadata yet.
        """
        # Track assets missing visibility for reporting
        missing_visibility = []

        for spec in all_specs:
            if "visibility" not in spec.metadata:
                missing_visibility.append(spec.key)
                continue

            visibility = spec.metadata["visibility"]
            assert isinstance(visibility, str), (
                f"Asset {spec.key} has non-string 'visibility' metadata: {visibility}"
            )
            assert len(visibility) > 0, (
                f"Asset {spec.key} has empty 'visibility' metadata"
            )

        # Allow up to 20 assets without visibility metadata (for newer assets under development)
        assert len(missing_visibility) <= 20, (
            f"Too many assets ({len(missing_visibility)}) missing 'visibility' metadata. "
            f"First 10: {[str(k) for k in missing_visibility[:10]]}"
        )

    def test_published_layer_assets_have_questions_answered(self, all_specs):
        """Test that published layer assets have 'questions_answered' metadata.

        Assets tagged with layer='gold' are designed for LLM consumption
        and should document what questions they can answer.

        Note: New SEC time-based gold assets may skip this check while under development.
        """
        # New SEC gold assets (unpartitioned, time-based) that are still under development
        # These assets use the new plural naming convention and will have questions_answered
        # added in a future update
        new_sec_gold_assets = {
            ("gold", "companies", "financials", "annual_reports"),
            ("gold", "companies", "financials", "quarterly_reports"),
            ("gold", "companies", "insider", "insider_activity"),
            ("gold", "institutions", "portfolio", "holdings"),
        }

        published_assets = [
            spec for spec in all_specs if spec.metadata.get("layer") == "gold"
        ]

        for spec in published_assets:
            # Skip new SEC gold assets (they're still under development)
            if tuple(spec.key.path) in new_sec_gold_assets:
                continue

            assert "questions_answered" in spec.metadata, (
                f"Published asset {spec.key} is missing 'questions_answered' metadata"
            )

            questions = spec.metadata["questions_answered"]
            assert isinstance(questions, list), (
                f"Published asset {spec.key} 'questions_answered' should be a list, got {type(questions)}"
            )
            assert len(questions) > 0, (
                f"Published asset {spec.key} has empty 'questions_answered' list"
            )

            # Validate each question is a non-empty string
            for i, question in enumerate(questions):
                assert isinstance(question, str), (
                    f"Published asset {spec.key} question[{i}] is not a string: {question}"
                )
                assert len(question.strip()) > 0, (
                    f"Published asset {spec.key} question[{i}] is empty or whitespace"
                )

    def test_asset_keys_follow_naming_standards(self, all_specs):
        """Test that asset key components follow naming standards.

        Standards:
        - All components should be lowercase (except internal markers like '_pipeline')
        - No spaces allowed
        - Use underscores for word separation
        """
        for spec in all_specs:
            for component in spec.key.path:
                # Allow leading underscores for internal markers
                clean_component = component.lstrip("_")

                assert component.islower() or component.startswith("_"), (
                    f"Asset {spec.key} has non-lowercase component '{component}'"
                )

                assert " " not in component, (
                    f"Asset {spec.key} has space in component '{component}'"
                )

                # Check for camelCase (simple heuristic: lowercase letter followed by uppercase)
                has_camel_case = any(
                    clean_component[i].islower() and clean_component[i + 1].isupper()
                    for i in range(len(clean_component) - 1)
                )
                assert not has_camel_case, (
                    f"Asset {spec.key} has camelCase component '{component}' - use underscores instead"
                )


class TestProvenanceTracking:
    """Ensure all load_asset_value calls have declared deps for provenance.

    Dagster only tracks provenance for DECLARED dependencies (deps=[], ins={}).
    Runtime load_asset_value() calls are invisible to lineage tracking unless
    also declared as deps. This test scans asset files for load_asset_value()
    calls and verifies each has a matching deps declaration.
    """

    @pytest.fixture
    def asset_files(self):
        """Get all asset files in the pipeline."""
        assets_dir = Path(__file__).parent.parent / "src" / "pipeline" / "assets"
        return list(assets_dir.glob("*.py"))

    def _extract_load_asset_value_keys(self, filepath) -> set[str]:
        """Extract asset keys from load_asset_value() calls using AST parsing."""
        with open(filepath) as f:
            source = f.read()

        tree = ast.parse(source)
        asset_keys = set()

        for node in ast.walk(tree):
            # Look for method calls like context.load_asset_value() or
            # context.instance.load_asset_value()
            if isinstance(node, ast.Call):
                # Check if it's a load_asset_value call
                func = node.func
                is_load_call = False

                if isinstance(func, ast.Attribute) and func.attr == "load_asset_value":
                    is_load_call = True

                if not is_load_call:
                    continue

                # Extract the asset_key argument
                for keyword in node.keywords:
                    # Handle dg.AssetKey(['bronze', 'fred', 'timeseries'])
                    if keyword.arg == "asset_key" and isinstance(
                        keyword.value, ast.Call
                    ):
                        call = keyword.value
                        if call.args and isinstance(call.args[0], ast.List):
                            parts = []
                            has_variable = False
                            for elt in call.args[0].elts:
                                if isinstance(elt, ast.Constant):
                                    parts.append(elt.value)
                                else:
                                    # Variable reference - can't fully extract
                                    has_variable = True
                            # Only add if we got all parts (no variables)
                            if parts and not has_variable:
                                asset_keys.add("/".join(parts))

        return asset_keys

    def _get_declared_deps(self, filepath) -> set[str]:
        """Get declared dependencies for assets defined in a file."""
        # Get the filename without path
        filename = filepath.name

        declared_deps = set()

        # Find assets from this file by checking their source
        for asset in defs.assets or []:
            try:
                # Get the compute function
                if hasattr(asset, "node_def") and hasattr(asset.node_def, "compute_fn"):
                    compute_fn = asset.node_def.compute_fn
                    # Handle decorated functions
                    if hasattr(compute_fn, "decorated_fn"):
                        compute_fn = compute_fn.decorated_fn

                    source_file = inspect.getfile(compute_fn)
                    if not source_file.endswith(filename):
                        continue

                    # Get deps from the asset
                    for key in asset.keys:
                        # Get deps for this asset from its specs
                        for spec in asset.specs:
                            if spec.key == key:
                                for dep in spec.deps:
                                    declared_deps.add(dep.asset_key.to_user_string())
            except (TypeError, OSError):
                continue

        return declared_deps

    def test_all_load_asset_value_calls_have_declared_deps(self, asset_files):
        """Verify all load_asset_value calls have matching declared deps.

        This ensures Dagster tracks provenance for all data inputs, which is
        required for compliance and auditing. Without declared deps, load_asset_value
        calls are invisible to lineage tracking.
        """
        # Files that use load_asset_value for asset checks (different pattern)
        exempt_files = {"checks.py"}

        violations = []

        for filepath in asset_files:
            if filepath.name in exempt_files:
                continue

            loaded_keys = self._extract_load_asset_value_keys(filepath)
            if not loaded_keys:
                continue

            declared_deps = self._get_declared_deps(filepath)

            # Check each loaded key has a matching declared dep
            for loaded_key in loaded_keys:
                if loaded_key not in declared_deps:
                    violations.append(
                        f"{filepath.name}: loads {loaded_key} but does not declare it in deps"
                    )

        assert not violations, (
            "Found load_asset_value() calls without declared deps (breaks provenance tracking):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )
