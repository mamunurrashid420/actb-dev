"""Tests for Dagster resources including SEC EDGAR and NOAA."""

import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import httpx
import pandas as pd
import pytest

from pipelines.resources import (
    NasaPowerApiResource,
    NoaaApiResource,
    RetryableHTTPError,
    SecEdgarResource,
)


class TestSecEdgarResource:
    """Test suite for SEC EDGAR resource."""

    def test_initialization(self):
        """Test that SecEdgarResource initializes with identity."""
        resource = SecEdgarResource(identity="Test User test@example.com")
        assert resource.identity == "Test User test@example.com"
        assert resource.timeout == 120.0
        assert resource.rate_limit_delay == 0.1

    def test_custom_configuration(self):
        """Test that custom configuration values are respected."""
        resource = SecEdgarResource(
            identity="Test User test@example.com",
            timeout=60.0,
            rate_limit_delay=0.2,
        )
        assert resource.timeout == 60.0
        assert resource.rate_limit_delay == 0.2

    def test_setup_for_execution(self):
        """Test that setup_for_execution can be called."""
        resource = SecEdgarResource(identity="Test User test@example.com")
        mock_context = Mock()
        # Should not raise - base class method
        resource.setup_for_execution(mock_context)

    @patch("pipelines.resources.httpx.get")
    @patch("pipelines.resources.time.sleep")
    def test_fetch_company_tickers_success(self, mock_sleep, mock_get):
        """Test fetching company tickers from SEC API."""
        # Arrange - mock SEC API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."},
            "1": {
                "cik_str": "789019",
                "ticker": "MSFT",
                "title": "Microsoft Corporation",
            },
            "2": {
                "cik_str": "1067983",
                "ticker": "BRK-A",
                "title": "Berkshire Hathaway",
            },
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        resource = SecEdgarResource(identity="Test User test@example.com")

        # Act
        result = resource.fetch_company_tickers()

        # Assert
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "company_tickers.json" in call_args[0][0]

        # Verify DataFrame structure
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert list(result.columns) == ["cik", "ticker", "company_name"]

        # Verify CIK zero-padding
        want_ciks = ["0000320193", "0000789019", "0001067983"]
        got_ciks = result["cik"].tolist()
        assert got_ciks == want_ciks

        # Verify ticker and company name
        want_ticker = "AAPL"
        got_ticker = result.loc[result["cik"] == "0000320193", "ticker"].iloc[0]
        assert got_ticker == want_ticker

    @patch("pipelines.resources.httpx.get")
    @patch("pipelines.resources.time.sleep")
    def test_fetch_company_tickers_http_error(self, mock_sleep, mock_get):
        """Test handling of HTTP errors in fetch_company_tickers."""
        # Arrange - mock 404 error (should not retry)
        mock_response = Mock()
        mock_response.status_code = 404
        error = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )
        mock_get.side_effect = error

        resource = SecEdgarResource(identity="Test User test@example.com")

        # Act & Assert - non-retryable error should propagate
        with pytest.raises(httpx.HTTPStatusError):
            resource.fetch_company_tickers()

    @patch("pipelines.resources.httpx.get")
    @patch("pipelines.resources.time.sleep")
    def test_fetch_company_tickers_retryable_error(self, mock_sleep, mock_get):
        """Test that 429/5xx errors are wrapped as RetryableHTTPError."""
        # Arrange - mock 429 rate limit error
        mock_response = Mock()
        mock_response.status_code = 429
        error = httpx.HTTPStatusError(
            "Rate Limited", request=Mock(), response=mock_response
        )
        mock_get.side_effect = error

        resource = SecEdgarResource(identity="Test User test@example.com")

        # Act & Assert - retryable error should be wrapped
        with pytest.raises(RetryableHTTPError):
            resource.fetch_company_tickers()

    @patch("pipelines.resources.httpx.get")
    @patch("pipelines.resources.time.sleep")
    def test_download_company_facts_zip_success(self, mock_sleep, mock_get):
        """Test downloading companyfacts.zip."""
        # Arrange - mock successful download
        mock_response = Mock()
        mock_response.content = b"fake_zip_content"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Use temporary directory for cache
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            resource = SecEdgarResource(identity="Test User test@example.com")

            # Act
            result = resource.download_company_facts_zip(cache_dir=cache_dir)

            # Assert
            want_url = (
                "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"
            )
            got_url = mock_get.call_args[0][0]
            assert got_url == want_url

            # Verify User-Agent header is set
            got_headers = mock_get.call_args[1]["headers"]
            assert got_headers["User-Agent"] == "Test User test@example.com"

            # Verify zip was saved
            assert (cache_dir / "companyfacts.zip").exists()

            # Verify result is path to zip file (not extracted)
            want_result = cache_dir / "companyfacts.zip"
            assert result == want_result

    @patch("pipelines.resources.httpx.get")
    @patch("pipelines.resources.time.sleep")
    def test_download_company_facts_zip_uses_cache(self, mock_sleep, mock_get):
        """Test that cached files are reused if fresh (< 24 hours)."""
        # Arrange - create fake cached files
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            zip_path = cache_dir / "companyfacts.zip"

            # Create cached file
            zip_path.write_bytes(b"cached_content")

            # Touch file to be recent (fresh)
            zip_path.touch()

            resource = SecEdgarResource(identity="Test User test@example.com")

            # Act
            result = resource.download_company_facts_zip(cache_dir=cache_dir)

            # Assert - should NOT make HTTP request
            mock_get.assert_not_called()
            assert result == zip_path

    @patch("pipelines.resources.httpx.get")
    @patch("pipelines.resources.time.sleep")
    def test_download_company_facts_zip_refreshes_stale_cache(
        self, mock_sleep, mock_get
    ):
        """Test that stale cached files (> 24 hours) are refreshed."""
        # Arrange - create old cached files
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            zip_path = cache_dir / "companyfacts.zip"

            # Create cached file
            zip_path.write_bytes(b"old_content")

            # Make file stale (> 24 hours old)
            old_time = time.time() - 90000  # 25 hours ago
            import os

            os.utime(zip_path, (old_time, old_time))

            # Mock fresh download
            mock_response = Mock()
            mock_response.content = b"fresh_content"
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            resource = SecEdgarResource(identity="Test User test@example.com")

            # Act
            resource.download_company_facts_zip(cache_dir=cache_dir)

            # Assert - should make HTTP request for fresh data
            mock_get.assert_called_once()
            assert zip_path.read_bytes() == b"fresh_content"

    @patch("pipelines.resources.httpx.get")
    @patch("pipelines.resources.time.sleep")
    def test_download_submissions_zip_success(self, mock_sleep, mock_get):
        """Test downloading submissions.zip."""
        # Arrange
        mock_response = Mock()
        mock_response.content = b"fake_zip_content"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Use temporary directory for cache
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            resource = SecEdgarResource(identity="Test User test@example.com")

            # Act
            result = resource.download_submissions_zip(cache_dir=cache_dir)

            # Assert
            want_url = "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip"
            got_url = mock_get.call_args[0][0]
            assert got_url == want_url

            # Verify User-Agent header is set
            got_headers = mock_get.call_args[1]["headers"]
            assert got_headers["User-Agent"] == "Test User test@example.com"

            # Verify zip was saved
            assert (cache_dir / "submissions.zip").exists()

            # Verify result is path to zip file (not extracted)
            want_result = cache_dir / "submissions.zip"
            assert result == want_result

    @patch("pipelines.resources.httpx.get")
    @patch("pipelines.resources.time.sleep")
    def test_download_company_facts_zip_retryable_error(self, mock_sleep, mock_get):
        """Test that 429/5xx errors are wrapped as RetryableHTTPError."""
        # Arrange - mock 429 rate limit error
        mock_response = Mock()
        mock_response.status_code = 429
        error = httpx.HTTPStatusError(
            "Rate Limited", request=Mock(), response=mock_response
        )
        mock_get.side_effect = error

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            resource = SecEdgarResource(identity="Test User test@example.com")

            # Act & Assert - retryable error should be wrapped
            with pytest.raises(RetryableHTTPError):
                resource.download_company_facts_zip(cache_dir=cache_dir)

    @patch("pipelines.resources.httpx.get")
    @patch("pipelines.resources.time.sleep")
    def test_download_submissions_zip_retryable_error(self, mock_sleep, mock_get):
        """Test that 429/5xx errors are wrapped as RetryableHTTPError."""
        # Arrange - mock 503 service unavailable
        mock_response = Mock()
        mock_response.status_code = 503
        error = httpx.HTTPStatusError(
            "Service Unavailable", request=Mock(), response=mock_response
        )
        mock_get.side_effect = error

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            resource = SecEdgarResource(identity="Test User test@example.com")

            # Act & Assert - retryable error should be wrapped
            with pytest.raises(RetryableHTTPError):
                resource.download_submissions_zip(cache_dir=cache_dir)


