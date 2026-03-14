"""Tests for Form 4 insider trading assets.

Tests validate that Form 4 assets have proper naming, partitioning, metadata,
and dependencies without making actual SEC API calls.
"""

import dagster as dg
import pytest

from pipelines.assets.sec.form_4 import parse_form4_xml
from pipelines.definitions import defs
from pipelines.partitions import sec_monthly_partitions


class TestForm4XmlParsing:
    """Tests for Form 4 XML parsing helper function."""

    def test_parse_form4_xml_extracts_basic_info(self):
        """Test that parse_form4_xml extracts issuer and owner information."""
        xml_content = """<?xml version="1.0"?>
        <ownershipDocument>
            <issuer>
                <issuerCik>0000320193</issuerCik>
                <issuerName>Apple Inc</issuerName>
                <issuerTradingSymbol>AAPL</issuerTradingSymbol>
            </issuer>
            <reportingOwner>
                <reportingOwnerId>
                    <rptOwnerCik>0001234567</rptOwnerCik>
                    <rptOwnerName>John Doe</rptOwnerName>
                </reportingOwnerId>
                <reportingOwnerRelationship>
                    <isDirector>1</isDirector>
                    <isOfficer>0</isOfficer>
                </reportingOwnerRelationship>
            </reportingOwner>
            <nonDerivativeTable>
                <nonDerivativeTransaction>
                    <transactionDate><value>2024-01-15</value></transactionDate>
                    <transactionCoding>
                        <transactionCode>P</transactionCode>
                    </transactionCoding>
                    <transactionAmounts>
                        <transactionShares><value>1000</value></transactionShares>
                        <transactionPricePerShare><value>185.50</value></transactionPricePerShare>
                    </transactionAmounts>
                </nonDerivativeTransaction>
            </nonDerivativeTable>
        </ownershipDocument>
        """

        transactions = parse_form4_xml(xml_content)

        # Should return a list with one transaction
        assert len(transactions) == 1

        txn = transactions[0]
        assert txn["issuer_cik"] == "0000320193"
        assert txn["issuer_name"] == "Apple Inc"
        assert txn["issuer_ticker"] == "AAPL"
        assert txn["owner_cik"] == "0001234567"
        assert txn["owner_name"] == "John Doe"
        assert txn["insider_title"] == "Director"
        assert txn["transaction_date"] == "2024-01-15"
        assert txn["transaction_code"] == "P"
        assert txn["shares"] == 1000.0
        assert txn["price_per_share"] == 185.50
        assert txn["total_value"] == 185500.0

    def test_parse_form4_xml_handles_officer_title(self):
        """Test that parse_form4_xml extracts officer titles."""
        xml_content = """<?xml version="1.0"?>
        <ownershipDocument>
            <issuer>
                <issuerCik>0000320193</issuerCik>
                <issuerName>Apple Inc</issuerName>
                <issuerTradingSymbol>AAPL</issuerTradingSymbol>
            </issuer>
            <reportingOwner>
                <reportingOwnerId>
                    <rptOwnerCik>0001234567</rptOwnerCik>
                    <rptOwnerName>Jane Smith</rptOwnerName>
                </reportingOwnerId>
                <reportingOwnerRelationship>
                    <isDirector>0</isDirector>
                    <isOfficer>1</isOfficer>
                    <officerTitle>Chief Financial Officer</officerTitle>
                </reportingOwnerRelationship>
            </reportingOwner>
            <nonDerivativeTable>
                <nonDerivativeTransaction>
                    <transactionDate><value>2024-01-15</value></transactionDate>
                    <transactionCoding>
                        <transactionCode>S</transactionCode>
                    </transactionCoding>
                    <transactionAmounts>
                        <transactionShares><value>500</value></transactionShares>
                        <transactionPricePerShare><value>190.00</value></transactionPricePerShare>
                    </transactionAmounts>
                </nonDerivativeTransaction>
            </nonDerivativeTable>
        </ownershipDocument>
        """

        transactions = parse_form4_xml(xml_content)

        assert len(transactions) == 1
        assert transactions[0]["insider_title"] == "Chief Financial Officer"

    def test_parse_form4_xml_handles_multiple_transactions(self):
        """Test that parse_form4_xml extracts multiple transactions."""
        xml_content = """<?xml version="1.0"?>
        <ownershipDocument>
            <issuer>
                <issuerCik>0000789019</issuerCik>
                <issuerName>Microsoft Corporation</issuerName>
                <issuerTradingSymbol>MSFT</issuerTradingSymbol>
            </issuer>
            <reportingOwner>
                <reportingOwnerId>
                    <rptOwnerCik>0001234567</rptOwnerCik>
                    <rptOwnerName>John Doe</rptOwnerName>
                </reportingOwnerId>
                <reportingOwnerRelationship>
                    <isDirector>1</isDirector>
                    <isOfficer>1</isOfficer>
                    <officerTitle>CEO</officerTitle>
                </reportingOwnerRelationship>
            </reportingOwner>
            <nonDerivativeTable>
                <nonDerivativeTransaction>
                    <transactionDate><value>2024-01-15</value></transactionDate>
                    <transactionCoding>
                        <transactionCode>P</transactionCode>
                    </transactionCoding>
                    <transactionAmounts>
                        <transactionShares><value>1000</value></transactionShares>
                        <transactionPricePerShare><value>100.00</value></transactionPricePerShare>
                    </transactionAmounts>
                </nonDerivativeTransaction>
                <nonDerivativeTransaction>
                    <transactionDate><value>2024-01-16</value></transactionDate>
                    <transactionCoding>
                        <transactionCode>S</transactionCode>
                    </transactionCoding>
                    <transactionAmounts>
                        <transactionShares><value>500</value></transactionShares>
                        <transactionPricePerShare><value>105.00</value></transactionPricePerShare>
                    </transactionAmounts>
                </nonDerivativeTransaction>
            </nonDerivativeTable>
        </ownershipDocument>
        """

        transactions = parse_form4_xml(xml_content)

        assert len(transactions) == 2
        assert transactions[0]["transaction_code"] == "P"
        assert transactions[0]["shares"] == 1000.0
        assert transactions[1]["transaction_code"] == "S"
        assert transactions[1]["shares"] == 500.0
        # Both should have same insider info
        assert transactions[0]["insider_title"] == "Director, CEO"
        assert transactions[1]["insider_title"] == "Director, CEO"

    def test_parse_form4_xml_handles_invalid_xml(self):
        """Test that parse_form4_xml handles invalid XML gracefully."""
        xml_content = "not valid xml"

        transactions = parse_form4_xml(xml_content)

        assert transactions == []

    def test_parse_form4_xml_handles_empty_transactions(self):
        """Test that parse_form4_xml handles Form 4 with no transactions."""
        xml_content = """<?xml version="1.0"?>
        <ownershipDocument>
            <issuer>
                <issuerCik>0000320193</issuerCik>
                <issuerName>Apple Inc</issuerName>
                <issuerTradingSymbol>AAPL</issuerTradingSymbol>
            </issuer>
            <reportingOwner>
                <reportingOwnerId>
                    <rptOwnerCik>0001234567</rptOwnerCik>
                    <rptOwnerName>John Doe</rptOwnerName>
                </reportingOwnerId>
                <reportingOwnerRelationship>
                    <isDirector>1</isDirector>
                    <isOfficer>0</isOfficer>
                </reportingOwnerRelationship>
            </reportingOwner>
        </ownershipDocument>
        """

        transactions = parse_form4_xml(xml_content)

        assert transactions == []


