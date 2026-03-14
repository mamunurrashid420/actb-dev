"""Form 10-K annual report assets with time-based partitions.

Architecture:
- Bronze: form_10k_text[year] - Narrative text for ALL companies in that year
- Silver: form_10k_sections[year] - Cleaned narrative sections
- Gold: annual_reports (unpartitioned) - All data combined, filtered by registry

Uses bulk downloads architecture:
- Depends on bronze/sec/submissions for filing discovery
- Fetches individual HTML files only for enabled companies
- Parses with sec-parser (future enhancement)
"""

import json

import dagster as dg
import pandas as pd
import polars as pl

from pipelines.assets.sec.common import (
    ASSET_GROUP,
    SecFilingConfig,
    generate_financial_summary,
)
from pipelines.partitions import sec_yearly_partitions
from pipelines.resources import SecEdgarResource

# =============================================================================
# BRONZE LAYER - Raw Text Extraction
# =============================================================================


@dg.asset(
    key_prefix=["bronze", "sec"],
    name="form_10k_text",
    partitions_def=sec_yearly_partitions,
    group_name=ASSET_GROUP,
    ins={
        "submissions": dg.AssetIn(key=["bronze", "sec", "submissions"]),
        "company_registry": dg.AssetIn(key=["silver", "sec", "company_registry"]),
    },
    op_tags={"dagster/concurrency_key": "sec_api"},
    retry_policy=dg.RetryPolicy(max_retries=3, delay=60),
    metadata={
        "layer": "bronze",
        "source": "sec_edgar",
        "form_type": "10-K",
        "visibility": "internal",
    },
)
def bronze_form_10k_text(
    context: dg.AssetExecutionContext,
    config: SecFilingConfig,
    sec_edgar: SecEdgarResource,
    submissions: pd.DataFrame,
    company_registry: pd.DataFrame,
) -> pd.DataFrame:
    """Fetch 10-K narrative text for ALL enabled companies in a given year.

    Uses bulk downloads architecture:
    1. Get enabled CIKs from company_registry
    2. Filter submissions to 10-K filings for those CIKs in this year
    3. Fetch individual HTML files using accession numbers from submissions
    4. Parse narrative sections (placeholder for sec-parser integration)
    """
    year = int(context.partition_key)  # "2024" -> 2024

    # Get enabled companies from registry
    enabled_ciks = set(company_registry["cik"].tolist())  # noqa: F841

    context.log.info(f"Fetching 10-K filings for year {year}...")
    context.log.info(
        f"Enabled companies: {sorted(company_registry['ticker'].tolist())}"
    )

    # Filter submissions to 10-K filings for this year and enabled companies
    filings = (
        submissions
        .query("form_type == '10-K'")
        .query("cik in @enabled_ciks")
        .assign(filing_year=lambda x: x["filing_date"].dt.year)
        .query("filing_year == @year")
    )

    context.log.info(f"Found {len(filings)} 10-K filings for year {year}")

    results = []
    for filing in filings.itertuples():
        try:
            # Get ticker from registry
            ticker_match = company_registry.query(f"cik == '{filing.cik}'")
            ticker = ticker_match["ticker"].iloc[0] if len(ticker_match) > 0 else None

            context.log.info(
                f"Fetching {ticker} ({filing.cik}): {filing.accession_number}"
            )

            # Fetch HTML content using resource method (includes retry and rate limiting)
            html_content = sec_edgar.fetch_filing_content(
                cik=filing.cik,
                accession_number=filing.accession_number,
                filename=filing.primary_document,
            )

            # Extract fiscal year from report_date
            fiscal_year = (
                filing.report_date.year if pd.notna(filing.report_date) else year
            )

            # For now, store the raw HTML length - sec-parser integration can come later
            # In future: parse_narrative_sections(html_content)
            sections = {
                "raw_html_length": len(html_content) if html_content else 0,
                # Placeholder for parsed sections
                "business": None,  # Item 1
                "risk_factors": None,  # Item 1A
                "mda": None,  # Item 7
            }

            results.append({
                "cik": filing.cik,
                "ticker": ticker,
                "accession_number": filing.accession_number,
                "filing_date": str(filing.filing_date.date()),
                "period_of_report": (
                    str(filing.report_date.date())
                    if pd.notna(filing.report_date)
                    else None
                ),
                "fiscal_year": fiscal_year,
                "sections": json.dumps(sections),
            })

        except Exception as e:
            context.log.warning(
                f"Error processing {filing.accession_number} for {ticker}: {e}"
            )
            continue

    df = pd.DataFrame(results)

    context.add_output_metadata({
        "year": year,
        "num_filings": len(df),
        "companies_with_filings": df["ticker"].nunique() if len(df) > 0 else 0,
    })

    context.log.info(f"Fetched {len(df)} 10-K filings for year {year}")
    return df


