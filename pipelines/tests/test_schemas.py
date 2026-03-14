"""Tests for Pandera schema validation."""

from pathlib import Path

import pandas as pd
import pandera.pandas as pa
import pytest

from pipelines.schemas import (
    BlsTimeseriesSchema,
    FredTimeseriesSchema,
    NasaPowerSchema,
    NoaaMonthlySchema,
    SecForm4Schema,
    SecForm10KSchema,
    SecForm10QSchema,
    SecForm13FSchema,
    WorldBankTimeseriesSchema,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestFredTimeseriesSchema:
    """Tests for FRED timeseries schema validation."""

    def test_validates_real_fred_data(self):
        """Test that schema validates real FRED data from fixture."""
        # Arrange
        fixture_path = FIXTURES_DIR / "fred_cpiaucsl.parquet"
        if not fixture_path.exists():
            pytest.skip(f"Fixture not found: {fixture_path}")

        df = pd.read_parquet(fixture_path)

        # Act - validate should not raise
        result = FredTimeseriesSchema.validate(df, lazy=True)

        # Assert
        assert result is not None
        assert len(result) > 0

    def test_rejects_missing_required_column(self):
        """Test that missing series_id column raises SchemaErrors."""
        # Arrange
        df = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01", "2023-02-01"]),
            "value": [100.0, 101.0],
            # Missing series_id
        })

        # Act & Assert
        with pytest.raises(pa.errors.SchemaErrors) as exc_info:
            FredTimeseriesSchema.validate(df, lazy=True)

        # Verify error mentions missing column
        error_message = str(exc_info.value)
        assert "series_id" in error_message.lower()

    def test_allows_extra_columns(self):
        """Test that extra columns don't cause validation failure."""
        # Arrange
        df = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01", "2023-02-01"]),
            "value": [100.0, 101.0],
            "series_id": ["GDP", "GDP"],
            "extra_column": ["foo", "bar"],
            "another_extra": [1, 2],
        })

        # Act - should not raise
        result = FredTimeseriesSchema.validate(df, lazy=True)

        # Assert
        assert result is not None
        assert "extra_column" in result.columns
        assert "another_extra" in result.columns

    def test_lazy_validation_collects_all_errors(self):
        """Test that lazy validation collects multiple errors."""
        # Arrange - create dataframe with multiple validation errors
        df = pd.DataFrame({
            "date": ["not-a-date", "2023-02-01"],  # Invalid date type
            "value": [100.0, 101.0],
            # Missing series_id column
        })

        # Act & Assert
        with pytest.raises(pa.errors.SchemaErrors) as exc_info:
            FredTimeseriesSchema.validate(df, lazy=True)

        # Verify multiple errors collected
        errors = exc_info.value
        assert len(errors.failure_cases) > 0

    def test_validates_correct_types(self):
        """Test that schema validates correct data types."""
        # Arrange
        df = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01", "2023-02-01", "2023-03-01"]),
            "value": [100.0, 101.5, None],  # value can be nullable
            "series_id": ["GDP", "GDP", "GDP"],
        })

        # Act
        result = FredTimeseriesSchema.validate(df, lazy=True)

        # Assert
        assert result is not None
        got_date_dtype = result["date"].dtype
        want_date_dtype = "datetime64[ns]"
        assert got_date_dtype == want_date_dtype

        got_series_dtype = result["series_id"].dtype
        want_series_dtype = "object"
        assert got_series_dtype == want_series_dtype

    def test_rejects_null_in_required_column(self):
        """Test that null values in required columns raise error."""
        # Arrange
        df = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01", None]),  # Null date
            "value": [100.0, 101.0],
            "series_id": ["GDP", "GDP"],
        })

        # Act & Assert
        with pytest.raises(pa.errors.SchemaErrors):
            FredTimeseriesSchema.validate(df, lazy=True)