class TestForm4BronzeAssets:
    """Tests for Form 4 bronze layer assets."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def specs_by_key(self, all_specs):
        """Index specs by asset key for efficient lookup."""
        return {spec.key: spec for spec in all_specs}

    def test_bronze_form_4_asset_exists(self, specs_by_key):
        """Test that bronze Form 4 asset is defined."""
        expected_key = dg.AssetKey(["bronze", "sec", "form_4"])
        assert expected_key in specs_by_key, "Missing bronze/sec/form_4 asset"

    def test_bronze_form_4_has_correct_key_prefix(self, specs_by_key):
        """Test that bronze Form 4 asset has correct key structure."""
        key = dg.AssetKey(["bronze", "sec", "form_4"])
        spec = specs_by_key[key]

        assert len(spec.key.path) == 3, "Bronze Form 4 asset should have 3 components"
        assert spec.key.path[0] == "bronze", 'First component should be "bronze"'
        assert spec.key.path[1] == "sec", 'Second component should be "sec"'
        assert spec.key.path[2] == "form_4", 'Third component should be "form_4"'

    def test_bronze_form_4_is_partitioned(self, specs_by_key):
        """Test that bronze Form 4 asset is partitioned by month."""
        key = dg.AssetKey(["bronze", "sec", "form_4"])
        spec = specs_by_key[key]

        assert spec.partitions_def is not None, "Bronze Form 4 should be partitioned"
        assert spec.partitions_def == sec_monthly_partitions, (
            "Bronze Form 4 should use sec_monthly_partitions"
        )

    def test_bronze_form_4_metadata_complete(self, specs_by_key):
        """Test that bronze Form 4 asset has complete metadata."""
        key = dg.AssetKey(["bronze", "sec", "form_4"])
        spec = specs_by_key[key]

        required_fields = ["layer", "source", "form_type", "visibility"]

        # Check required fields present
        for field in required_fields:
            assert field in spec.metadata, (
                f'Bronze Form 4 missing required metadata field "{field}"'
            )

        # Check specific values
        assert spec.metadata["layer"] == "bronze", 'Should have layer="bronze"'
        assert spec.metadata["source"] == "sec_edgar", 'Should have source="sec_edgar"'
        assert spec.metadata["form_type"] == "4", 'Should have form_type="4"'
        assert spec.metadata["visibility"] == "internal", (
            'Should have visibility="internal"'
        )

    def test_bronze_form_4_has_description(self, specs_by_key):
        """Test that bronze Form 4 asset has a description."""
        key = dg.AssetKey(["bronze", "sec", "form_4"])
        spec = specs_by_key[key]

        description = spec.description or spec.metadata.get("description", "")
        assert len(description) > 0, "Bronze Form 4 should have a description"


class TestForm4SilverAssets:
    """Tests for Form 4 silver layer assets."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def specs_by_key(self, all_specs):
        """Index specs by asset key for efficient lookup."""
        return {spec.key: spec for spec in all_specs}

    def test_silver_form_4_transactions_asset_exists(self, specs_by_key):
        """Test that silver Form 4 transactions asset is defined."""
        expected_key = dg.AssetKey(["silver", "sec", "form_4_transactions"])
        assert expected_key in specs_by_key, (
            "Missing silver/sec/form_4_transactions asset"
        )

    def test_silver_form_4_transactions_has_correct_key_prefix(self, specs_by_key):
        """Test that silver Form 4 transactions asset has correct key structure."""
        key = dg.AssetKey(["silver", "sec", "form_4_transactions"])
        spec = specs_by_key[key]

        assert len(spec.key.path) == 3, (
            "Silver Form 4 transactions should have 3 components"
        )
        assert spec.key.path[0] == "silver", 'First component should be "silver"'
        assert spec.key.path[1] == "sec", 'Second component should be "sec"'
        assert spec.key.path[2] == "form_4_transactions", (
            'Third component should be "form_4_transactions"'
        )

    def test_silver_form_4_transactions_is_partitioned(self, specs_by_key):
        """Test that silver Form 4 transactions asset is partitioned by month."""
        key = dg.AssetKey(["silver", "sec", "form_4_transactions"])
        spec = specs_by_key[key]

        assert spec.partitions_def is not None, (
            "Silver Form 4 transactions should be partitioned"
        )
        assert spec.partitions_def == sec_monthly_partitions, (
            "Silver Form 4 transactions should use sec_monthly_partitions"
        )

    def test_silver_form_4_transactions_metadata_complete(self, specs_by_key):
        """Test that silver Form 4 transactions asset has complete metadata."""
        key = dg.AssetKey(["silver", "sec", "form_4_transactions"])
        spec = specs_by_key[key]

        required_fields = ["layer", "data_quality", "visibility"]

        # Check required fields present
        for field in required_fields:
            assert field in spec.metadata, (
                f'Silver Form 4 transactions missing required metadata field "{field}"'
            )

        # Check specific values
        assert spec.metadata["layer"] == "silver", 'Should have layer="silver"'
        assert spec.metadata["data_quality"] == "validated", (
            'Should have data_quality="validated"'
        )
        assert spec.metadata["visibility"] == "internal", (
            'Should have visibility="internal"'
        )

    def test_silver_form_4_transactions_has_description(self, specs_by_key):
        """Test that silver Form 4 transactions asset has a description."""
        key = dg.AssetKey(["silver", "sec", "form_4_transactions"])
        spec = specs_by_key[key]

        description = spec.description or spec.metadata.get("description", "")
        assert len(description) > 0, (
            "Silver Form 4 transactions should have a description"
        )


