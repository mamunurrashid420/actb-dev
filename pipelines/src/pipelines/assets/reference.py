"""
Silver layer reference and crosswalk assets for ID mapping between source-native and semantic identifiers.
"""

import dagster as dg
import pandas as pd


@dg.asset(
    key_prefix=["silver", "reference"],
    name="indicator_id_crosswalk",
    code_version="1",
    metadata={
        "layer": "silver",
        "description": "Master mapping from source series IDs to indicator slugs",
        "visibility": "internal",
    },
)
def indicator_id_crosswalk() -> pd.DataFrame:
    """
    Master mapping from source series IDs to canonical indicator slugs.

    Returns:
        DataFrame with columns: source | source_series_id | canonical_slug | display_name
    """
    data = [
        # FRED economic indicators
        ("fred", "GDP", "gdp", "Gross Domestic Product"),
        ("fred", "UNRATE", "unemployment", "Unemployment Rate"),
        ("fred", "CPIAUCSL", "inflation", "Consumer Price Index"),
        ("fred", "PCE", "consumer_spending", "Personal Consumption Expenditures"),
        ("fred", "FEDFUNDS", "interest_rate", "Federal Funds Rate"),
        # BLS labor market indicators (21-char format since Oct 2020)
        ("bls", "JTS000000000000000JOL", "job_openings", "JOLTS Job Openings"),
        ("bls", "JTS000000000000000QUR", "quit_rate", "JOLTS Quit Rate"),
        ("bls", "CIU1010000000000A", "wage_inflation", "Employment Cost Index"),
        ("bls", "WPUFD4", "producer_prices", "Producer Price Index - Final Demand"),
        (
            "bls",
            "LNS11300000",
            "labor_force_participation",
            "Labor Force Participation Rate",
        ),
        ("bls", "CES0500000003", "hourly_earnings", "Average Hourly Earnings"),
        ("bls", "LNS14000000", "unemployment", "Unemployment Rate"),
        ("bls", "CUSR0000SA0", "inflation", "CPI-U All Items"),
        # World Bank indicators
        ("worldbank", "NY.GDP.MKTP.CD", "gdp", "GDP Current USD"),
        ("worldbank", "NY.GDP.PCAP.CD", "gdp_per_capita", "GDP Per Capita"),
        (
            "worldbank",
            "GC.DOD.TOTL.GD.ZS",
            "government_debt",
            "Government Debt as % of GDP",
        ),
        ("worldbank", "SL.UEM.TOTL.ZS", "unemployment", "Unemployment Rate"),
        ("worldbank", "FP.CPI.TOTL.ZG", "inflation", "Inflation CPI"),
        ("worldbank", "EN.ATM.CO2E.PC", "co2_per_capita", "CO2 Emissions Per Capita"),
        (
            "worldbank",
            "BN.CAB.XOKA.GD.ZS",
            "trade_balance",
            "Current Account Balance % of GDP",
        ),
        ("worldbank", "FR.INR.RINR", "interest_rate", "Real Interest Rate"),
    ]

    return pd.DataFrame(
        data, columns=["source", "source_series_id", "canonical_slug", "display_name"]
    )
