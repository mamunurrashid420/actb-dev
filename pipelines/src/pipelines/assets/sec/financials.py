"""Gold layer financials - SEC financial data with enrichment.

This module creates a single gold/sec/financials asset that:
1. Filters silver/sec/company_facts to relevant form types (10-K, 10-Q, etc.)
2. Joins with registry for ticker/company_name enrichment
3. Joins with taxonomy for human-readable labels

All US-GAAP concepts are included. Theme filtering happens at query time
via shared/data/themes.py in the data library.

Returns LazyFrame - IO manager handles streaming sharded parquet writes.
"""

import dagster as dg
import pandas as pd
import polars as pl

from pipelines.assets.sec.common import ASSET_GROUP

# All SEC form types with XBRL financial data
INCLUDED_FORM_TYPES = [
    # Annual reports
    "10-K",
    "10-K/A",
    "10-KT",
    "10-KT/A",
    # Quarterly reports
    "10-Q",
    "10-Q/A",
    "10-QT",
    "10-QT/A",
    # Foreign annual (ADRs)
    "20-F",
    "20-F/A",
    # Canadian annual
    "40-F",
    "40-F/A",
    # Foreign current reports
    "6-K",
    "6-K/A",
    # Current reports (material events)
    "8-K",
    "8-K/A",
]


@dg.asset(
    key_prefix=["gold", "sec"],
    name="financials",
    group_name=ASSET_GROUP,
    automation_condition=dg.AutomationCondition.all_deps_updated_since_cron(
        "30 * * * *"  # 30 min offset from silver, runs when silver completes
    ),
    ins={
        "company_facts": dg.AssetIn(key=["silver", "sec", "company_facts"]),
        "sec_filer_registry": dg.AssetIn(key=["bronze", "sec", "sec_filer_registry"]),
        "xbrl_taxonomy": dg.AssetIn(key=["silver", "sec", "xbrl_taxonomy"]),
    },
    metadata={
        "layer": "gold",
        "visibility": "llm_accessible",
        "questions_answered": [
            "What is {company}'s revenue?",
            "Is {company} profitable?",
            "What is {company}'s net income?",
            "How much debt does {company} have?",
            "What is {company}'s EPS?",
            "What dividends does {company} pay?",
            "What is {company}'s operating cash flow?",
            "How much does {company} spend on R&D?",
            "What is {company}'s effective tax rate?",
        ],
    },
)
def gold_sec_financials(
    context: dg.AssetExecutionContext,
    company_facts: pl.LazyFrame,
    sec_filer_registry: pd.DataFrame,
    xbrl_taxonomy: pd.DataFrame,
) -> pl.LazyFrame:
    """SEC financial data with ticker/label enrichment.

    Enriches company_facts with:
    - ticker and company_name from SEC filer registry
    - label from XBRL taxonomy (human-readable concept names)

    All US-GAAP concepts included. Theme filtering happens at query time.
    Returns LazyFrame - IO manager handles streaming sharded parquet writes.
    """
    context.log.info("Building gold/sec/financials...")

    # Convert registry and taxonomy to Polars lazy for efficient join
    lf_registry = (
        pl
        .from_pandas(sec_filer_registry)
        .lazy()
        .select(["cik", "ticker", "company_name"])
    )

    lf_taxonomy = pl.from_pandas(xbrl_taxonomy).lazy().select(["concept", "label"])

    # Build query: filter, join, select
    # All concepts included - theme filtering happens at query time
    context.log.info("Building lazy query...")
    lf = (
        company_facts
        # Filter to relevant form types and US-GAAP taxonomy
        .filter(pl.col("form_type").is_in(INCLUDED_FORM_TYPES))
        .filter(pl.col("taxonomy") == "us-gaap")
        # Join with registry for ticker/company_name
        .join(lf_registry, on="cik", how="left")
        # Filter to companies with tickers (public companies)
        .filter(
            pl.col("ticker").is_not_null()
            & pl.col("fiscal_year").is_not_null()
            & pl.col("fiscal_period").is_not_null()
        )
        # Join with taxonomy for label
        .join(lf_taxonomy, on="concept", how="left")
        # Convert date strings
        .with_columns([
            pl.col("end_date").str.to_date().alias("end_date"),
            pl.col("filed_date").str.to_date().alias("filed_date"),
        ])
        # Select final columns in desired order
        .select([
            "ticker",
            "company_name",
            "cik",
            "concept",
            "label",
            "value",
            "unit",
            "fiscal_year",
            "fiscal_period",
            "form_type",
            "end_date",
            "filed_date",
        ])
        .sort(["ticker", "fiscal_year", "fiscal_period", "concept"])
    )

    # Get stats via separate aggregation (doesn't force full collect)
    context.log.info("Computing metadata stats...")
    stats = lf.select([
        pl.len().alias("total_rows"),
        pl.col("ticker").n_unique().alias("num_companies"),
        pl.col("concept").n_unique().alias("num_concepts"),
    ]).collect()

    total_rows = stats["total_rows"][0]
    num_companies = stats["num_companies"][0]
    num_concepts = stats["num_concepts"][0]

    context.add_output_metadata({
        "num_records": total_rows,
        "num_companies": num_companies,
        "num_concepts": num_concepts,
        "form_types": INCLUDED_FORM_TYPES,
    })

    context.log.info(
        f"Returning LazyFrame: {total_rows:,} rows "
        f"({num_companies:,} companies, {num_concepts} concepts)"
    )

    # Return LazyFrame - IO manager handles streaming sharded write
    return lf


__all__ = [
    "gold_sec_financials",
]