class TestNoaaMonthlySchema:
    """Tests for NOAA monthly weather schema validation."""

    def test_validates_real_noaa_data(self):
        """Test that schema validates real NOAA data from fixture."""
        # Arrange
        fixture_path = FIXTURES_DIR / "noaa_nyc_monthly.parquet"
        if not fixture_path.exists():
            pytest.skip(f"Fixture not found: {fixture_path}")

        df = pd.read_parquet(fixture_path)

        # Act
        result = NoaaMonthlySchema.validate(df, lazy=True)

        # Assert
        assert result is not None
        assert len(result) > 0

    def test_validates_required_columns(self):
        """Test that schema requires station_id and date."""
        # Arrange
        df = pd.DataFrame({
            "station_id": ["STATION1", "STATION1"],
            "date": pd.to_datetime(["2023-01-01", "2023-02-01"]),
            "TAVG": [15.5, 16.2],
        })

        # Act
        result = NoaaMonthlySchema.validate(df, lazy=True)

        # Assert
        assert result is not None
        assert "station_id" in result.columns
        assert "date" in result.columns

    def test_allows_optional_weather_columns(self):
        """Test that weather measurement columns are optional."""
        # Arrange - only required columns, no weather measurements
        df = pd.DataFrame({
            "station_id": ["STATION1", "STATION2"],
            "date": pd.to_datetime(["2023-01-01", "2023-02-01"]),
        })

        # Act - should not raise
        result = NoaaMonthlySchema.validate(df, lazy=True)

        # Assert
        assert result is not None
        assert len(result) == 2

    def test_allows_null_weather_measurements(self):
        """Test that null values allowed in weather measurements."""
        # Arrange
        df = pd.DataFrame({
            "station_id": ["STATION1", "STATION1", "STATION1"],
            "date": pd.to_datetime(["2023-01-01", "2023-02-01", "2023-03-01"]),
            "TAVG": [15.5, None, 17.2],
            "TMAX": [None, 25.0, 28.5],
            "PRCP": [0.0, 5.2, None],
        })

        # Act
        result = NoaaMonthlySchema.validate(df, lazy=True)

        # Assert
        assert result is not None
        assert pd.isna(result.loc[1, "TAVG"])
        assert pd.isna(result.loc[0, "TMAX"])
        assert pd.isna(result.loc[2, "PRCP"])

    def test_rejects_missing_station_id(self):
        """Test that missing station_id raises error."""
        # Arrange
        df = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01", "2023-02-01"]),
            "TAVG": [15.5, 16.2],
        })

        # Act & Assert
        with pytest.raises(pa.errors.SchemaErrors) as exc_info:
            NoaaMonthlySchema.validate(df, lazy=True)

        error_message = str(exc_info.value)
        assert "station_id" in error_message.lower()

    def test_allows_extra_weather_columns(self):
        """Test that extra weather measurement columns are allowed."""
        # Arrange
        df = pd.DataFrame({
            "station_id": ["STATION1", "STATION1"],
            "date": pd.to_datetime(["2023-01-01", "2023-02-01"]),
            "TAVG": [15.5, 16.2],
            "CUSTOM_METRIC": [1.0, 2.0],
            "EXTRA_WEATHER": ["sunny", "cloudy"],
        })

        # Act
        result = NoaaMonthlySchema.validate(df, lazy=True)

        # Assert
        assert result is not None
        assert "CUSTOM_METRIC" in result.columns
        assert "EXTRA_WEATHER" in result.columns


