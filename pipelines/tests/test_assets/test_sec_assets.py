"""Tests for SEC asset structure and metadata.

Tests validate that SEC assets have proper naming, metadata, and structure
without making actual SEC API calls.
"""

import dagster as dg
import pytest

from pipelines.definitions import defs


class TestSecBronzeAssets:
    """Tests for SEC bronze layer assets."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def sec_bronze_specs(self, all_specs):
        """Get only SEC bronze asset specs, excluding auto-created stubs."""
        return [
            spec
            for spec in all_specs
            if len(spec.key.path) >= 2
            and spec.key.path[:2] == ["bronze", "sec"]
            and not spec.metadata.get("dagster/auto_created_stub_asset", False)
        ]

    @pytest.fixture
    def sec_bronze_registry_specs(self, sec_bronze_specs):
        """Get only registry assets."""
        return [spec for spec in sec_bronze_specs if "registry" in spec.key.path[-1]]

    @pytest.fixture
    def sec_bronze_form_specs(self, sec_bronze_specs):
        """Get only form-specific assets (exclude registry and bulk downloads)."""
        # Exclude: registry, company_facts*, submissions* (bulk downloads are unpartitioned)
        excluded_suffixes = [
            "registry",
            "company_facts",
            "company_facts_download",
            "submissions",
            "submissions_download",
        ]
        return [
            spec
            for spec in sec_bronze_specs
            if not any(suffix in spec.key.path[-1] for suffix in excluded_suffixes)
        ]

    @pytest.fixture
    def sec_bronze_bulk_download_specs(self, sec_bronze_specs):
        """Get only bulk download assets (download + parse)."""
        bulk_suffixes = [
            "company_facts",
            "company_facts_download",
            "submissions",
            "submissions_download",
        ]
        return [
            spec
            for spec in sec_bronze_specs
            if any(spec.key.path[-1] == suffix for suffix in bulk_suffixes)
        ]

    def test_sec_bronze_registry_exists(self, sec_bronze_specs):
        """Test that sec_filer_registry bronze asset exists."""
        keys = [spec.key for spec in sec_bronze_specs]
        expected_key = dg.AssetKey(["bronze", "sec", "sec_filer_registry"])
        assert expected_key in keys, "Missing bronze/sec/sec_filer_registry asset"

    def test_sec_bronze_form_10k_text_exists(self, sec_bronze_specs):
        """Test that form_10k_text bronze asset exists."""
        keys = [spec.key for spec in sec_bronze_specs]
        expected_key = dg.AssetKey(["bronze", "sec", "form_10k_text"])
        assert expected_key in keys, "Missing bronze/sec/form_10k_text asset"

    def test_sec_bronze_form_10q_text_exists(self, sec_bronze_specs):
        """Test that form_10q_text bronze asset exists."""
        keys = [spec.key for spec in sec_bronze_specs]
        expected_key = dg.AssetKey(["bronze", "sec", "form_10q_text"])
        assert expected_key in keys, "Missing bronze/sec/form_10q_text asset"

    def test_sec_bronze_form_13f_exists(self, sec_bronze_specs):
        """Test that form_13f bronze asset exists."""
        keys = [spec.key for spec in sec_bronze_specs]
        expected_key = dg.AssetKey(["bronze", "sec", "form_13f"])
        assert expected_key in keys, "Missing bronze/sec/form_13f asset"

    def test_sec_bronze_form_4_exists(self, sec_bronze_specs):
        """Test that form_4 bronze asset exists."""
        keys = [spec.key for spec in sec_bronze_specs]
        expected_key = dg.AssetKey(["bronze", "sec", "form_4"])
        assert expected_key in keys, "Missing bronze/sec/form_4 asset"

    def test_sec_bronze_form_assets_are_partitioned(self, sec_bronze_form_specs):
        """Test that SEC bronze form assets (10-K, 10-Q, 4, 13-F) are partitioned."""
        form_assets = [
            "form_10k_text",
            "form_10q_text",
            "form_4",
            "form_13f",
        ]
        for spec in sec_bronze_form_specs:
            asset_name = spec.key.path[-1]
            if asset_name in form_assets:
                assert spec.partitions_def is not None, (
                    f"SEC bronze form asset {spec.key} should be partitioned"
                )

    def test_sec_bronze_registry_is_unpartitioned(self, sec_bronze_registry_specs):
        """Test that registry assets are unpartitioned."""
        for spec in sec_bronze_registry_specs:
            assert spec.partitions_def is None, (
                f"SEC bronze registry asset {spec.key} should be unpartitioned"
            )

    def test_sec_bronze_bulk_download_assets_exist(self, sec_bronze_specs):
        """Test that bulk download assets exist."""
        keys = [spec.key for spec in sec_bronze_specs]

        # Download checkpoint assets
        assert dg.AssetKey(["bronze", "sec", "company_facts_download"]) in keys
        assert dg.AssetKey(["bronze", "sec", "submissions_download"]) in keys

        # Submissions parse asset (company_facts is now in silver layer)
        assert dg.AssetKey(["bronze", "sec", "submissions"]) in keys

    def test_sec_bronze_bulk_download_assets_are_unpartitioned(
        self, sec_bronze_bulk_download_specs
    ):
        """Test that bulk download assets are unpartitioned."""
        for spec in sec_bronze_bulk_download_specs:
            assert spec.partitions_def is None, (
                f"SEC bronze bulk download asset {spec.key} should be unpartitioned"
            )

    def test_sec_bronze_assets_have_required_metadata(self, sec_bronze_specs):
        """Test that SEC bronze assets have required metadata fields."""
        required_fields = ["layer", "source"]

        for spec in sec_bronze_specs:
            for field in required_fields:
                assert field in spec.metadata, (
                    f'SEC bronze asset {spec.key} missing required metadata field "{field}"'
                )

            assert spec.metadata["layer"] == "bronze", (
                f'SEC bronze asset {spec.key} should have layer="bronze"'
            )

            # Visibility is recommended but optional for some newer assets
            if "visibility" in spec.metadata:
                assert spec.metadata["visibility"] == "internal", (
                    f'SEC bronze asset {spec.key} should have visibility="internal"'
                )

            # Source should be sec_edgar, sec_dera (for bulk downloads), or fasb (for xbrl_taxonomy)
            allowed_sources = ["sec_edgar", "sec_dera", "fasb"]
            assert spec.metadata["source"] in allowed_sources, (
                f"SEC bronze asset {spec.key} has unexpected source={spec.metadata['source']}"
            )

    def test_sec_bronze_form_assets_have_form_type_metadata(
        self, sec_bronze_form_specs
    ):
        """Test that SEC bronze form assets have form_type in metadata."""
        # Only check assets that are actual form filings
        form_assets = ["form_10k_text", "form_10q_text", "form_4", "form_13f"]
        expected_types = ["10-K", "10-Q", "13-F", "4"]

        for spec in sec_bronze_form_specs:
            asset_name = spec.key.path[-1]
            if asset_name in form_assets:
                assert "form_type" in spec.metadata, (
                    f"SEC bronze asset {spec.key} should have form_type metadata"
                )

                form_type = spec.metadata["form_type"]
                assert form_type in expected_types, (
                    f"SEC bronze asset {spec.key} has unexpected form_type: {form_type}"
                )


class TestSecSilverAssets:
    """Tests for SEC silver layer assets."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def sec_silver_specs(self, all_specs):
        """Get only SEC silver asset specs."""
        return [
            spec
            for spec in all_specs
            if len(spec.key.path) >= 2 and spec.key.path[:2] == ["silver", "sec"]
        ]

    @pytest.fixture
    def sec_silver_registry_specs(self, sec_silver_specs):
        """Get only registry assets."""
        return [spec for spec in sec_silver_specs if "registry" in spec.key.path[-1]]

    def test_sec_silver_company_registry_exists(self, sec_silver_specs):
        """Test that company_registry silver asset exists."""
        keys = [spec.key for spec in sec_silver_specs]
        expected_key = dg.AssetKey(["silver", "sec", "company_registry"])
        assert expected_key in keys, "Missing silver/sec/company_registry asset"

    def test_sec_silver_institution_registry_exists(self, sec_silver_specs):
        """Test that institution_registry silver asset exists."""
        keys = [spec.key for spec in sec_silver_specs]
        expected_key = dg.AssetKey(["silver", "sec", "institution_registry"])
        assert expected_key in keys, "Missing silver/sec/institution_registry asset"

    def test_sec_silver_form_10k_sections_exists(self, sec_silver_specs):
        """Test that form_10k_sections silver asset exists."""
        keys = [spec.key for spec in sec_silver_specs]
        expected_key = dg.AssetKey(["silver", "sec", "form_10k_sections"])
        assert expected_key in keys, "Missing silver/sec/form_10k_sections asset"

    def test_sec_silver_form_10q_sections_exists(self, sec_silver_specs):
        """Test that form_10q_sections silver asset exists."""
        keys = [spec.key for spec in sec_silver_specs]
        expected_key = dg.AssetKey(["silver", "sec", "form_10q_sections"])
        assert expected_key in keys, "Missing silver/sec/form_10q_sections asset"

    def test_sec_silver_form_13f_holdings_exists(self, sec_silver_specs):
        """Test that form_13f_holdings silver asset exists."""
        keys = [spec.key for spec in sec_silver_specs]
        expected_key = dg.AssetKey(["silver", "sec", "form_13f_holdings"])
        assert expected_key in keys, "Missing silver/sec/form_13f_holdings asset"

    def test_sec_silver_form_4_transactions_exists(self, sec_silver_specs):
        """Test that form_4_transactions silver asset exists."""
        keys = [spec.key for spec in sec_silver_specs]
        expected_key = dg.AssetKey(["silver", "sec", "form_4_transactions"])
        assert expected_key in keys, "Missing silver/sec/form_4_transactions asset"

    def test_sec_silver_assets_have_required_metadata(self, sec_silver_specs):
        """Test that SEC silver assets have required metadata fields."""
        required_fields = ["layer"]

        for spec in sec_silver_specs:
            for field in required_fields:
                assert field in spec.metadata, (
                    f'SEC silver asset {spec.key} missing required metadata field "{field}"'
                )

            assert spec.metadata["layer"] == "silver", (
                f'SEC silver asset {spec.key} should have layer="silver"'
            )

            # Visibility is recommended but optional for some newer assets
            if "visibility" in spec.metadata:
                assert spec.metadata["visibility"] == "internal", (
                    f'SEC silver asset {spec.key} should have visibility="internal"'
                )


