"""Formatting utilities for financial data and summaries."""


class FinancialFormatter:
    """Format financial data for human-readable summaries.

    Example:
        FinancialFormatter.to_billions(1_500_000_000) → 1.5
        FinancialFormatter.format_currency(1_500_000_000, billions=True) → '$1.5B'
        FinancialFormatter.format_percentage(0.1532) → '15.3%'
    """

    @staticmethod
    def to_billions(value: float | None) -> float:
        """Convert to billions."""
        return value / 1_000_000_000 if value else 0.0

    @staticmethod
    def to_millions(value: float | None) -> float:
        """Convert to millions."""
        return value / 1_000_000 if value else 0.0

    @staticmethod
    def format_financial_summary(
        company_name: str,
        period: str,
        revenue: float | None,
        net_income: float | None,
        net_margin: float | None,
        form_type: str = "filing",
    ) -> str:
        """Generate summary string for financial filing."""
        if revenue and net_margin:
            revenue_b = FinancialFormatter.to_billions(revenue)
            net_income_b = FinancialFormatter.to_billions(net_income)
            margin_pct = net_margin * 100
            return (
                f"{company_name} {period}: "
                f"${revenue_b:.1f}B revenue, ${net_income_b:.1f}B net income "
                f"({margin_pct:.1f}% margin)"
            )
        else:
            return f"{company_name} {period} {form_type}"

    @staticmethod
    def format_currency(value: float | None, billions: bool | None = None) -> str:
        """Format currency as $XB or $XM.

        Args:
            value: Dollar amount to format
            billions: If True, format as billions. If False, format as millions.
                     If None (default), auto-detect based on value size.

        Returns:
            Formatted string like "$123.45B" or "$67.8M"
        """
        if value is None:
            return "N/A"

        # Auto-detect if not specified
        if billions is None:
            billions = abs(value) >= 1e9

        if billions:
            converted = FinancialFormatter.to_billions(value)
            return f"${converted:.2f}B"
        else:
            converted = FinancialFormatter.to_millions(value)
            return f"${converted:.2f}M"

    @staticmethod
    def format_percentage(value: float | None, decimal_places: int = 1) -> str:
        """Format decimal as percentage (0.15 → 15.0%)."""
        if value is None:
            return "N/A"
        pct = value * 100
        return f"{pct:.{decimal_places}f}%"
