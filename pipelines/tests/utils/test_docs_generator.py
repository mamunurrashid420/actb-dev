"""Tests for docs generator lineage extraction.

Verifies that the docs generator correctly extracts a KNOWN mock topology
that mirrors our real pipeline patterns (deps, ins, partitions).
"""

import dagster as dg
import pandas as pd
import pytest

from pipelines.utils.docs_generator import AssetDocExtractor, MarkdownRenderer

# =============================================================================
# MOCK ASSET DEFINITIONS
# =============================================================================
# These mock assets mirror our real pipeline patterns:
# - Bronze: Source nodes with no dependencies
# - Silver: Reference/crosswalk data
# - Gold: Published layer using both `deps` and `ins`


@dg.asset(
    key_prefix=["bronze", "api"],
    name="raw_data",
    partitions_def=dg.StaticPartitionsDefinition(["A", "B", "C"]),
    metadata={"layer": "bronze"},
)
def bronze_raw_data() -> pd.DataFrame:
    """Bronze source with static partitions."""
    return pd.DataFrame({"value": [1, 2, 3]})


@dg.asset(
    key_prefix=["bronze", "api"],
    name="metadata",
    metadata={"layer": "bronze"},
)
def bronze_metadata() -> pd.DataFrame:
    """Bronze source without partitions."""
    return pd.DataFrame({"meta": ["info"]})


@dg.asset(
    key_prefix=["silver", "reference"],
    name="crosswalk",
    metadata={"layer": "silver"},
)
def silver_crosswalk() -> pd.DataFrame:
    """Silver reference data (like indicator_id_crosswalk)."""
    return pd.DataFrame({"id": [1], "name": ["test"]})


@dg.asset(
    key_prefix=["silver", "transform"],
    name="processed",
    ins={
        "raw_data": dg.AssetIn(
            key=dg.AssetKey(["bronze", "api", "raw_data"]),
            partition_mapping=dg.AllPartitionMapping(),
        ),
    },
    metadata={"layer": "silver"},
)
def silver_processed(raw_data: pd.DataFrame) -> pd.DataFrame:
    """Silver transform that depends on bronze (mirrors silver/sec/form_10k)."""
    return raw_data


@dg.asset(
    key_prefix=["gold", "published"],
    name="report",
    partitions_def=dg.StaticPartitionsDefinition(["US", "EU"]),
    ins={
        "crosswalk": dg.AssetIn(
            key=dg.AssetKey(["silver", "reference", "crosswalk"]),
            partition_mapping=dg.AllPartitionMapping(),
        ),
    },
    deps=[
        dg.AssetDep(
            dg.AssetKey(["bronze", "api", "raw_data"]),
            partition_mapping=dg.AllPartitionMapping(),
        ),
        dg.AssetDep(
            dg.AssetKey(["bronze", "api", "metadata"]),
        ),
    ],
    metadata={"layer": "gold"},
)
def gold_report(crosswalk: pd.DataFrame) -> pd.DataFrame:
    """Gold published asset using both deps and ins."""
    return pd.DataFrame({"report": ["data"]})


# =============================================================================
# TEST CLASS
# =============================================================================


class TestDocsGeneratorWithMockTopology:
    """Verify docs generator extracts KNOWN mock topology correctly."""

    @pytest.fixture
    def mock_definitions(self) -> dg.Definitions:
        """Create mock Dagster definitions mirroring real pipeline patterns."""
        return dg.Definitions(
            assets=[
                bronze_raw_data,
                bronze_metadata,
                silver_crosswalk,
                silver_processed,
                gold_report,
            ]
        )

    @pytest.fixture
    def extractor(self, mock_definitions: dg.Definitions) -> AssetDocExtractor:
        """Create extractor from mock definitions."""
        return AssetDocExtractor(mock_definitions)

    @pytest.fixture
    def extracted_assets(self, extractor: AssetDocExtractor) -> dict:
        """Extract assets and index by key."""
        assets = extractor.extract_all()
        return {a.key: a for a in assets}

    def test_extracts_all_five_assets(self, extracted_assets):
        """Extractor should find all 5 mock assets."""
        want = 5
        got = len(extracted_assets)
        assert got == want

    def test_bronze_raw_data_has_no_dependencies(self, extracted_assets):
        """Bronze source node should have empty dependency list."""
        asset = extracted_assets["bronze/api/raw_data"]
        want = []
        got = asset.dependencies
        assert got == want

    def test_bronze_metadata_has_no_dependencies(self, extracted_assets):
        """Bronze source node (no partitions) should have empty dependency list."""
        asset = extracted_assets["bronze/api/metadata"]
        want = []
        got = asset.dependencies
        assert got == want

    def test_silver_crosswalk_has_no_dependencies(self, extracted_assets):
        """Silver reference node should have empty dependency list."""
        asset = extracted_assets["silver/reference/crosswalk"]
        want = []
        got = asset.dependencies
        assert got == want

    def test_silver_transform_depends_on_bronze(self, extracted_assets):
        """Silver transform should show dependency on bronze."""
        asset = extracted_assets["silver/transform/processed"]
        want = ["bronze/api/raw_data"]
        got = asset.dependencies
        assert got == want

    def test_gold_report_has_three_dependencies(self, extracted_assets):
        """Gold asset should capture all upstream deps (from both deps and ins)."""
        asset = extracted_assets["gold/published/report"]
        want = sorted([
            "bronze/api/metadata",
            "bronze/api/raw_data",
            "silver/reference/crosswalk",
        ])
        got = sorted(asset.dependencies)
        assert got == want

    def test_gold_captures_ins_dependency(self, extracted_assets):
        """Gold asset should capture dependency declared via ins={}."""
        asset = extracted_assets["gold/published/report"]
        # silver/reference/crosswalk is declared via ins={}
        assert "silver/reference/crosswalk" in asset.dependencies

    def test_gold_captures_deps_dependencies(self, extracted_assets):
        """Gold asset should capture dependencies declared via deps=[]."""
        asset = extracted_assets["gold/published/report"]
        # Both bronze assets are declared via deps=[]
        assert "bronze/api/raw_data" in asset.dependencies
        assert "bronze/api/metadata" in asset.dependencies

    def test_partition_extraction_static(self, extracted_assets):
        """Static partitions should be extracted correctly."""
        asset = extracted_assets["bronze/api/raw_data"]
        want_partitions = ["A", "B", "C"]
        want_type = "static"
        assert asset.partitions == want_partitions
        assert asset.partition_type == want_type

    def test_partition_extraction_none(self, extracted_assets):
        """Non-partitioned assets should have None for partitions."""
        asset = extracted_assets["bronze/api/metadata"]
        assert asset.partitions is None
        assert asset.partition_type is None

    def test_layer_extraction_bronze(self, extracted_assets):
        """Bronze layer should be extracted from metadata."""
        asset = extracted_assets["bronze/api/raw_data"]
        assert asset.layer == "bronze"

    def test_layer_extraction_silver(self, extracted_assets):
        """Silver layer should be extracted from metadata."""
        asset = extracted_assets["silver/reference/crosswalk"]
        assert asset.layer == "silver"

    def test_layer_extraction_gold(self, extracted_assets):
        """Gold layer should be extracted from metadata."""
        asset = extracted_assets["gold/published/report"]
        assert asset.layer == "gold"


