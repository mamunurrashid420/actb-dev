"""Tests for financial calculation utilities."""

from pipelines.utils.financial_calcs import FinancialRatios


class TestFinancialRatios:
    """Tests for FinancialRatios class."""

    def test_safe_divide_valid(self):
        """Test safe division with valid inputs."""
        result = FinancialRatios.safe_divide(100, 200)
        assert result == 0.5

    def test_safe_divide_zero_denominator(self):
        """Test safe division with zero denominator."""
        result = FinancialRatios.safe_divide(100, 0)
        assert result is None

    def test_safe_divide_none_numerator(self):
        """Test safe division with None numerator."""
        result = FinancialRatios.safe_divide(None, 100)
        assert result is None

    def test_safe_divide_none_denominator(self):
        """Test safe division with None denominator."""
        result = FinancialRatios.safe_divide(100, None)
        assert result is None

    def test_net_margin(self):
        """Test net margin calculation."""
        result = FinancialRatios.net_margin(1000, 150)
        assert result == 0.15

    def test_net_margin_none(self):
        """Test net margin with None."""
        result = FinancialRatios.net_margin(None, 150)
        assert result is None

    def test_current_ratio(self):
        """Test current ratio calculation."""
        result = FinancialRatios.current_ratio(500, 250)
        assert result == 2.0

    def test_current_ratio_zero_liabilities(self):
        """Test current ratio with zero liabilities."""
        result = FinancialRatios.current_ratio(500, 0)
        assert result is None

    def test_return_on_equity(self):
        """Test ROE calculation."""
        result = FinancialRatios.return_on_equity(150, 1000)
        assert result == 0.15

    def test_return_on_equity_none(self):
        """Test ROE with None."""
        result = FinancialRatios.return_on_equity(None, 1000)
        assert result is None

    def test_debt_to_equity(self):
        """Test debt-to-equity calculation."""
        result = FinancialRatios.debt_to_equity(300, 1000)
        assert result == 0.3

    def test_calculate_all(self):
        """Test calculating all ratios."""
        data = {
            "revenue": 1000,
            "net_income": 150,
            "current_assets": 500,
            "current_liabilities": 250,
            "stockholders_equity": 1000,
            "total_debt": 300,
        }
        result = FinancialRatios.calculate_all(data)

        assert result["net_margin"] == 0.15
        assert result["current_ratio"] == 2.0
        assert result["return_on_equity"] == 0.15
        assert result["debt_to_equity"] == 0.3

    def test_calculate_all_partial_data(self):
        """Test calculating ratios with partial data."""
        data = {
            "revenue": 1000,
            "net_income": None,
        }
        result = FinancialRatios.calculate_all(data)

        assert result["net_margin"] is None
        assert result["current_ratio"] is None
        assert result["return_on_equity"] is None