class TestForm4GoldAssets:
    """Tests for Form 4 gold layer assets."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def specs_by_key(self, all_specs):
        """Index specs by asset key for efficient lookup."""
        return {spec.key: spec for spec in all_specs}

    def test_gold_insider_activity_asset_exists(self, specs_by_key):
        """Test that gold insider activity asset is defined."""
        expected_key = dg.AssetKey(["gold", "companies", "insider", "insider_activity"])
        assert expected_key in specs_by_key, (
            "Missing gold/companies/insider/insider_activity asset"
        )

    def test_gold_insider_activity_has_correct_key_prefix(self, specs_by_key):
        """Test that gold insider activity asset has correct key structure."""
        key = dg.AssetKey(["gold", "companies", "insider", "insider_activity"])
        spec = specs_by_key[key]

        assert len(spec.key.path) == 4, "Gold insider activity should have 4 components"
        assert spec.key.path[0] == "gold", 'First component should be "gold"'
        assert spec.key.path[1] == "companies", 'Second component should be "companies"'
        assert spec.key.path[2] == "insider", 'Third component should be "insider"'
        assert spec.key.path[3] == "insider_activity", (
            'Fourth component should be "insider_activity"'
        )

    def test_gold_insider_activity_is_unpartitioned(self, specs_by_key):
        """Test that gold insider activity asset is unpartitioned (aggregated)."""
        key = dg.AssetKey(["gold", "companies", "insider", "insider_activity"])
        spec = specs_by_key[key]

        assert spec.partitions_def is None, (
            "Gold insider activity should be unpartitioned (uses AllPartitionMapping)"
        )

    def test_gold_insider_activity_metadata_complete(self, specs_by_key):
        """Test that gold insider activity asset has complete metadata."""
        key = dg.AssetKey(["gold", "companies", "insider", "insider_activity"])
        spec = specs_by_key[key]

        required_fields = ["layer", "visibility"]

        # Check required fields present
        for field in required_fields:
            assert field in spec.metadata, (
                f'Gold insider activity missing required metadata field "{field}"'
            )

        # Check specific values
        assert spec.metadata["layer"] == "gold", 'Should have layer="gold"'
        assert spec.metadata["visibility"] == "llm_accessible", (
            'Should have visibility="llm_accessible"'
        )

    def test_gold_insider_activity_has_description(self, specs_by_key):
        """Test that gold insider activity asset has a description."""
        key = dg.AssetKey(["gold", "companies", "insider", "insider_activity"])
        spec = specs_by_key[key]

        description = spec.description or spec.metadata.get("description", "")
        assert len(description) > 0, "Gold insider activity should have a description"


class TestForm4AssetDependencies:
    """Tests for Form 4 asset dependency structure."""

    @pytest.fixture
    def all_specs(self):
        """Get all asset specs from definitions."""
        return list(defs.resolve_all_asset_specs())

    @pytest.fixture
    def specs_by_key(self, all_specs):
        """Index specs by asset key for efficient lookup."""
        return {spec.key: spec for spec in all_specs}

    def test_silver_depends_on_bronze(self, specs_by_key):
        """Test that silver Form 4 transactions depends on bronze Form 4."""
        silver_key = dg.AssetKey(["silver", "sec", "form_4_transactions"])
        silver_spec = specs_by_key[silver_key]

        # Get dependency keys
        dep_keys = {dep.asset_key for dep in silver_spec.deps}

        bronze_key = dg.AssetKey(["bronze", "sec", "form_4"])
        assert bronze_key in dep_keys, (
            "Silver Form 4 transactions should depend on bronze Form 4"
        )

    def test_gold_depends_on_silver_and_registry(self, specs_by_key):
        """Test that gold insider activity depends on silver transactions and registry."""
        gold_key = dg.AssetKey(["gold", "companies", "insider", "insider_activity"])
        gold_spec = specs_by_key[gold_key]

        # Get dependency keys
        dep_keys = {dep.asset_key for dep in gold_spec.deps}

        silver_key = dg.AssetKey(["silver", "sec", "form_4_transactions"])
        registry_key = dg.AssetKey(["silver", "sec", "company_registry"])

        assert silver_key in dep_keys, (
            "Gold insider activity should depend on silver transactions"
        )
        assert registry_key in dep_keys, (
            "Gold insider activity should depend on company registry"
        )

    def test_gold_uses_all_partition_mapping_for_silver(self, specs_by_key):
        """Test that gold insider activity uses AllPartitionMapping for silver dependency."""
        gold_key = dg.AssetKey(["gold", "companies", "insider", "insider_activity"])
        gold_spec = specs_by_key[gold_key]

        # Find the silver transactions dependency
        silver_key = dg.AssetKey(["silver", "sec", "form_4_transactions"])
        silver_dep = None
        for dep in gold_spec.deps:
            if dep.asset_key == silver_key:
                silver_dep = dep
                break

        assert silver_dep is not None, "Should have silver transactions dependency"
        assert isinstance(silver_dep.partition_mapping, dg.AllPartitionMapping), (
            "Should use AllPartitionMapping for silver transactions"
        )
