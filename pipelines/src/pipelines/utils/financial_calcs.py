"""Financial ratio calculations with safe division."""


class FinancialRatios:
    """Calculate common financial ratios with safe division.

    Example:
        FinancialRatios.net_margin(1000, 150) → 0.15
        FinancialRatios.safe_divide(100, 0) → None
    """

    @staticmethod
    def safe_divide(numerator: float | None, denominator: float | None) -> float | None:
        """Divide two numbers, handling None and zero."""
        if numerator is None or denominator is None:
            return None
        if denominator == 0:
            return None
        return numerator / denominator

    @staticmethod
    def net_margin(revenue: float | None, net_income: float | None) -> float | None:
        """Calculate net profit margin (net_income / revenue)."""
        return FinancialRatios.safe_divide(net_income, revenue)

    @staticmethod
    def current_ratio(
        current_assets: float | None, current_liabilities: float | None
    ) -> float | None:
        """Calculate current ratio (current_assets / current_liabilities)."""
        return FinancialRatios.safe_divide(current_assets, current_liabilities)

    @staticmethod
    def return_on_equity(
        net_income: float | None, stockholders_equity: float | None
    ) -> float | None:
        """Calculate return on equity (net_income / stockholders_equity)."""
        return FinancialRatios.safe_divide(net_income, stockholders_equity)

    @staticmethod
    def debt_to_equity(
        total_debt: float | None, stockholders_equity: float | None
    ) -> float | None:
        """Calculate debt-to-equity ratio (total_debt / stockholders_equity)."""
        return FinancialRatios.safe_divide(total_debt, stockholders_equity)

    @staticmethod
    def calculate_all(data: dict) -> dict:
        """Calculate all common ratios and add to data dict."""
        data["net_margin"] = FinancialRatios.net_margin(
            data.get("revenue"), data.get("net_income")
        )
        data["current_ratio"] = FinancialRatios.current_ratio(
            data.get("current_assets"), data.get("current_liabilities")
        )
        data["return_on_equity"] = FinancialRatios.return_on_equity(
            data.get("net_income"), data.get("stockholders_equity")
        )
        data["debt_to_equity"] = FinancialRatios.debt_to_equity(
            data.get("total_debt"), data.get("stockholders_equity")
        )
        return data
