"""Tests for SEC asset helper functions.

Tests validate helper functions used across SEC filing assets without making
actual SEC API calls.
"""

from pipelines.assets.sec import extract_date_component
from pipelines.utils.formatters import FinancialFormatter


class TestFormatCurrency:
    """Tests for FinancialFormatter.format_currency helper."""

    def test_format_billions(self):
        """Test formatting values >= 1 billion."""
        assert FinancialFormatter.format_currency(1_500_000_000) == "$1.50B"
        assert FinancialFormatter.format_currency(25_000_000_000) == "$25.00B"
        assert FinancialFormatter.format_currency(1_000_000_000) == "$1.00B"

    def test_format_millions(self):
        """Test formatting values < 1 billion."""
        assert FinancialFormatter.format_currency(500_000_000) == "$500.00M"
        assert FinancialFormatter.format_currency(25_000_000) == "$25.00M"
        assert FinancialFormatter.format_currency(1_000_000) == "$1.00M"

    def test_format_negative_values(self):
        """Test formatting negative values."""
        assert FinancialFormatter.format_currency(-1_500_000_000) == "$-1.50B"
        assert FinancialFormatter.format_currency(-25_000_000) == "$-25.00M"

    def test_format_zero(self):
        """Test formatting zero."""
        assert FinancialFormatter.format_currency(0) == "$0.00M"


class TestExtractDateComponent:
    """Tests for extract_date_component helper."""

    def test_extract_year(self):
        """Test extracting fiscal year from period string."""
        assert extract_date_component("2023-12-31", "year") == 2023
        assert extract_date_component("2024-06-30", "year") == 2024

    def test_extract_quarter(self):
        """Test extracting quarter from period string."""
        assert extract_date_component("2024-03-31", "quarter") == 1
        assert extract_date_component("2024-06-30", "quarter") == 2
        assert extract_date_component("2024-09-30", "quarter") == 3
        assert extract_date_component("2024-12-31", "quarter") == 4

    def test_extract_month(self):
        """Test extracting month from period string."""
        assert extract_date_component("2024-01-15", "month") == 1
        assert extract_date_component("2024-06-30", "month") == 6
        assert extract_date_component("2024-12-31", "month") == 12

    def test_invalid_component_returns_zero(self):
        """Test that invalid component returns 0."""
        assert extract_date_component("2024-06-30", "invalid") == 0

    def test_invalid_date_returns_zero(self):
        """Test that invalid date returns 0."""
        assert extract_date_component("not-a-date", "year") == 0
        assert extract_date_component(None, "year") == 0
