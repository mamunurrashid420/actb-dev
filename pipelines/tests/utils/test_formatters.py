"""Tests for formatting utilities."""

from pipelines.utils.formatters import FinancialFormatter


class TestFinancialFormatter:
    """Tests for FinancialFormatter class."""

    def test_to_billions(self):
        """Test conversion to billions."""
        result = FinancialFormatter.to_billions(1_500_000_000)
        assert result == 1.5

    def test_to_billions_none(self):
        """Test conversion with None."""
        result = FinancialFormatter.to_billions(None)
        assert result == 0.0

    def test_to_millions(self):
        """Test conversion to millions."""
        result = FinancialFormatter.to_millions(1_500_000)
        assert result == 1.5

    def test_to_millions_none(self):
        """Test conversion with None."""
        result = FinancialFormatter.to_millions(None)
        assert result == 0.0

    def test_format_financial_summary_with_data(self):
        """Test financial summary formatting with complete data."""
        result = FinancialFormatter.format_financial_summary(
            company_name="Apple Inc.",
            period="FY2023",
            revenue=1_000_000_000_000,
            net_income=150_000_000_000,
            net_margin=0.15,
            form_type="10-K filing",
        )
        assert "Apple Inc. FY2023:" in result
        assert "$1000.0B revenue" in result
        assert "$150.0B net income" in result
        assert "15.0% margin" in result

    def test_format_financial_summary_missing_data(self):
        """Test financial summary with missing data."""
        result = FinancialFormatter.format_financial_summary(
            company_name="Test Corp",
            period="FY2023",
            revenue=None,
            net_income=None,
            net_margin=None,
            form_type="10-K filing",
        )
        assert result == "Test Corp FY2023 10-K filing"

    def test_format_currency_billions(self):
        """Test currency formatting in billions."""
        result = FinancialFormatter.format_currency(1_500_000_000, billions=True)
        assert result == "$1.50B"

    def test_format_currency_millions(self):
        """Test currency formatting in millions."""
        result = FinancialFormatter.format_currency(1_500_000, billions=False)
        assert result == "$1.50M"

    def test_format_currency_none(self):
        """Test currency formatting with None."""
        result = FinancialFormatter.format_currency(None)
        assert result == "N/A"

    def test_format_percentage(self):
        """Test percentage formatting."""
        result = FinancialFormatter.format_percentage(0.1532)
        assert result == "15.3%"

    def test_format_percentage_custom_decimals(self):
        """Test percentage formatting with custom decimal places."""
        result = FinancialFormatter.format_percentage(0.1532, decimal_places=2)
        assert result == "15.32%"

    def test_format_percentage_none(self):
        """Test percentage formatting with None."""
        result = FinancialFormatter.format_percentage(None)
        assert result == "N/A"