class TestNoaaApiResource:
    """Test suite for NOAA API resource."""

    def test_initialization(self):
        """Test that NoaaApiResource initializes with API token."""
        resource = NoaaApiResource(api_token="test_token_12345")
        assert resource.api_token == "test_token_12345"

    @patch("pipelines.resources.requests.get")
    def test_get_daily_data_success(self, mock_get):
        """Test fetching daily weather data successfully."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "DATE": "2024-01-01",
                "TMAX": 10.5,
                "TMIN": 2.3,
                "PRCP": 0.0,
                "STATION": "USW00094728",
            },
            {
                "DATE": "2024-01-02",
                "TMAX": 12.1,
                "TMIN": 3.8,
                "PRCP": 5.2,
                "STATION": "USW00094728",
            },
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute
        resource = NoaaApiResource(api_token="test_token")
        result = resource.get_daily_data("USW00094728", "2024-01-01", "2024-01-02")

        # Verify request was made correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]["headers"]["token"] == "test_token"
        assert call_args[1]["params"]["dataset"] == "daily-summaries"
        assert call_args[1]["params"]["stations"] == "USW00094728"

        # Verify DataFrame structure
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "date" in result.columns
        assert "TMAX" in result.columns

    @patch("pipelines.resources.requests.get")
    def test_get_monthly_data_success(self, mock_get):
        """Test fetching monthly weather data successfully."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = [
            {"DATE": "2024-01", "TAVG": 8.5, "TMAX": 15.0, "TMIN": 2.0, "PRCP": 45.3},
            {"DATE": "2024-02", "TAVG": 9.2, "TMAX": 16.5, "TMIN": 2.8, "PRCP": 52.1},
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute
        resource = NoaaApiResource(api_token="test_token")
        result = resource.get_monthly_data("USW00094728", "2024-01", "2024-02")

        # Verify
        call_args = mock_get.call_args
        assert call_args[1]["params"]["dataset"] == "global-summary-of-the-month"
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    @patch("pipelines.resources.requests.get")
    def test_get_annual_data_success(self, mock_get):
        """Test fetching annual weather data successfully."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = [
            {"DATE": "2023", "TAVG": 12.5, "TMAX": 25.0, "TMIN": -5.0, "PRCP": 650.0},
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute
        resource = NoaaApiResource(api_token="test_token")
        result = resource.get_annual_data("USW00094728", "2023", "2023")

        # Verify
        call_args = mock_get.call_args
        assert call_args[1]["params"]["dataset"] == "global-summary-of-the-year"
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

    @patch("pipelines.resources.requests.get")
    def test_get_daily_data_empty_response(self, mock_get):
        """Test handling of empty API response."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute
        resource = NoaaApiResource(api_token="test_token")
        result = resource.get_daily_data("USW00094728")

        # Verify
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    @patch("pipelines.resources.requests.get")
    def test_date_conversion(self, mock_get):
        """Test that DATE column is converted to datetime."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = [
            {"DATE": "2024-01-15", "TMAX": 10.5, "TMIN": 2.3},
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute
        resource = NoaaApiResource(api_token="test_token")
        result = resource.get_daily_data("USW00094728")

        # Verify date conversion
        assert "date" in result.columns
        assert "DATE" not in result.columns
        assert pd.api.types.is_datetime64_any_dtype(result["date"])

    @patch("pipelines.resources.requests.get")
    def test_default_date_range(self, mock_get):
        """Test that default date range is set correctly."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute without date parameters
        resource = NoaaApiResource(api_token="test_token")
        resource.get_daily_data("USW00094728")

        # Verify default dates were used (last 10 years)
        call_args = mock_get.call_args
        assert "startDate" in call_args[1]["params"]
        assert "endDate" in call_args[1]["params"]


