"""Form 10-Q quarterly report assets with time-based partitions.

Architecture:
- Bronze: form_10q_text[quarter] - Narrative text for ALL companies in that quarter
- Silver: form_10q_sections[quarter] - Cleaned narrative sections
- Gold: quarterly_reports (unpartitioned) - All data combined, filtered by registry

Uses bulk downloads architecture:
- Depends on bronze/sec/submissions for filing discovery
- Fetches individual HTML files only for enabled companies
- Partitioned quarterly (2024-Q1, 2024-Q2, etc.)
"""

import json

import dagster as dg
import pandas as pd
import polars as pl

from pipelines.assets.sec.common import (
    ASSET_GROUP,
    SecFilingConfig,
    extract_date_component,
    generate_financial_summary,
)
from pipelines.partitions import parse_quarter, sec_quarterly_partitions
from pipelines.resources import SecEdgarResource

# =============================================================================
# BRONZE LAYER - Raw Text Extraction
# =============================================================================


@dg.asset(
    key_prefix=["bronze", "sec"],
    name="form_10q_text",
    partitions_def=sec_quarterly_partitions,
    group_name=ASSET_GROUP,
    op_tags={"dagster/concurrency_key": "sec_api"},
    retry_policy=dg.RetryPolicy(max_retries=3, delay=60),
    ins={
        "submissions": dg.AssetIn(key=["bronze", "sec", "submissions"]),
        "company_registry": dg.AssetIn(key=["silver", "sec", "company_registry"]),
    },
    metadata={
        "layer": "bronze",
        "source": "sec_edgar",
        "form_type": "10-Q",
        "visibility": "internal",
    },
)
def bronze_form_10q_text(
    context: dg.AssetExecutionContext,
    config: SecFilingConfig,
    sec_edgar: SecEdgarResource,
    submissions: pd.DataFrame,
    company_registry: pd.DataFrame,
) -> pd.DataFrame:
    """Fetch 10-Q narrative text for ALL enabled companies in a given quarter.

    Uses bulk downloads architecture:
    1. Get filing metadata from bronze/sec/submissions
    2. Filter to 10-Q filings for enabled companies in this quarter
    3. Fetch individual HTML files using accession numbers
    4. Parse and store narrative sections
    """
    partition_key = context.partition_key  # "2024-Q2"
    year, quarter = parse_quarter(partition_key)

    # Get enabled companies from registry
    enabled_ciks = set(company_registry["cik"].tolist())

    context.log.info(f"Fetching 10-Q filings for {partition_key}...")
    context.log.info(f"Enabled companies: {len(enabled_ciks)} CIKs")

    # Filter submissions to 10-Q filings for enabled companies in this quarter
    filings = (
        submissions
        .query("form_type == '10-Q'")
        .query("cik in @enabled_ciks")
        .assign(
            filing_year=lambda x: x["filing_date"].dt.year,
            filing_quarter=lambda x: x["filing_date"].dt.quarter,
        )
        .query("filing_year == @year and filing_quarter == @quarter")
    )

    context.log.info(f"Found {len(filings)} 10-Q filings to fetch")

    results = []
    for _idx, filing in filings.iterrows():
        cik = filing["cik"]
        accession_number = filing["accession_number"]
        primary_document = filing.get("primary_document", "primary_doc.htm")

        # Map CIK back to ticker for logging
        ticker = company_registry.query("cik == @cik")["ticker"].iloc[0]

        try:
            # Fetch HTML content using bulk downloads pattern
            html_content = sec_edgar.fetch_filing_content(
                cik=cik,
                accession_number=accession_number,
                filename=primary_document,
            )

            # Extract period info (from filing metadata)
            period_of_report = filing.get("period_of_report")
            fiscal_year = (
                extract_date_component(period_of_report, "year")
                if period_of_report
                else year
            )
            fiscal_quarter = (
                extract_date_component(period_of_report, "quarter")
                if period_of_report
                else quarter
            )

            # For now, store the raw HTML - sec-parser integration can come later
            # In future: parse_narrative_sections(html_content)
            sections = {
                "raw_html_length": len(html_content) if html_content else 0,
                # Placeholder for parsed sections
                "financial_condition": None,  # Part I, Item 2 (MD&A)
                "quantitative_qualitative_disclosures": None,  # Part I, Item 3
            }

            results.append({
                "cik": cik,
                "ticker": ticker,
                "accession_number": accession_number,
                "filing_date": str(filing["filing_date"]),
                "period_of_report": period_of_report,
                "fiscal_year": fiscal_year,
                "quarter": fiscal_quarter,
                "sections": json.dumps(sections),
            })

        except Exception as e:
            context.log.warning(
                f"Error processing filing for {ticker} ({accession_number}): {e}"
            )
            continue

    df = pd.DataFrame(results)

    context.add_output_metadata({
        "partition": partition_key,
        "num_filings": len(df),
        "companies_with_filings": df["ticker"].nunique() if len(df) > 0 else 0,
    })

    context.log.info(f"Fetched {len(df)} 10-Q filings for {partition_key}")
    return df


