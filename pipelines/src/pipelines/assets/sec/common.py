"""Shared utilities, schemas, and constants for SEC assets.

This module contains helper functions and constants that are used across
multiple SEC filing types (10-K, 10-Q, Form 4, 13-F).
"""

import datetime as dt

import dagster as dg
import numpy as np

from pipelines.utils.formatters import FinancialFormatter

# =============================================================================
# CONSTANTS
# =============================================================================

ASSET_GROUP = "sec_filings"


# =============================================================================
# RUNTIME CONFIGURATION
# =============================================================================


class SecFilingConfig(dg.Config):
    """Runtime configuration for SEC filing assets.

    Use from the Dagster UI Launchpad to limit filings fetched during testing.
    """

    min_year: int | None = None  # If set, skip filings before this year


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def extract_date_component(period_of_report: str, component: str) -> int:
    """Extract year, quarter, or month from period_of_report date string."""
    try:
        date = dt.datetime.strptime(period_of_report, "%Y-%m-%d")
        extractors = {
            "year": date.year,
            "quarter": (date.month - 1) // 3 + 1,
            "month": date.month,
        }
        return extractors.get(component, 0)
    except (ValueError, TypeError):
        return 0


def generate_financial_summary(
    ticker: str,
    fiscal_year: int | None = None,
    quarter: int | None = None,
    revenue: float | None = None,
    net_income: float | None = None,
    net_margin: float | None = None,
) -> str:
    """Generate a concise financial summary for LLM consumption."""
    # Determine period label
    if quarter is not None:
        period_label = f"{fiscal_year}-Q{quarter}"
    elif fiscal_year is not None:
        period_label = f"FY{fiscal_year}"
    else:
        period_label = "Unknown Period"

    if not revenue or not net_income:
        return f"{ticker} {period_label}: Financial data incomplete"

    revenue_str = FinancialFormatter.format_currency(revenue)
    income_str = FinancialFormatter.format_currency(net_income)
    margin_str = FinancialFormatter.format_percentage(net_margin)

    return f"{ticker} {period_label}: Revenue {revenue_str}, Net Income {income_str}, Margin {margin_str}"


def generate_insider_summary(
    ticker: str,
    year: int,
    month: int,
    txn_count: int,
    insider_count: int,
    shares_bought: float,
    shares_sold: float,
    value_bought: float,
    value_sold: float,
) -> str:
    """Generate a concise insider activity summary for LLM consumption."""
    if txn_count == 0:
        return f"{ticker} {year}-{month:02d}: No insider activity"

    net_shares = shares_bought - shares_sold
    net_value = value_bought - value_sold

    sign = int(np.sign(net_shares))
    direction = {1: "net buying", -1: "net selling", 0: "balanced activity"}.get(
        sign, "balanced activity"
    )

    # Format smaller values as K for insider activity (typically smaller amounts)
    if abs(net_value) >= 1e6:
        value_str = FinancialFormatter.format_currency(abs(net_value))
    else:
        value_str = f"${abs(net_value) / 1e3:.1f}K"

    return f"{ticker} {year}-{month:02d}: {txn_count} transactions by {insider_count} insiders, {direction} ({value_str})"


def generate_portfolio_summary(
    institution_name: str,
    year: int,
    quarter: int,
    holdings_count: int,
    total_value: float,
    top_holdings: list[dict],
) -> str:
    """Generate a concise portfolio summary for LLM consumption."""
    if holdings_count == 0:
        return f"{institution_name} {year}-Q{quarter}: No holdings reported"

    value_str = FinancialFormatter.format_currency(total_value)
    top_names = [h.get("holding_company_name", "Unknown") for h in top_holdings[:3]]
    top_str = ", ".join(top_names) if top_names else "N/A"

    return f"{institution_name} {year}-Q{quarter}: {holdings_count} holdings worth {value_str}. Top positions: {top_str}"


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # Constants
    "ASSET_GROUP",
    # Runtime config
    "SecFilingConfig",
    # Helper functions
    "extract_date_component",
    "generate_financial_summary",
    "generate_insider_summary",
    "generate_portfolio_summary",
]