# =============================================================================
# SILVER LAYER - Cleaned Sections
# =============================================================================


@dg.asset(
    key_prefix=["silver", "sec"],
    name="form_10k_sections",
    partitions_def=sec_yearly_partitions,
    group_name=ASSET_GROUP,
    ins={
        "bronze_text": dg.AssetIn(key=["bronze", "sec", "form_10k_text"]),
    },
    metadata={
        "layer": "silver",
        "data_quality": "validated",
        "visibility": "internal",
    },
)
def silver_form_10k_sections(
    context: dg.AssetExecutionContext,
    bronze_text: pd.DataFrame,
) -> pd.DataFrame:
    """Clean and normalize 10-K narrative sections."""
    year = context.partition_key

    context.log.info(f"Cleaning 10-K sections for year {year}...")

    if bronze_text.empty:
        context.log.warning(f"No 10-K text data for year {year}")
        return pd.DataFrame()

    # For now, just pass through - text cleaning can be enhanced later
    df = bronze_text.copy()

    context.add_output_metadata({
        "year": year,
        "num_filings": len(df),
    })

    return df


@dg.asset(
    key_prefix=["silver", "sec"],
    name="form_10k_financials",
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
def silver_form_10k_financials(
    context: dg.AssetExecutionContext,
    company_facts: pl.LazyFrame,
    sec_filer_registry: pd.DataFrame,
) -> pl.LazyFrame:
    """Extract 10-K financials from bulk company facts for ALL companies.

    Extracts key financial statement concepts (Revenue, NetIncomeLoss, Assets, etc.)
    for all companies in the SEC filer registry (~10K companies).

    Includes amended forms (10-K/A) and transition reports (10-KT, 10-KT/A).

    Uses Polars lazy evaluation throughout - returns LazyFrame that IO manager
    sinks to parquet. Memory efficient: ~763 MB vs 3.5 GB if using pandas.
    """
    context.log.info("Building 10-K financials query (lazy)...")

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
    form_types = ["10-K", "10-K/A", "10-KT", "10-KT/A"]

    # Convert registry to lazy for join
    lf_registry = pl.from_pandas(sec_filer_registry).lazy()

    # Build lazy query - all operations stay lazy until IO manager sinks
    lf_result = (
        company_facts
        .filter(pl.col("form_type").is_in(form_types))
        .filter(pl.col("concept").is_in(key_concepts))
        .filter(pl.col("taxonomy") == "us-gaap")
        .join(lf_registry.select(["cik", "ticker"]), on="cik", how="left")
        .sort(["ticker", "fiscal_year", "concept"])
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
        f"Built lazy query for {df_stats['num_records'][0]:,} 10-K records "
        f"from {df_stats['num_companies'][0]:,} companies"
    )
    return lf_result


# =============================================================================
# GOLD LAYER - Unpartitioned Annual Reports
# =============================================================================


@dg.asset(
    key_prefix=["gold", "companies", "financials"],
    name="annual_reports",
    group_name=ASSET_GROUP,
    automation_condition=dg.AutomationCondition.all_deps_updated_since_cron(
        "30 * * * *"  # 30 min offset from silver, runs when silver completes
    ),
    ins={
        "silver_sections": dg.AssetIn(
            key=["silver", "sec", "form_10k_sections"],
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
            "What are {company}'s annual financials?",
            "Show me {company} 10-K filing",
        ],
    },
)
def gold_annual_reports(
    context: dg.AssetExecutionContext,
    silver_sections: dict[str, pd.DataFrame],
    company_registry: pd.DataFrame,
) -> pd.DataFrame:
    """LLM-ready annual reports combining all years, filtered by registry."""
    context.log.info("Creating gold annual reports...")

    # Combine all years
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
            ),
            axis=1,
        ),
    )

    # Sort by ticker and fiscal year
    df = df.sort_values(["ticker", "fiscal_year"]).reset_index(drop=True)

    context.add_output_metadata({
        "num_reports": len(df),
        "num_companies": df["ticker"].nunique() if len(df) > 0 else 0,
        "fiscal_years": (
            sorted(df["fiscal_year"].unique().tolist()) if len(df) > 0 else []
        ),
    })

    context.log.info(f"Created {len(df)} annual reports")
    return df


__all__ = [
    "bronze_form_10k_text",
    "silver_form_10k_sections",
    "silver_form_10k_financials",
    "gold_annual_reports",
]
