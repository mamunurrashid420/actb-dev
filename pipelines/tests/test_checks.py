"""Tests for asset check functions.

These tests verify that:
1. Asset checks are properly defined and discoverable
2. The checks reference valid asset keys
3. Schema validation logic works correctly (tested via schemas module)

Note: Direct invocation of asset checks requires Dagster execution context.
Schema validation is tested in test_schemas.py. This file focuses on
check definition and registration.
"""

import dagster as dg
import pandas as pd
import pandera.pandas as pa
import pytest

from pipelines.definitions import defs
from pipelines.schemas import (
    BlsTimeseriesSchema,
    FredTimeseriesSchema,
    NoaaMonthlySchema,
    SecForm4Schema,
    SecForm10KSchema,
    SecForm10QSchema,
    SecForm13FSchema,
    WorldBankTimeseriesSchema,
)


class TestCheckRegistration:
    """Tests that all asset checks are properly registered in definitions."""

    def test_definitions_has_asset_checks(self):
        """Test that definitions includes asset checks."""
        # Assert
        assert defs.asset_checks is not None
        assert len(defs.asset_checks) > 0

    def test_all_expected_checks_are_registered(self):
        """Test that all expected check functions are registered."""
        # Arrange - current set of checks (matches actual registered checks)
        want_check_specs = {
            # FRED
            dg.AssetCheckKey(
                asset_key=dg.AssetKey(["bronze", "fred", "series"]),
                name="check_fred_timeseries_schema",
            ),
            # BLS
            dg.AssetCheckKey(
                asset_key=dg.AssetKey(["bronze", "bls", "all_series"]),
                name="check_bls_timeseries_schema",
            ),
            # World Bank
            dg.AssetCheckKey(
                asset_key=dg.AssetKey(["bronze", "world_bank", "timeseries"]),
                name="check_world_bank_timeseries",
            ),
            # NOAA
            dg.AssetCheckKey(
                asset_key=dg.AssetKey(["bronze", "noaa", "monthly"]),
                name="check_noaa_monthly_schema",
            ),
            dg.AssetCheckKey(
                asset_key=dg.AssetKey(["bronze", "noaa", "daily"]),
                name="check_noaa_daily_schema",
            ),
            dg.AssetCheckKey(
                asset_key=dg.AssetKey(["bronze", "noaa", "annual"]),
                name="check_noaa_annual_schema",
            ),
            # NASA POWER
            dg.AssetCheckKey(
                asset_key=dg.AssetKey(["bronze", "nasa_power", "daily"]),
                name="check_nasa_power_daily_completeness",
            ),
            dg.AssetCheckKey(
                asset_key=dg.AssetKey(["bronze", "nasa_power", "monthly"]),
                name="check_nasa_power_monthly_completeness",
            ),
            # SEC Bronze (time-based partitions)
            dg.AssetCheckKey(
                asset_key=dg.AssetKey(["bronze", "sec", "form_10k_text"]),
                name="check_sec_form_10k_text",
            ),
            dg.AssetCheckKey(
                asset_key=dg.AssetKey(["bronze", "sec", "form_10q_text"]),
                name="check_sec_form_10q_text",
            ),
            dg.AssetCheckKey(
                asset_key=dg.AssetKey(["bronze", "sec", "form_4"]),
                name="check_sec_form_4",
            ),
            dg.AssetCheckKey(
                asset_key=dg.AssetKey(["bronze", "sec", "form_13f"]),
                name="check_sec_form_13f",
            ),
            # SEC Gold
            dg.AssetCheckKey(
                asset_key=dg.AssetKey([
                    "gold",
                    "companies",
                    "financials",
                    "annual_reports",
                ]),
                name="check_annual_reports",
            ),
            dg.AssetCheckKey(
                asset_key=dg.AssetKey([
                    "gold",
                    "companies",
                    "financials",
                    "quarterly_reports",
                ]),
                name="check_quarterly_reports",
            ),
            dg.AssetCheckKey(
                asset_key=dg.AssetKey([
                    "gold",
                    "companies",
                    "insider",
                    "insider_activity",
                ]),
                name="check_insider_activity",
            ),
            dg.AssetCheckKey(
                asset_key=dg.AssetKey([
                    "gold",
                    "institutions",
                    "portfolio",
                    "holdings",
                ]),
                name="check_portfolio_holdings",
            ),
        }

        # Act - collect all check keys from definitions
        got_check_specs = set()
        for check_def in defs.asset_checks:
            for key in check_def.check_keys:
                got_check_specs.add(key)

        # Assert - all expected checks should be present
        missing_checks = want_check_specs - got_check_specs
        assert not missing_checks, f"Missing checks in definitions: {missing_checks}"


class TestCheckAssetKeyReferences:
    """Tests that asset checks reference valid asset keys."""

    def test_all_checks_reference_defined_assets(self):
        """Test that all asset checks reference assets that exist in definitions."""
        # Arrange - get all defined asset keys
        defined_asset_keys = set()
        for spec in defs.resolve_all_asset_specs():
            defined_asset_keys.add(spec.key)

        # Act - collect asset keys referenced by checks
        check_violations = []
        for check_def in defs.asset_checks:
            for key in check_def.check_keys:
                if key.asset_key not in defined_asset_keys:
                    check_violations.append(
                        f"Check {key.name} references undefined asset {key.asset_key}"
                    )

        # Assert
        assert not check_violations, "\n".join(check_violations)