class TestBlsTimeseriesSchema:
    """Tests for BLS timeseries schema validation."""

    def test_validates_correct_bls_data(self):
        """Test that schema validates correct BLS data."""
        # Arrange
        df = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01", "2023-02-01"]),
            "value": [3.5, 3.6],
            "series_id": ["UNRATE", "UNRATE"],
            "year": [2023, 2023],
            "period": ["M01", "M02"],
        })

        # Act
        result = BlsTimeseriesSchema.validate(df, lazy=True)

        # Assert
        assert result is not None
        assert len(result) == 2

    def test_validates_year_range(self):
        """Test that year field validates range constraints."""
        # Arrange - year outside valid range
        df = pd.DataFrame({
            "date": pd.to_datetime(["1800-01-01"]),
            "value": [100.0],
            "series_id": ["TEST"],
            "year": [1800],  # Below minimum of 1900
            "period": ["M01"],
        })

        # Act & Assert
        with pytest.raises(pa.errors.SchemaErrors):
            BlsTimeseriesSchema.validate(df, lazy=True)

    def test_requires_all_bls_specific_columns(self):
        """Test that all BLS-specific columns are required."""
        # Arrange - missing period column
        df = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01"]),
            "value": [100.0],
            "series_id": ["UNRATE"],
            "year": [2023],
            # Missing period
        })

        # Act & Assert
        with pytest.raises(pa.errors.SchemaErrors) as exc_info:
            BlsTimeseriesSchema.validate(df, lazy=True)

        error_message = str(exc_info.value)
        assert "period" in error_message.lower()


class TestWorldBankTimeseriesSchema:
    """Tests for World Bank timeseries schema validation."""

    def test_validates_correct_world_bank_data(self):
        """Test that schema validates correct World Bank data."""
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

    def test_validates_country_code_length(self):
        """Test that country_code validates string length (2-3 chars)."""
        # Arrange - valid 2 and 3 char codes
        df_valid = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01", "2023-01-01"]),
            "value": [1000.0, 2000.0],
            "country_code": ["US", "USA"],  # Both valid lengths
            "indicator_code": ["TEST", "TEST"],
        })

        # Act
        result = WorldBankTimeseriesSchema.validate(df_valid, lazy=True)

        # Assert
        assert result is not None

    def test_rejects_invalid_country_code_length(self):
        """Test that country codes outside 2-3 char range are rejected."""
        # Arrange - country code too long
        df = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01"]),
            "value": [1000.0],
            "country_code": ["TOOLONG"],  # 7 chars, invalid
            "indicator_code": ["TEST"],
        })

        # Act & Assert
        with pytest.raises(pa.errors.SchemaErrors):
            WorldBankTimeseriesSchema.validate(df, lazy=True)

    def test_requires_indicator_code(self):
        """Test that indicator_code is required."""
        # Arrange
        df = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01"]),
            "value": [1000.0],
            "country_code": ["USA"],
            # Missing indicator_code
        })

        # Act & Assert
        with pytest.raises(pa.errors.SchemaErrors) as exc_info:
            WorldBankTimeseriesSchema.validate(df, lazy=True)

        error_message = str(exc_info.value)
        assert "indicator_code" in error_message.lower()


class TestSchemaConfiguration:
    """Tests for schema configuration settings."""

    def test_fred_schema_allows_extra_columns(self):
        """Test that strict=False allows extra columns."""
        # Arrange
        df = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01"]),
            "value": [100.0],
            "series_id": ["GDP"],
            "unexpected_column": ["surprise"],
        })

        # Act - should not raise
        result = FredTimeseriesSchema.validate(df, lazy=True)

        # Assert
        assert "unexpected_column" in result.columns

    def test_schema_does_not_coerce_types(self):
        """Test that coerce=False means types must already be correct."""
        # Arrange - string date instead of datetime
        df = pd.DataFrame({
            "date": ["2023-01-01"],  # String, not datetime
            "value": [100.0],
            "series_id": ["GDP"],
        })

        # Act & Assert - should fail because coerce=False
        with pytest.raises(pa.errors.SchemaErrors):
            FredTimeseriesSchema.validate(df, lazy=True)