# =============================================================================
# SILVER LAYER - Cleaned Sections
# =============================================================================


@dg.asset(
    key_prefix=["silver", "sec"],
    name="form_10q_sections",
    partitions_def=sec_quarterly_partitions,
    group_name=ASSET_GROUP,
    ins={
        "bronze_text": dg.AssetIn(key=["bronze", "sec", "form_10q_text"]),
    },
    metadata={
        "layer": "silver",
        "data_quality": "validated",
        "visibility": "internal",
    },
)
def silver_form_10q_sections(
    context: dg.AssetExecutionContext,
    bronze_text: pd.DataFrame,
) -> pd.DataFrame:
    """Clean and normalize 10-Q narrative sections."""
    partition_key = context.partition_key

    context.log.info(f"Cleaning 10-Q sections for {partition_key}...")

    if bronze_text.empty:
        context.log.warning(f"No 10-Q text data for {partition_key}")
        return pd.DataFrame()

    # For now, just pass through - text cleaning can be enhanced later
    df = bronze_text.copy()

    context.add_output_metadata({
        "partition": partition_key,
        "num_filings": len(df),
    })

    return df


@dg.asset(
    key_prefix=["silver", "sec"],
    name="form_10q_financials",
    group_name=ASSET_GROUP,
    ins={
        "company_facts": dg.AssetIn(key=["silver", "sec", "company_facts"]),
        "sec_filer_registry": dg.AssetIn(key=["bronze", "sec", "sec_filer_registry"]),
    },
    metadata={
        "layer": "silver",
        "data_quality": "validated",
        "visibility": "internal",
    },
)
def silver_form_10q_financials(
    context: dg.AssetExecutionContext,
    company_facts: pl.LazyFrame,
    sec_filer_registry: pd.DataFrame,
) -> pl.LazyFrame:
    """Extract 10-Q financials from bulk company facts for ALL companies.

    Extracts key financial statement concepts (Revenue, NetIncomeLoss, Assets, etc.)
    for all companies in the SEC filer registry (~10K companies).

    Includes amended forms (10-Q/A) and transition reports (10-QT, 10-QT/A).

    Uses Polars lazy evaluation throughout - returns LazyFrame that IO manager
    sinks to parquet. Memory efficient: ~763 MB vs 3.5 GB if using pandas.
    """
    context.log.info("Building 10-Q financials query (lazy)...")

    # Key financial concepts to extract (us-gaap taxonomy)
    key_concepts = [
        "Revenue",
        "Revenues",
        "NetIncomeLoss",
        "Assets",
        "Liabilities",
        "StockholdersEquity",
        "LiabilitiesAndStockholdersEquity",
        "CashAndCashEquivalentsAtCarryingValue",
        "OperatingIncomeLoss",
        "GrossProfit",
    ]

    # Include amended and transition forms
    form_types = ["10-Q", "10-Q/A", "10-QT", "10-QT/A"]

    # Convert registry to lazy for join
    lf_registry = pl.from_pandas(sec_filer_registry).lazy()

    # Build lazy query - all operations stay lazy until IO manager sinks
    lf_result = (
        company_facts
        .filter(pl.col("form_type").is_in(form_types))
        .filter(pl.col("concept").is_in(key_concepts))
        .filter(pl.col("taxonomy") == "us-gaap")
        .join(lf_registry.select(["cik", "ticker"]), on="cik", how="left")
        .sort(["ticker", "fiscal_year", "fiscal_period", "concept"])
    )

    # Collect stats for metadata (executes query once for counts)
    df_stats = (
        company_facts
        .filter(pl.col("form_type").is_in(form_types))
        .filter(pl.col("concept").is_in(key_concepts))
        .filter(pl.col("taxonomy") == "us-gaap")
        .select([
            pl.len().alias("num_records"),
            pl.col("cik").n_unique().alias("num_companies"),
            pl.col("concept").n_unique().alias("num_concepts"),
        ])
        .collect()
    )

    context.add_output_metadata({
        "num_records": int(df_stats["num_records"][0]),
        "num_companies": int(df_stats["num_companies"][0]),
        "num_concepts": int(df_stats["num_concepts"][0]),
    })

    context.log.info(
        f"Built lazy query for {df_stats['num_records'][0]:,} 10-Q records "
        f"from {df_stats['num_companies'][0]:,} companies"
    )
    return lf_result


