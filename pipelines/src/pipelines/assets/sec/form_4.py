"""Form 4 insider trading assets with time-based partitions.

Architecture:
- Bronze: form_4[month] - Transaction data for ALL companies in that month
- Silver: form_4_transactions[month] - Validated transactions
- Gold: insider_activity (unpartitioned) - Aggregated activity, filtered by registry

Uses bulk downloads architecture:
- Depends on bronze/sec/submissions for filing discovery
- Fetches individual XML files only for enabled companies
- Partitioned monthly (2024-01, 2024-02, etc.)
"""

import dagster as dg
import pandas as pd
from lxml import etree

from pipelines.assets.sec.common import (
    ASSET_GROUP,
    SecFilingConfig,
    generate_insider_summary,
)
from pipelines.partitions import parse_month, sec_monthly_partitions
from pipelines.resources import SecEdgarResource

# =============================================================================
# XML PARSING HELPERS
# =============================================================================


def parse_form4_xml(xml_content: str) -> list[dict]:
    """Parse Form 4 XML and extract transactions.

    Args:
        xml_content: Raw XML content from Form 4 filing

    Returns:
        List of transaction dictionaries with standardized fields
    """
    try:
        root = etree.fromstring(xml_content.encode())
    except Exception:
        return []

    # Extract issuer info
    issuer_cik = root.findtext(".//issuerCik", default="")
    issuer_name = root.findtext(".//issuerName", default="")
    issuer_ticker = root.findtext(".//issuerTradingSymbol", default="")

    # Extract owner info
    owner_cik = root.findtext(".//rptOwnerCik", default="")
    owner_name = root.findtext(".//rptOwnerName", default="")

    # Extract relationship info
    is_director = root.findtext(".//isDirector", default="0")
    is_officer = root.findtext(".//isOfficer", default="0")
    officer_title = root.findtext(".//officerTitle", default="")

    # Determine insider title
    titles = []
    if is_director == "1":
        titles.append("Director")
    if is_officer == "1" and officer_title:
        titles.append(officer_title)
    elif is_officer == "1":
        titles.append("Officer")

    insider_title = ", ".join(titles) if titles else "Unknown"

    transactions = []

    # Parse non-derivative transactions
    for txn in root.findall(".//nonDerivativeTransaction"):
        txn_date = txn.findtext(".//transactionDate/value", default="")
        txn_code = txn.findtext(".//transactionCode", default="")
        shares_text = txn.findtext(".//transactionShares/value", default="")
        price_text = txn.findtext(".//transactionPricePerShare/value", default="")

        # Parse shares and price
        shares = float(shares_text) if shares_text else None
        price_per_share = float(price_text) if price_text else None

        # Calculate total value
        if shares is not None and price_per_share is not None:
            total_value = shares * price_per_share
        else:
            total_value = None

        transactions.append({
            "issuer_cik": issuer_cik.zfill(10) if issuer_cik else None,
            "issuer_name": issuer_name,
            "issuer_ticker": issuer_ticker,
            "owner_cik": owner_cik.zfill(10) if owner_cik else None,
            "owner_name": owner_name,
            "insider_title": insider_title,
            "transaction_date": txn_date,
            "transaction_code": txn_code,
            "shares": shares,
            "price_per_share": price_per_share,
            "total_value": total_value,
        })

    return transactions


# =============================================================================
# BRONZE LAYER - Raw XML Extraction
# =============================================================================


@dg.asset(
    key_prefix=["bronze", "sec"],
    name="form_4",
    partitions_def=sec_monthly_partitions,
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
        "form_type": "4",
        "visibility": "internal",
    },
)
def bronze_form_4(
    context: dg.AssetExecutionContext,
    config: SecFilingConfig,
    sec_edgar: SecEdgarResource,
    submissions: pd.DataFrame,
    company_registry: pd.DataFrame,
) -> pd.DataFrame:
    """Fetch Form 4 insider transactions for ALL enabled companies in a given month.

    Uses bulk downloads architecture:
    1. Get filing metadata from bronze/sec/submissions
    2. Filter to Form 4 filings for enabled companies in this month
    3. Fetch individual XML files using accession numbers
    4. Parse and store transaction data
    """
    partition_key = context.partition_key  # "2024-11"
    year, month = parse_month(partition_key)

    # Get enabled companies from registry
    enabled_ciks = set(company_registry["cik"].tolist())

    context.log.info(f"Fetching Form 4 filings for {partition_key}...")
    context.log.info(f"Enabled companies: {len(enabled_ciks)} CIKs")

    # Filter submissions to Form 4 filings for enabled companies in this month
    filings = (
        submissions
        .query("form_type == '4'")
        .query("cik in @enabled_ciks")
        .assign(
            filing_year=lambda x: x["filing_date"].dt.year,
            filing_month=lambda x: x["filing_date"].dt.month,
        )
        .query("filing_year == @year and filing_month == @month")
    )

    context.log.info(f"Found {len(filings)} Form 4 filings to fetch")

    all_transactions = []
    filings_processed = 0

    for _, filing in filings.iterrows():
        cik = filing["cik"]
        accession_number = filing["accession_number"]
        primary_document = filing.get("primary_document", "primary_doc.xml")

        # Map CIK back to ticker for logging
        ticker_match = company_registry.query("cik == @cik")
        ticker = ticker_match["ticker"].iloc[0] if len(ticker_match) > 0 else None

        try:
            # Fetch XML content using bulk downloads pattern
            xml_content = sec_edgar.fetch_filing_content(
                cik=cik,
                accession_number=accession_number,
                filename=primary_document,
            )

            # Parse Form 4 XML
            transactions = parse_form4_xml(xml_content)

            if not transactions:
                context.log.debug(
                    f"No transactions parsed from {ticker} filing {accession_number}"
                )
                continue

            # Add filing metadata to each transaction
            for txn in transactions:
                txn["cik"] = cik
                txn["ticker"] = ticker
                txn["accession_number"] = accession_number
                txn["filing_date"] = str(filing["filing_date"])

            all_transactions.extend(transactions)
            filings_processed += 1

        except Exception as e:
            context.log.warning(
                f"Error processing Form 4 for {ticker} ({accession_number}): {e}"
            )
            continue

    df = pd.DataFrame(all_transactions)

    context.add_output_metadata({
        "partition": partition_key,
        "num_transactions": len(df),
        "num_filings_processed": filings_processed,
        "companies_with_transactions": df["ticker"].nunique() if len(df) > 0 else 0,
    })

    context.log.info(
        f"Processed {filings_processed} Form 4 filings with {len(df)} transactions for {partition_key}"
    )

    return df