class TestNasaPowerApiResource:
    """Test suite for NASA POWER API resource."""

    def test_initialization(self):
        """Test that NasaPowerApiResource initializes without authentication."""
        resource = NasaPowerApiResource()
        # No attributes to check - NASA POWER doesn't require auth
        assert resource is not None

    @patch("pipelines.resources.requests.get")
    def test_get_daily_data_success(self, mock_get):
        """Test fetching daily agricultural weather data successfully."""
        # Setup mock response (NASA POWER format)
        mock_response = Mock()
        mock_response.json.return_value = {
            "properties": {
                "parameter": {
                    "T2M": {"20240101": 25.5, "20240102": 26.2},
                    "T2M_MAX": {"20240101": 32.1, "20240102": 33.5},
                    "T2M_MIN": {"20240101": 18.9, "20240102": 19.2},
                    "PRECTOTCORR": {"20240101": 2.5, "20240102": 0.0},
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute
        resource = NasaPowerApiResource()
        result = resource.get_daily_data(
            latitude=-18.94,
            longitude=-46.99,
            start_date="20240101",
            end_date="20240102",
        )

        # Verify request was made correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "daily" in call_args[0][0]  # URL contains 'daily'
        assert call_args[1]["params"]["latitude"] == -18.94
        assert call_args[1]["params"]["longitude"] == -46.99
        assert call_args[1]["params"]["community"] == "AG"

        # Verify DataFrame structure
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "date" in result.columns
        assert "T2M" in result.columns
        assert "latitude" in result.columns
        assert "longitude" in result.columns

    @patch("pipelines.resources.requests.get")
    def test_get_monthly_data_success(self, mock_get):
        """Test fetching monthly agricultural weather data successfully."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "properties": {
                "parameter": {
                    "T2M": {"202401": 24.5, "202402": 25.1},
                    "PRECTOTCORR": {"202401": 120.5, "202402": 95.3},
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute
        resource = NasaPowerApiResource()
        result = resource.get_monthly_data(
            latitude=-18.94, longitude=-46.99, start_date="202401", end_date="202402"
        )

        # Verify
        call_args = mock_get.call_args
        assert "monthly" in call_args[0][0]  # URL contains 'monthly'
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    @patch("pipelines.resources.requests.get")
    def test_get_daily_data_empty_response(self, mock_get):
        """Test handling of empty API response."""
        # Setup mock response with no data
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute
        resource = NasaPowerApiResource()
        result = resource.get_daily_data(latitude=-18.94, longitude=-46.99)

        # Verify
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    @patch("pipelines.resources.requests.get")
    def test_date_conversion(self, mock_get):
        """Test that date column is converted to datetime."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "properties": {
                "parameter": {
                    "T2M": {"20240115": 25.5},
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute
        resource = NasaPowerApiResource()
        result = resource.get_daily_data(latitude=-18.94, longitude=-46.99)

        # Verify date conversion
        assert "date" in result.columns
        assert pd.api.types.is_datetime64_any_dtype(result["date"])
        assert result["date"].iloc[0].year == 2024
        assert result["date"].iloc[0].month == 1
        assert result["date"].iloc[0].day == 15

    @patch("pipelines.resources.requests.get")
    def test_default_parameters(self, mock_get):
        """Test that default agricultural parameters are used."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {"properties": {"parameter": {}}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute without specifying parameters
        resource = NasaPowerApiResource()
        resource.get_daily_data(latitude=-18.94, longitude=-46.99)

        # Verify default parameters were used
        call_args = mock_get.call_args
        params_str = call_args[1]["params"]["parameters"]

        # Check that default agricultural parameters are present
        assert "T2M" in params_str
        assert "T2M_MAX" in params_str
        assert "T2M_MIN" in params_str
        assert "PRECTOTCORR" in params_str
        assert "RH2M" in params_str
        assert "TS" in params_str
        assert "ALLSKY_SFC_SW_DWN" in params_str

    @patch("pipelines.resources.requests.get")
    def test_coordinates_in_result(self, mock_get):
        """Test that latitude and longitude are added to result."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "properties": {"parameter": {"T2M": {"20240101": 25.5}}}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Execute
        resource = NasaPowerApiResource()
        result = resource.get_daily_data(latitude=-18.94, longitude=-46.99)

        # Verify coordinates are in result
        assert "latitude" in result.columns
        assert "longitude" in result.columns
        assert result["latitude"].iloc[0] == -18.94
        assert result["longitude"].iloc[0] == -46.99

    @patch("pipelines.resources.requests.get")
    def test_monthly_uses_yyyy_date_format(self, mock_get):
        """Test that monthly temporal resolution uses YYYY date format."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {"properties": {"parameter": {}}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Act
        resource = NasaPowerApiResource()
        resource.get_monthly_data(latitude=-18.94, longitude=-46.99)

        # Assert - NASA POWER monthly API requires YYYY (4 chars) request format
        # Note: response data uses YYYYMM format for individual months
        call_args = mock_get.call_args
        got_start = call_args[1]["params"]["start"]
        got_end = call_args[1]["params"]["end"]
        assert len(got_start) == 4, f"Monthly start should be YYYY, got {got_start}"
        assert len(got_end) == 4, f"Monthly end should be YYYY, got {got_end}"

    @patch("pipelines.resources.requests.get")
    def test_daily_uses_yyyymmdd_date_format(self, mock_get):
        """Test that daily temporal resolution uses YYYYMMDD date format."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {"properties": {"parameter": {}}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Act
        resource = NasaPowerApiResource()
        resource.get_daily_data(latitude=-18.94, longitude=-46.99)

        # Assert - date format should be YYYYMMDD (8 chars)
        call_args = mock_get.call_args
        got_start = call_args[1]["params"]["start"]
        got_end = call_args[1]["params"]["end"]
        assert len(got_start) == 8, f"Daily start should be YYYYMMDD, got {got_start}"
        assert len(got_end) == 8, f"Daily end should be YYYYMMDD, got {got_end}"