class TestNasaPowerSchema:
    """Tests for NASA POWER weather schema validation."""

    def test_validates_correct_nasa_power_data(self):
        """Test that schema validates correct NASA POWER data."""
        # Arrange
        df = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01", "2023-02-01"]),
            "location_id": ["brazil_minas_gerais", "brazil_minas_gerais"],
            "latitude": [-18.9433, -18.9433],
            "longitude": [-46.9978, -46.9978],
            "T2M": [22.5, 23.1],
            "PRECTOTCORR": [150.2, 180.5],
        })

        # Act
        result = NasaPowerSchema.validate(df, lazy=True)

        # Assert
        assert result is not None
        assert len(result) == 2

    def test_requires_location_id(self):
        """Test that location_id is required."""
        # Arrange - missing location_id
        df = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01"]),
            "latitude": [-18.9433],
            "longitude": [-46.9978],
        })

        # Act & Assert
        with pytest.raises(pa.errors.SchemaErrors) as exc_info:
            NasaPowerSchema.validate(df, lazy=True)

        error_message = str(exc_info.value)
        assert "location_id" in error_message.lower()

    def test_requires_coordinates(self):
        """Test that latitude and longitude are required."""
        # Arrange - missing coordinates
        df = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01"]),
            "location_id": ["brazil_minas_gerais"],
        })

        # Act & Assert
        with pytest.raises(pa.errors.SchemaErrors):
            NasaPowerSchema.validate(df, lazy=True)

    def test_allows_optional_weather_columns(self):
        """Test that weather measurement columns are optional."""
        # Arrange - only required columns
        df = pd.DataFrame({
            "date": pd.to_datetime(["2023-01-01"]),
            "location_id": ["brazil_minas_gerais"],
            "latitude": [-18.9433],
            "longitude": [-46.9978],
        })

        # Act - should not raise
        result = NasaPowerSchema.validate(df, lazy=True)

        # Assert
        assert result is not None


class TestSecForm10KSchema:
    """Tests for SEC Form 10-K schema validation."""

    def test_validates_correct_10k_data(self):
        """Test that schema validates correct 10-K filing data."""
        # Arrange
        df = pd.DataFrame({
            "ticker": ["AAPL", "AAPL"],
            "cik": ["0000320193", "0000320193"],
            "company_name": ["Apple Inc.", "Apple Inc."],
            "fiscal_year": [2023, 2022],
            "filing_date": ["2023-11-03", "2022-10-28"],
            "period_of_report": ["2023-09-30", "2022-09-24"],
            "accession_number": ["0000320193-23-000106", "0000320193-22-000108"],
            "filing_url": ["https://sec.gov/1", "https://sec.gov/2"],
        })

        # Act
        result = SecForm10KSchema.validate(df, lazy=True)

        # Assert
        assert result is not None
        assert len(result) == 2

    def test_validates_fiscal_year_range(self):
        """Test that fiscal_year validates range constraints."""
        # Arrange - year outside valid range
        df = pd.DataFrame({
            "ticker": ["AAPL"],
            "cik": ["0000320193"],
            "company_name": ["Apple Inc."],
            "fiscal_year": [1980],  # Below minimum of 1990
            "filing_date": ["1980-01-01"],
            "period_of_report": ["1979-12-31"],
            "accession_number": ["test"],
            "filing_url": ["https://sec.gov/test"],
        })

        # Act & Assert
        with pytest.raises(pa.errors.SchemaErrors):
            SecForm10KSchema.validate(df, lazy=True)

    def test_requires_accession_number(self):
        """Test that accession_number is required."""
        # Arrange - missing accession_number
        df = pd.DataFrame({
            "ticker": ["AAPL"],
            "cik": ["0000320193"],
            "company_name": ["Apple Inc."],
            "fiscal_year": [2023],
            "filing_date": ["2023-11-03"],
            "period_of_report": ["2023-09-30"],
            "filing_url": ["https://sec.gov/1"],
        })

        # Act & Assert
        with pytest.raises(pa.errors.SchemaErrors) as exc_info:
            SecForm10KSchema.validate(df, lazy=True)

        error_message = str(exc_info.value)
        assert "accession_number" in error_message.lower()