class TestSecGoldAssets:
    """Tests for SEC gold (LLM-accessible) layer assets."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def sec_gold_specs(self, all_specs):
        """Get SEC gold asset specs (gold/companies/* and gold/institutions/*)."""
        return [
            spec
            for spec in all_specs
            if (
                len(spec.key.path) >= 2
                and spec.key.path[0] == "gold"
                and spec.key.path[1] in ["companies", "institutions"]
                and spec.metadata.get("layer") == "gold"
            )
        ]

    def test_annual_reports_exists(self, all_specs):
        """Test that annual_reports gold asset exists."""
        keys = [spec.key for spec in all_specs]
        expected_key = dg.AssetKey([
            "gold",
            "companies",
            "financials",
            "annual_reports",
        ])
        assert expected_key in keys, (
            "Missing gold/companies/financials/annual_reports asset"
        )

    def test_quarterly_reports_exists(self, all_specs):
        """Test that quarterly_reports gold asset exists."""
        keys = [spec.key for spec in all_specs]
        expected_key = dg.AssetKey([
            "gold",
            "companies",
            "financials",
            "quarterly_reports",
        ])
        assert expected_key in keys, (
            "Missing gold/companies/financials/quarterly_reports asset"
        )

    def test_insider_activity_exists(self, all_specs):
        """Test that insider_activity gold asset exists."""
        keys = [spec.key for spec in all_specs]
        expected_key = dg.AssetKey(["gold", "companies", "insider", "insider_activity"])
        assert expected_key in keys, (
            "Missing gold/companies/insider/insider_activity asset"
        )

    def test_portfolio_holdings_exists(self, all_specs):
        """Test that holdings gold asset exists."""
        keys = [spec.key for spec in all_specs]
        expected_key = dg.AssetKey(["gold", "institutions", "portfolio", "holdings"])
        assert expected_key in keys, (
            "Missing gold/institutions/portfolio/holdings asset"
        )

    def test_sec_gold_assets_have_required_metadata(self, sec_gold_specs):
        """Test that SEC gold assets have required metadata fields."""
        # Note: questions_answered is recommended but optional for new assets
        required_fields = ["layer", "visibility"]

        for spec in sec_gold_specs:
            # Skip non-SEC gold assets
            if (
                "sec" not in str(spec.key).lower()
                and "annual" not in str(spec.key).lower()
                and "quarterly" not in str(spec.key).lower()
                and "insider" not in str(spec.key).lower()
                and "portfolio" not in str(spec.key).lower()
                and "holdings" not in str(spec.key).lower()
            ):
                continue

            for field in required_fields:
                assert field in spec.metadata, (
                    f'SEC gold asset {spec.key} missing required metadata field "{field}"'
                )

            assert spec.metadata["layer"] == "gold", (
                f'SEC gold asset {spec.key} should have layer="gold"'
            )

            assert spec.metadata["visibility"] == "llm_accessible", (
                f'SEC gold asset {spec.key} should have visibility="llm_accessible"'
            )

    def test_sec_gold_assets_have_questions_answered(self, sec_gold_specs):
        """Test that SEC gold assets have non-empty questions_answered when present."""
        for spec in sec_gold_specs:
            # Skip non-SEC gold assets
            if (
                "sec" not in str(spec.key).lower()
                and "annual" not in str(spec.key).lower()
                and "quarterly" not in str(spec.key).lower()
                and "insider" not in str(spec.key).lower()
                and "portfolio" not in str(spec.key).lower()
                and "holdings" not in str(spec.key).lower()
            ):
                continue

            # If questions_answered is present, it should be a non-empty list
            if "questions_answered" in spec.metadata:
                questions = spec.metadata["questions_answered"]
                assert isinstance(questions, list), (
                    f"SEC gold asset {spec.key} questions_answered should be a list"
                )
                assert len(questions) > 0, (
                    f"SEC gold asset {spec.key} should have at least one question"
                )


class TestSecAssetLayering:
    """Tests for SEC asset layer structure and dependencies."""

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

    def test_form_10q_medallion_layers_exist(self, all_specs):
        """Test that all 3 medallion layers exist for Form 10-Q."""
        keys = [spec.key for spec in all_specs]

        assert dg.AssetKey(["bronze", "sec", "form_10q_text"]) in keys
        assert dg.AssetKey(["silver", "sec", "form_10q_sections"]) in keys
        assert (
            dg.AssetKey(["gold", "companies", "financials", "quarterly_reports"])
            in keys
        )

    def test_form_13f_medallion_layers_exist(self, all_specs):
        """Test that all 3 medallion layers exist for Form 13-F."""
        keys = [spec.key for spec in all_specs]

        assert dg.AssetKey(["bronze", "sec", "form_13f"]) in keys
        assert dg.AssetKey(["silver", "sec", "form_13f_holdings"]) in keys
        assert dg.AssetKey(["gold", "institutions", "portfolio", "holdings"]) in keys

    def test_form_4_medallion_layers_exist(self, all_specs):
        """Test that all 3 medallion layers exist for Form 4."""
        keys = [spec.key for spec in all_specs]

        assert dg.AssetKey(["bronze", "sec", "form_4"]) in keys
        assert dg.AssetKey(["silver", "sec", "form_4_transactions"]) in keys
        assert dg.AssetKey(["gold", "companies", "insider", "insider_activity"]) in keys

    def test_registry_layers_exist(self, all_specs):
        """Test that registry assets exist at bronze and silver layers."""
        keys = [spec.key for spec in all_specs]

        # Bronze registry
        assert dg.AssetKey(["bronze", "sec", "sec_filer_registry"]) in keys

        # Silver registries
        assert dg.AssetKey(["silver", "sec", "company_registry"]) in keys
        assert dg.AssetKey(["silver", "sec", "institution_registry"]) in keys