class TestFredSchemaValidation:
    """Tests for FRED schema validation logic used by checks."""

    def test_valid_fred_data_passes_schema(self):
        """Test that valid FRED data passes schema validation."""
        # Arrange
        df = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01", "2023-02-01", "2023-03-01"]),
            "value": [100.0, 101.5, 102.0],
            "series_id": ["GDP", "GDP", "GDP"],
        })

        # Act
        result = FredTimeseriesSchema.validate(df, lazy=True)

        # Assert
        assert result is not None
        assert len(result) == 3

    def test_missing_column_fails_schema(self):
        """Test that missing series_id column fails validation."""
        # Arrange
        df = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01", "2023-02-01"]),
            "value": [100.0, 101.5],
        })

        # Act & Assert
        with pytest.raises(pa.errors.SchemaErrors):
            FredTimeseriesSchema.validate(df, lazy=True)


class TestBlsSchemaValidation:
    """Tests for BLS schema validation logic used by checks."""

    def test_valid_bls_data_with_new_series_ids(self):
        """Test that valid BLS data with new 21-char JOLTS IDs passes."""
        # Arrange - use the new 21-character JOLTS series ID format
        df = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01", "2023-02-01"]),
            "value": [7500.0, 7600.0],
            "series_id": [
                "JTS000000000000000JOL",
                "JTS000000000000000JOL",
            ],
            "year": [2023, 2023],
            "period": ["M01", "M02"],
        })

        # Act
        result = BlsTimeseriesSchema.validate(df, lazy=True)

        # Assert
        assert result is not None
        assert len(result) == 2


class TestWorldBankSchemaValidation:
    """Tests for World Bank schema validation logic used by checks."""

    def test_valid_world_bank_data_passes_schema(self):
        """Test that valid World Bank data passes schema validation."""
        # Arrange
        df = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01", "2023-01-01"]),
            "value": [25000.0, 18000.0],
            "country_code": ["USA", "CHN"],
            "indicator_code": ["NY.GDP.MKTP.CD", "NY.GDP.MKTP.CD"],
        })

        # Act
        result = WorldBankTimeseriesSchema.validate(df, lazy=True)

        # Assert
        assert result is not None
        assert len(result) == 2


class TestNoaaSchemaValidation:
    """Tests for NOAA schema validation logic used by checks."""

    def test_valid_noaa_data_passes_schema(self):
        """Test that valid NOAA data passes schema validation."""
        # Arrange
        df = pd.DataFrame({
            "station_id": ["USW00094728", "USW00094728"],
            "date": pd.to_datetime(["2023-01-01", "2023-02-01"]),
            "TAVG": [15.5, 16.2],
        })

        # Act
        result = NoaaMonthlySchema.validate(df, lazy=True)

        # Assert
        assert result is not None
        assert len(result) == 2


class TestSecSchemaValidation:
    """Tests for SEC schema validation logic used by checks."""

    def test_valid_form_10k_data_passes_schema(self):
        """Test that valid SEC Form 10-K data passes schema validation."""
        # Arrange
        df = pd.DataFrame({
            "ticker": ["AAPL"],
            "cik": ["0000320193"],
            "company_name": ["Apple Inc."],
            "fiscal_year": [2023],
            "filing_date": ["2023-11-03"],
            "period_of_report": ["2023-09-30"],
            "accession_number": ["0000320193-23-000106"],
            "filing_url": ["https://sec.gov/1"],
        })

        # Act
        result = SecForm10KSchema.validate(df, lazy=True)

        # Assert
        assert result is not None

    def test_valid_form_10q_data_passes_schema(self):
        """Test that valid SEC Form 10-Q data passes schema validation."""
        # Arrange
        df = pd.DataFrame({
            "ticker": ["AAPL"],
            "cik": ["0000320193"],
            "company_name": ["Apple Inc."],
            "fiscal_year": [2023],
            "quarter": [3],
            "filing_date": ["2023-08-04"],
            "period_of_report": ["2023-07-01"],
            "accession_number": ["0000320193-23-000077"],
            "filing_url": ["https://sec.gov/1"],
        })

        # Act
        result = SecForm10QSchema.validate(df, lazy=True)

        # Assert
        assert result is not None

    def test_valid_form_4_data_passes_schema(self):
        """Test that valid SEC Form 4 data passes schema validation."""
        # Arrange
        df = pd.DataFrame({
            "ticker": ["AAPL"],
            "cik": ["0000320193"],
            "company_name": ["Apple Inc."],
            "year": [2023],
            "month": [11],
            "filing_date": ["2023-11-15"],
            "accession_number": ["test1"],
            "filing_url": ["https://sec.gov/1"],
        })

        # Act
        result = SecForm4Schema.validate(df, lazy=True)

        # Assert
        assert result is not None

    def test_valid_form_13f_data_passes_schema(self):
        """Test that valid SEC Form 13-F data passes schema validation."""
        # Arrange
        df = pd.DataFrame({
            "cik": ["0001067983"],
            "institution_name": ["Berkshire Hathaway"],
            "fiscal_year": [2023],
            "quarter": [3],
            "filing_date": ["2023-11-14"],
            "period_of_report": ["2023-09-30"],
            "accession_number": ["test1"],
            "filing_url": ["https://sec.gov/1"],
        })

        # Act
        result = SecForm13FSchema.validate(df, lazy=True)

        # Assert
        assert result is not None