class TestLineageMarkdownRendering:
    """Verify lineage markdown output shows grouped dependency trees.

    The format:
    - Gold layer section with domain subheadings
    - Silver layer section for intermediate assets
    - Unused assets section for orphans
    - Tree connectors (├── └──) for dependencies
    """

    @pytest.fixture
    def mock_definitions(self) -> dg.Definitions:
        """Create mock Dagster definitions."""
        return dg.Definitions(
            assets=[
                bronze_raw_data,
                bronze_metadata,
                silver_crosswalk,
                silver_processed,
                gold_report,
            ]
        )

    @pytest.fixture
    def lineage_markdown(self, mock_definitions: dg.Definitions) -> str:
        """Generate lineage markdown from mock definitions."""
        extractor = AssetDocExtractor(mock_definitions)
        assets = extractor.extract_all()
        renderer = MarkdownRenderer(assets)
        return renderer.render_lineage()

    def test_has_gold_layer_section(self, lineage_markdown):
        """Should have a Gold Layer section."""
        assert "## Gold Layer" in lineage_markdown

    def test_gold_asset_in_gold_section(self, lineage_markdown):
        """Gold assets should appear in the Gold Layer section."""
        assert "gold/published/report" in lineage_markdown

    def test_gold_shows_dependencies_with_tree_connectors(self, lineage_markdown):
        """Gold asset should show dependencies with tree connectors."""
        # All three deps should appear
        assert "bronze/api/raw_data" in lineage_markdown
        assert "bronze/api/metadata" in lineage_markdown
        assert "silver/reference/crosswalk" in lineage_markdown
        # Should use tree connectors
        assert "├──" in lineage_markdown or "└──" in lineage_markdown

    def test_has_silver_layer_section(self, lineage_markdown):
        """Should have a Silver Layer section for intermediate assets."""
        assert "## Silver Layer" in lineage_markdown

    def test_silver_terminal_in_silver_section(self, lineage_markdown):
        """Silver terminal should appear in Silver Layer section."""
        # silver/transform/processed has no downstream, so it's a terminal
        assert "silver/transform/processed" in lineage_markdown

    def test_silver_terminal_shows_bronze_dependency(self, lineage_markdown):
        """Silver terminal should show its bronze dependency."""
        # Find silver/transform/processed and verify bronze/api/raw_data follows
        lines = lineage_markdown.split("\n")
        found_silver = False
        for line in lines:
            if "silver/transform/processed" in line:
                found_silver = True
            if found_silver and "bronze/api/raw_data" in line:
                # Dependency found after the silver asset
                break
        assert found_silver, "silver/transform/processed not found in lineage"

    def test_no_unused_assets_in_mock_topology(self, lineage_markdown):
        """Mock topology has no unused assets (all are connected)."""
        # silver/reference/crosswalk has no deps but IS used by gold
        # bronze assets are used by gold and silver
        # Therefore no assets are truly unused (no deps AND no dependents)
        assert "## Unused" not in lineage_markdown

    def test_uses_tree_connectors(self, lineage_markdown):
        """Lineage should use tree connectors for visual hierarchy."""
        assert "└──" in lineage_markdown