# =============================================================================
# SILVER LAYER - Validated Transactions
# =============================================================================


@dg.asset(
    key_prefix=["silver", "sec"],
    name="form_4_transactions",
    partitions_def=sec_monthly_partitions,
    group_name=ASSET_GROUP,
    ins={
        "bronze_form_4": dg.AssetIn(key=["bronze", "sec", "form_4"]),
    },
    metadata={
        "layer": "silver",
        "data_quality": "validated",
        "visibility": "internal",
    },
)
def silver_form_4_transactions(
    context: dg.AssetExecutionContext,
    bronze_form_4: pd.DataFrame,
) -> pd.DataFrame:
    """Clean and validate Form 4 transaction data."""
    if bronze_form_4.empty:
        return pd.DataFrame()

    # Filter out rows without valid transaction data
    df = bronze_form_4.dropna(
        subset=["transaction_date", "transaction_code"], how="all"
    ).assign(
        # Ensure insider_name is populated (fallback to owner_name)
        insider_name=lambda x: x["owner_name"],
    )

    context.add_output_metadata({
        "num_transactions": len(df),
    })

    return df


# =============================================================================
# GOLD LAYER - Unpartitioned Insider Activity
# =============================================================================


@dg.asset(
    key_prefix=["gold", "companies", "insider"],
    name="insider_activity",
    group_name=ASSET_GROUP,
    automation_condition=dg.AutomationCondition.all_deps_updated_since_cron(
        "30 * * * *"  # 30 min offset from silver, runs when silver completes
    ),
    ins={
        "silver_transactions": dg.AssetIn(
            key=["silver", "sec", "form_4_transactions"],
            partition_mapping=dg.AllPartitionMapping(),
        ),
        "company_registry": dg.AssetIn(
            key=["silver", "sec", "company_registry"],
        ),
    },
    metadata={
        "layer": "gold",
        "visibility": "llm_accessible",
    },
)
def gold_insider_activity(
    context: dg.AssetExecutionContext,
    silver_transactions: dict[str, pd.DataFrame],
    company_registry: pd.DataFrame,
) -> pd.DataFrame:
    """LLM-ready insider activity combining all months, filtered by registry."""
    context.log.info("Creating gold insider activity...")

    dfs = [df for df in silver_transactions.values() if not df.empty]
    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)

    enabled_tickers = set(company_registry["ticker"].tolist())  # noqa: F841
    combined = combined.query("ticker in @enabled_tickers")

    if combined.empty:
        return pd.DataFrame()

    # Extract year/month from filing_date for aggregation
    combined = combined.assign(
        filing_date_parsed=pd.to_datetime(combined["filing_date"]),
    )
    combined = combined.assign(
        year=combined["filing_date_parsed"].dt.year,
        month=combined["filing_date_parsed"].dt.month,
        is_buy=combined["transaction_code"].isin(["P", "M"]),
        is_sell=combined["transaction_code"] == "S",
    )

    # Aggregate by ticker, year, month
    def aggregate_group(group):
        buy_mask = group["is_buy"]
        sell_mask = group["is_sell"]

        return pd.Series({
            "cik": group["cik"].iloc[0],
            "transactions_count": len(group),
            "unique_insiders": group["insider_name"].nunique(),
            "shares_bought": (
                group.loc[buy_mask, "shares"].sum() if buy_mask.any() else 0
            ),
            "value_bought": (
                group.loc[buy_mask, "total_value"].sum() if buy_mask.any() else 0
            ),
            "shares_sold": (
                group.loc[sell_mask, "shares"].sum() if sell_mask.any() else 0
            ),
            "value_sold": (
                group.loc[sell_mask, "total_value"].sum() if sell_mask.any() else 0
            ),
        })

    result = (
        combined
        .groupby(["ticker", "year", "month"])
        .apply(aggregate_group)
        .reset_index()
    )

    result = result.assign(
        available=True,
        net_shares=lambda x: x["shares_bought"] - x["shares_sold"],
        net_value=lambda x: x["value_bought"] - x["value_sold"],
        key_takeaway=lambda x: x.apply(
            lambda row: generate_insider_summary(
                ticker=row["ticker"],
                year=int(row["year"]),
                month=int(row["month"]),
                txn_count=int(row["transactions_count"]),
                insider_count=int(row["unique_insiders"]),
                shares_bought=row["shares_bought"],
                shares_sold=row["shares_sold"],
                value_bought=row["value_bought"],
                value_sold=row["value_sold"],
            ),
            axis=1,
        ),
    )

    result = result.sort_values(["ticker", "year", "month"]).reset_index(drop=True)

    context.add_output_metadata({
        "num_monthly_records": len(result),
        "num_companies": result["ticker"].nunique() if len(result) > 0 else 0,
    })

    return result


__all__ = [
    "bronze_form_4",
    "silver_form_4_transactions",
    "gold_insider_activity",
]