class TestSecForm10QSchema:
    """Tests for SEC Form 10-Q schema validation."""

    def test_validates_correct_10q_data(self):
        """Test that schema validates correct 10-Q filing data."""
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

    def test_validates_quarter_range(self):
        """Test that quarter validates range constraints (1-4)."""
        # Arrange - quarter outside valid range
        df = pd.DataFrame({
            "ticker": ["AAPL"],
            "cik": ["0000320193"],
            "company_name": ["Apple Inc."],
            "fiscal_year": [2023],
            "quarter": [5],  # Invalid quarter
            "filing_date": ["2023-08-04"],
            "period_of_report": ["2023-07-01"],
            "accession_number": ["test"],
            "filing_url": ["https://sec.gov/1"],
        })

        # Act & Assert
        with pytest.raises(pa.errors.SchemaErrors):
            SecForm10QSchema.validate(df, lazy=True)


class TestSecForm4Schema:
    """Tests for SEC Form 4 schema validation."""

    def test_validates_correct_form4_data(self):
        """Test that schema validates correct Form 4 filing data."""
        # Arrange
        df = pd.DataFrame({
            "ticker": ["AAPL", "AAPL"],
            "cik": ["0000320193", "0000320193"],
            "company_name": ["Apple Inc.", "Apple Inc."],
            "year": [2023, 2023],
            "month": [11, 10],
            "filing_date": ["2023-11-15", "2023-10-20"],
            "accession_number": ["test1", "test2"],
            "filing_url": ["https://sec.gov/1", "https://sec.gov/2"],
        })

        # Act
        result = SecForm4Schema.validate(df, lazy=True)

        # Assert
        assert result is not None
        assert len(result) == 2

    def test_validates_month_range(self):
        """Test that month validates range constraints (1-12)."""
        # Arrange - month outside valid range
        df = pd.DataFrame({
            "ticker": ["AAPL"],
            "cik": ["0000320193"],
            "company_name": ["Apple Inc."],
            "year": [2023],
            "month": [13],  # Invalid month
            "filing_date": ["2023-11-15"],
            "accession_number": ["test"],
            "filing_url": ["https://sec.gov/1"],
        })

        # Act & Assert
        with pytest.raises(pa.errors.SchemaErrors):
            SecForm4Schema.validate(df, lazy=True)


class TestSecForm13FSchema:
    """Tests for SEC Form 13-F schema validation."""

    def test_validates_correct_13f_data(self):
        """Test that schema validates correct 13-F filing data."""
        # Arrange
        df = pd.DataFrame({
            "cik": ["0001067983", "0001067983"],
            "institution_name": ["Berkshire Hathaway", "Berkshire Hathaway"],
            "fiscal_year": [2023, 2023],
            "quarter": [3, 2],
            "filing_date": ["2023-11-14", "2023-08-14"],
            "period_of_report": ["2023-09-30", "2023-06-30"],
            "accession_number": ["test1", "test2"],
            "filing_url": ["https://sec.gov/1", "https://sec.gov/2"],
        })

        # Act
        result = SecForm13FSchema.validate(df, lazy=True)

        # Assert
        assert result is not None
        assert len(result) == 2

    def test_requires_institution_name(self):
        """Test that institution_name is required."""
        # Arrange - missing institution_name
        df = pd.DataFrame({
            "cik": ["0001067983"],
            "fiscal_year": [2023],
            "quarter": [3],
            "filing_date": ["2023-11-14"],
            "period_of_report": ["2023-09-30"],
            "accession_number": ["test"],
            "filing_url": ["https://sec.gov/1"],
        })

        # Act & Assert
        with pytest.raises(pa.errors.SchemaErrors) as exc_info:
            SecForm13FSchema.validate(df, lazy=True)

        error_message = str(exc_info.value)
        assert "institution_name" in error_message.lower()
