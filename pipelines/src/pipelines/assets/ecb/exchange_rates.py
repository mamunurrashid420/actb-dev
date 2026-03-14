"""ECB exchange rate assets - bronze and silver layers.

Bronze layer:
- exchange_rates: Daily EUR exchange rates from ECB SDMX API

Silver layer:
- exchange_rates: Enriched with computed metrics (MAs, volatility, USD crosses)
"""

import dagster as dg
import pandas as pd

from pipelines.assets.ecb.common import ASSET_GROUP, ECB_CURRENCIES
from pipelines.resources import EcbDataResource

# =============================================================================
# BRONZE LAYER
# =============================================================================


@dg.asset(
    key_prefix=["bronze", "ecb"],
    name="exchange_rates",
    group_name=ASSET_GROUP,
)
def bronze_exchange_rates(
    context: dg.AssetExecutionContext,
    ecb_data: EcbDataResource,
) -> pd.DataFrame:
    """Fetch all EUR exchange rates from ECB.

    Source: ECB SDMX API (public, no auth required)
    Coverage: 1999-present, daily rates for ~30 currencies
    Refresh: Weekly

    Exchange rates are point-in-time observations - no revisions to historical data.
    """
    context.log.info(
        f"Fetching ECB exchange rates for {len(ECB_CURRENCIES)} currencies..."
    )

    df = ecb_data.get_exchange_rates(
        frequency="D",
        currencies=ECB_CURRENCIES,
    )

    if df.empty:
        context.log.warning("No exchange rate data returned from ECB")
        return df

    context.add_output_metadata({
        "num_records": len(df),
        "date_range": (
            f"{df['date'].min()} to {df['date'].max()}"
            if "date" in df.columns and not df["date"].isna().all()
            else "N/A"
        ),
        "num_currencies": (df["currency"].nunique() if "currency" in df.columns else 0),
        "currencies": (
            sorted(df["currency"].unique().tolist()) if "currency" in df.columns else []
        ),
    })

    return df


# =============================================================================
# SILVER LAYER - COMPUTED METRICS
# =============================================================================


def compute_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """Compute moving averages for exchange rates."""
    if "rate" not in df.columns or "currency" not in df.columns:
        return df

    # Sort by currency and date for proper rolling calculation
    df = df.sort_values(["currency", "date"])

    # Compute MAs within each currency group
    df = df.assign(
        ma_7d=lambda x: x.groupby("currency")["rate"].transform(
            lambda s: s.rolling(7, min_periods=1).mean()
        ),
        ma_30d=lambda x: x.groupby("currency")["rate"].transform(
            lambda s: s.rolling(30, min_periods=1).mean()
        ),
        ma_90d=lambda x: x.groupby("currency")["rate"].transform(
            lambda s: s.rolling(90, min_periods=1).mean()
        ),
        ma_200d=lambda x: x.groupby("currency")["rate"].transform(
            lambda s: s.rolling(200, min_periods=1).mean()
        ),
    )

    return df


def compute_volatility(df: pd.DataFrame) -> pd.DataFrame:
    """Compute rolling volatility (30-day standard deviation)."""
    if "rate" not in df.columns or "currency" not in df.columns:
        return df

    df = df.assign(
        volatility_30d=lambda x: x.groupby("currency")["rate"].transform(
            lambda s: s.rolling(30, min_periods=1).std()
        ),
        volatility_pct=lambda x: (
            x["volatility_30d"] / x["ma_30d"].replace(0, pd.NA) * 100
        ).round(4),
    )

    return df


def compute_yoy_change(df: pd.DataFrame) -> pd.DataFrame:
    """Compute year-over-year change percentage."""
    if "rate" not in df.columns or "currency" not in df.columns:
        return df

    # Sort and compute YoY (approximately 252 trading days)
    df = df.sort_values(["currency", "date"])

    df = df.assign(
        rate_1yr_ago=lambda x: x.groupby("currency")["rate"].transform(
            lambda s: s.shift(252)
        ),
        yoy_change=lambda x: (
            (x["rate"] - x["rate_1yr_ago"]) / x["rate_1yr_ago"].replace(0, pd.NA) * 100
        ).round(4),
    )

    # Drop intermediate column
    df = df.drop(columns=["rate_1yr_ago"])

    return df


def compute_usd_cross_rates(df: pd.DataFrame) -> pd.DataFrame:
    """Compute USD cross rates from EUR-based rates.

    ECB provides EUR/XXX rates. This computes USD/XXX rates:
    USD/XXX = EUR/XXX / EUR/USD
    """
    if (
        "rate" not in df.columns
        or "currency" not in df.columns
        or "date" not in df.columns
    ):
        return df

    # Get EUR/USD rates indexed by date
    usd_rates = df[df["currency"] == "USD"][["date", "rate"]].set_index("date")["rate"]

    if usd_rates.empty:
        return df

    # Compute USD cross rate for each row
    def get_usd_cross(row):
        eur_usd = usd_rates.get(row["date"])
        if eur_usd and eur_usd > 0:
            return row["rate"] / eur_usd
        return None

    df = df.assign(usd_cross_rate=df.apply(get_usd_cross, axis=1))

    return df


def compute_distance_from_ma(df: pd.DataFrame) -> pd.DataFrame:
    """Compute percentage distance from 200-day moving average."""
    if "rate" not in df.columns or "ma_200d" not in df.columns:
        return df

    df = df.assign(
        distance_from_ma_200d=lambda x: (
            (x["rate"] - x["ma_200d"]) / x["ma_200d"].replace(0, pd.NA) * 100
        ).round(4)
    )

    return df


@dg.asset(
    key_prefix=["silver", "ecb"],
    name="exchange_rates",
    group_name=ASSET_GROUP,
    automation_condition=dg.AutomationCondition.all_deps_updated_since_cron(
        "0 * * * *"  # Hourly check, runs when bronze deps complete
    ),
    ins={
        "bronze_ecb_exchange_rates": dg.AssetIn(
            key=dg.AssetKey(["bronze", "ecb", "exchange_rates"]),
        ),
    },
)
def silver_exchange_rates(
    context: dg.AssetExecutionContext,
    bronze_ecb_exchange_rates: pd.DataFrame,
) -> pd.DataFrame:
    """Enrich exchange rates with computed metrics.

    Computed metrics:
    - Moving averages (7d, 30d, 90d, 200d)
    - Volatility (30d rolling std, volatility %)
    - Year-over-year change %
    - USD cross rates (EUR/XXX → USD/XXX)
    - Distance from 200d MA
    """
    if bronze_ecb_exchange_rates.empty:
        context.log.warning("Bronze exchange rates data is empty")
        return bronze_ecb_exchange_rates

    context.log.info("Computing exchange rate metrics...")

    df = (
        bronze_ecb_exchange_rates
        .pipe(compute_moving_averages)
        .pipe(compute_volatility)
        .pipe(compute_yoy_change)
        .pipe(compute_usd_cross_rates)
        .pipe(compute_distance_from_ma)
    )

    computed_cols = [
        c
        for c in df.columns
        if c
        in [
            "ma_7d",
            "ma_30d",
            "ma_90d",
            "ma_200d",
            "volatility_30d",
            "volatility_pct",
            "yoy_change",
            "usd_cross_rate",
            "distance_from_ma_200d",
        ]
    ]

    context.add_output_metadata({
        "num_records": len(df),
        "num_currencies": (df["currency"].nunique() if "currency" in df.columns else 0),
        "computed_columns": computed_cols,
    })

    return df


__all__ = [
    "bronze_exchange_rates",
    "silver_exchange_rates",
]