# =============================================================================
# GOLD LAYER - Unpartitioned Quarterly Reports
# =============================================================================


@dg.asset(
    key_prefix=["gold", "companies", "financials"],
    name="quarterly_reports",
    group_name=ASSET_GROUP,
    automation_condition=dg.AutomationCondition.all_deps_updated_since_cron(
        "30 * * * *"  # 30 min offset from silver, runs when silver completes
    ),
    ins={
        "silver_sections": dg.AssetIn(
            key=["silver", "sec", "form_10q_sections"],
            partition_mapping=dg.AllPartitionMapping(),
        ),
        "company_registry": dg.AssetIn(
            key=["silver", "sec", "company_registry"],
        ),
    },
    metadata={
        "layer": "gold",
        "visibility": "llm_accessible",
        "questions_answered": [
            "What are {company}'s quarterly financials?",
            "Show me {company} 10-Q filing",
        ],
    },
)
def gold_quarterly_reports(
    context: dg.AssetExecutionContext,
    silver_sections: dict[str, pd.DataFrame],
    company_registry: pd.DataFrame,
) -> pd.DataFrame:
    """LLM-ready quarterly reports combining all quarters, filtered by registry."""
    context.log.info("Creating gold quarterly reports...")

    # Combine all quarters
    dfs = [df for df in silver_sections.values() if not df.empty]
    if not dfs:
        context.log.warning("No silver section data available")
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)

    # Filter to enabled companies (from registry)
    enabled_tickers = set(company_registry["ticker"].tolist())  # noqa: F841
    df = combined.query("ticker in @enabled_tickers")

    # Add key_takeaway
    df = df.assign(
        available=True,
        key_takeaway=lambda x: x.apply(
            lambda row: generate_financial_summary(
                ticker=row["ticker"],
                fiscal_year=row.get("fiscal_year"),
                quarter=row.get("quarter"),
            ),
            axis=1,
        ),
    )

    # Sort by ticker, fiscal year, and quarter
    df = df.sort_values(["ticker", "fiscal_year", "quarter"]).reset_index(drop=True)

    context.add_output_metadata({
        "num_reports": len(df),
        "num_companies": df["ticker"].nunique() if len(df) > 0 else 0,
        "fiscal_years": (
            sorted(df["fiscal_year"].unique().tolist()) if len(df) > 0 else []
        ),
    })

    context.log.info(f"Created {len(df)} quarterly reports")
    return df


__all__ = [
    "bronze_form_10q_text",
    "silver_form_10q_sections",
    "silver_form_10q_financials",
    "gold_quarterly_reports",
]
