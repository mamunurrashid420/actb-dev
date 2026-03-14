"""Form 13-F institutional holdings assets with time-based partitions.

Architecture:
- Bronze (API): form_13f[quarter] - Holdings fetched via API for recent quarters
- Bronze (Bulk): form_13f_bulk[quarter] - Holdings from DERA quarterly bulk downloads
- Silver: form_13f_holdings[quarter] - Validated holdings with portfolio %
- Gold: institutional_holdings (unpartitioned) - All data combined, filtered by registry

The bulk/API dual-source pattern follows USDA PSD - bulk for historical coverage,
API for freshness on recent quarters.
"""

import tempfile
import zipfile
from pathlib import Path

import dagster as dg
import pandas as pd
import polars as pl
from lxml import etree

from pipelines.assets.sec.common import (
    ASSET_GROUP,
    SecFilingConfig,
    extract_date_component,
    generate_portfolio_summary,
)
from pipelines.partitions import parse_quarter, sec_quarterly_partitions
from pipelines.resources import SecEdgarResource

# =============================================================================
# FORM 13F BULK DOWNLOAD ASSET (DERA Data Sets)
# =============================================================================


def _extract_file_from_zip(zip_path: Path, filename: str) -> Path:
    """Extract a single file from ZIP to temp directory, return path."""
    temp_dir = Path(tempfile.gettempdir()) / "form_13f_bulk"
    temp_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        # Find the file (case-insensitive)
        matching_files = [n for n in zf.namelist() if filename.lower() in n.lower()]
        if not matching_files:
            raise FileNotFoundError(f"{filename} not found in {zip_path}")

        target_file = matching_files[0]
        zf.extract(target_file, temp_dir)
        return temp_dir / target_file


@dg.asset(
    key_prefix=["bronze", "sec"],
    name="form_13f_bulk",
    partitions_def=sec_quarterly_partitions,
    group_name=ASSET_GROUP,
    pool="sec_api",
    retry_policy=dg.RetryPolicy(max_retries=3, delay=60),
    metadata={
        "layer": "bronze",
        "source": "sec_dera",
        "form_type": "13-F",
        "visibility": "internal",
    },
)
def bronze_form_13f_bulk(
    context: dg.AssetExecutionContext,
    sec_edgar: SecEdgarResource,
) -> pl.LazyFrame:
    """Fetch 13-F holdings from DERA bulk dataset for a quarter.

    Downloads SEC Form 13F Data Sets (quarterly ZIP files from DERA) and parses
    the INFOTABLE and SUBMISSION files to extract institutional holdings.

    Returns LazyFrame - IOManager calls sink_parquet() for streaming write.
    """
    partition_key = context.partition_key  # "2024-Q2"
    year, quarter = parse_quarter(partition_key)

    context.log.info(f"Downloading Form 13F Data Set for {partition_key}...")
    zip_path = sec_edgar.download_form_13f_dataset(partition_key)

    context.log.info(f"Extracting files from {zip_path}...")

    # Extract INFOTABLE and SUBMISSION files
    # Per SEC docs, files are tab-delimited text
    try:
        infotable_path = _extract_file_from_zip(zip_path, "INFOTABLE")
        submission_path = _extract_file_from_zip(zip_path, "SUBMISSION")
    except FileNotFoundError as e:
        context.log.error(f"Required file not found: {e}")
        return pl.LazyFrame()

    context.log.info("Parsing INFOTABLE and SUBMISSION files...")

    # Scan CSV lazily (tab-delimited)
    infotable_lf = pl.scan_csv(
        infotable_path,
        separator="\t",
        infer_schema_length=10000,
        ignore_errors=True,
    )

    submission_lf = pl.scan_csv(
        submission_path,
        separator="\t",
        infer_schema_length=10000,
        ignore_errors=True,
    )

    # INFOTABLE columns (per SEC docs):
    # ACCESSION_NUMBER, INFOTABLE_SK, NAMEOFISSUER, TITLEOFCLASS, CUSIP,
    # VALUE, SSHPRNAMT, SSHPRNAMTTYPE, PUTCALL, INVESTMENTDISCRETION,
    # OTHERMANAGER, VOTING_AUTHORITY_SOLE, VOTING_AUTHORITY_SHARED, VOTING_AUTHORITY_NONE

    # SUBMISSION columns (per SEC docs):
    # ACCESSION_NUMBER, FILING_DATE, SUBMISSIONTYPE, CIK, PERIODOFREPORT,
    # FILINGMANAGER_NAME, FILINGMANAGER_STREET1, FILINGMANAGER_CITY, etc.

    # Join and transform to match existing bronze_form_13f schema
    result = (
        infotable_lf
        .join(submission_lf, on="ACCESSION_NUMBER", how="left")
        .select([
            # Map to standard schema
            pl.col("CIK").cast(pl.Utf8).str.zfill(10).alias("institution_cik"),
            pl.col("FILINGMANAGER_NAME").alias("institution_name"),
            pl.col("ACCESSION_NUMBER").alias("accession_number"),
            pl.col("FILING_DATE").alias("filing_date"),
            pl.col("PERIODOFREPORT").alias("period_of_report"),
            pl.lit(year).alias("fiscal_year"),
            pl.lit(quarter).alias("quarter"),
            pl.col("NAMEOFISSUER").alias("holding_company_name"),
            pl.col("CUSIP").alias("cusip"),
            # VALUE is in thousands per SEC spec
            (pl.col("VALUE").cast(pl.Float64) * 1000).alias("market_value"),
            pl.col("SSHPRNAMT").cast(pl.Int64).alias("shares"),
            pl.col("TITLEOFCLASS").alias("security_type"),
        ])
        .filter(pl.col("institution_cik").is_not_null())
    )

    # Add output metadata (collect minimal stats)
    stats = result.select([
        pl.count().alias("num_holdings"),
        pl.col("institution_cik").n_unique().alias("num_institutions"),
    ]).collect()

    context.add_output_metadata({
        "partition": partition_key,
        "num_holdings": stats["num_holdings"][0],
        "num_institutions": stats["num_institutions"][0],
    })

    return result


def parse_form13f_xml(xml_content: str) -> list[dict]:
    """Parse 13-F information table XML and extract holdings.

    Args:
        xml_content: Raw XML content from infotable.xml

    Returns:
        List of holding dictionaries with issuer_name, cusip, market_value, shares
    """
    try:
        root = etree.fromstring(xml_content.encode())
    except Exception:
        return []

    # Handle namespace if present
    ns = {"ns": "http://www.sec.gov/edgar/document/thirteenf/informationtable"}

    holdings = []
    # Try with and without namespace
    info_tables = root.findall(".//infoTable") or root.findall(".//ns:infoTable", ns)

    def find_text(holding, path, ns):
        """Find text in holding element, trying with and without namespace."""
        elem = holding.find(path) or holding.find(path.replace("//", "//ns:"), ns)
        return elem.text if elem is not None else None

    for holding in info_tables:
        issuer_name = find_text(holding, ".//nameOfIssuer", ns)
        cusip = find_text(holding, ".//cusip", ns)
        value = find_text(holding, ".//value", ns)  # In thousands
        shares = find_text(holding, ".//sshPrnamt", ns)
        title_of_class = find_text(holding, ".//titleOfClass", ns)

        holdings.append({
            "issuer_name": issuer_name,
            "cusip": cusip,
            "market_value": (
                int(value) * 1000 if value else None
            ),  # Convert from thousands
            "shares": int(shares) if shares else None,
            "security_type": title_of_class if title_of_class else "Common Stock",
        })

    return holdings


@dg.asset(
    key_prefix=["bronze", "sec"],
    name="form_13f",
    partitions_def=sec_quarterly_partitions,
    group_name=ASSET_GROUP,
    pool="sec_api",
    retry_policy=dg.RetryPolicy(max_retries=3, delay=60),
    ins={
        "submissions": dg.AssetIn(key=["bronze", "sec", "submissions"]),
        "institution_registry": dg.AssetIn(
            key=["silver", "sec", "institution_registry"]
        ),
    },
    metadata={
        "layer": "bronze",
        "source": "sec_edgar",
        "form_type": "13-F",
        "visibility": "internal",
    },
)
def bronze_form_13f(
    context: dg.AssetExecutionContext,
    config: SecFilingConfig,
    sec_edgar: SecEdgarResource,
    submissions: pd.DataFrame,
    institution_registry: pd.DataFrame,
) -> pl.LazyFrame:
    """Fetch 13-F holdings for ALL enabled institutions in a given quarter."""
    partition_key = context.partition_key  # "2024-Q2"
    year, quarter = parse_quarter(partition_key)

    # Get enabled institutions from registry
    enabled_institutions = institution_registry.query("enabled == True")
    enabled_ciks = set(enabled_institutions["cik"].tolist())  # noqa: F841

    context.log.info(f"Fetching 13-F filings for {partition_key}...")
    context.log.info(
        f"Enabled institutions: {enabled_institutions['display_name'].tolist()}"
    )

    # Filter submissions to 13F-HR filings for enabled institutions in this quarter
    form_13f_submissions = (
        submissions.query("cik in @enabled_ciks").query('form == "13F-HR"').copy()
    )

    # Parse filing dates and filter to this quarter
    form_13f_submissions["filing_date_parsed"] = pd.to_datetime(
        form_13f_submissions["filingDate"]
    )
    form_13f_submissions["filing_year"] = form_13f_submissions[
        "filing_date_parsed"
    ].dt.year
    form_13f_submissions["filing_month"] = form_13f_submissions[
        "filing_date_parsed"
    ].dt.month

    # Calculate quarter month boundaries
    quarter_start_month = (quarter - 1) * 3 + 1  # noqa: F841
    quarter_end_month = quarter * 3  # noqa: F841

    quarter_filings = form_13f_submissions.query(
        "filing_year == @year and @quarter_start_month <= filing_month <= @quarter_end_month"
    )

    context.log.info(f"Found {len(quarter_filings)} 13F-HR filings in {partition_key}")

    results = []
    for filing_row in quarter_filings.itertuples(index=False):
        cik = filing_row.cik
        accession_number = filing_row.accessionNumber
        filing_date = str(filing_row.filing_date_parsed.date())

        # Get institution name from registry
        institution_info = enabled_institutions.query(f'cik == "{cik}"')
        if institution_info.empty:
            continue
        institution_name = institution_info["display_name"].iloc[0]

        try:
            # Try to fetch infotable.xml
            # Most 13F-HR filings have a primary document and an infotable.xml
            # The infotable filename is typically 'infotable.xml' or similar
            xml_content = None
            try:
                # Try standard infotable.xml
                xml_content = sec_edgar.fetch_filing_content(cik, accession_number)
            except Exception:
                # Try with infotable.xml suffix
                try:
                    xml_content = sec_edgar.fetch_filing_content(
                        cik, accession_number, filename="infotable.xml"
                    )
                except Exception as e:
                    context.log.debug(
                        f"Could not fetch infotable.xml for {institution_name} "
                        f"({accession_number}): {e}"
                    )
                    continue

            if not xml_content:
                continue

            # Parse XML to extract holdings
            holdings = parse_form13f_xml(xml_content)

            if not holdings:
                context.log.debug(
                    f"No holdings found for {institution_name} ({accession_number})"
                )
                continue

            # Get period of report from reportDate field if available
            period_of_report = (
                str(filing_row.reportDate)
                if hasattr(filing_row, "reportDate")
                else None
            )
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

            # Add each holding to results
            for holding in holdings:
                results.append({
                    "institution_cik": cik,
                    "institution_name": institution_name,
                    "accession_number": accession_number,
                    "filing_date": filing_date,
                    "period_of_report": period_of_report,
                    "fiscal_year": fiscal_year,
                    "quarter": fiscal_quarter,
                    "holding_company_name": holding["issuer_name"],
                    "cusip": holding["cusip"],
                    "shares": holding["shares"],
                    "market_value": holding["market_value"],
                    "security_type": holding["security_type"],
                })

        except Exception as e:
            context.log.warning(
                f"Error processing 13-F for {institution_name} ({accession_number}): {e}"
            )
            continue

    df = pd.DataFrame(results)

    context.add_output_metadata({
        "partition": partition_key,
        "num_holdings": len(df),
        "institutions_with_data": (
            df["institution_cik"].nunique() if len(df) > 0 else 0
        ),
    })

    # Return as LazyFrame for consistency with bulk asset and IOManager streaming
    return pl.LazyFrame(df)


def _quarters_ago(partition_key: str, current_quarter: str) -> int:
    """Calculate how many quarters ago a partition is relative to current quarter.

    Args:
        partition_key: Quarter string like "2024-Q2"
        current_quarter: Current quarter string like "2024-Q4"

    Returns:
        Number of quarters difference (0 = same quarter)
    """
    p_year, p_q = int(partition_key[:4]), int(partition_key[-1])
    c_year, c_q = int(current_quarter[:4]), int(current_quarter[-1])
    return (c_year - p_year) * 4 + (c_q - p_q)


def _get_current_quarter() -> str:
    """Get current quarter string like '2024-Q4'."""
    import datetime as dt

    today = dt.datetime.now()
    quarter = (today.month - 1) // 3 + 1
    return f"{today.year}-Q{quarter}"


@dg.asset(
    key_prefix=["silver", "sec"],
    name="form_13f_holdings",
    partitions_def=sec_quarterly_partitions,
    group_name=ASSET_GROUP,
    ins={
        "bronze_form_13f": dg.AssetIn(key=["bronze", "sec", "form_13f"]),
        "bronze_form_13f_bulk": dg.AssetIn(key=["bronze", "sec", "form_13f_bulk"]),
    },
    metadata={
        "layer": "silver",
        "data_quality": "validated",
        "visibility": "internal",
    },
)
def silver_form_13f_holdings(
    context: dg.AssetExecutionContext,
    bronze_form_13f: pl.LazyFrame,
    bronze_form_13f_bulk: pl.LazyFrame,
) -> pl.LazyFrame:
    """Merge bulk and API 13-F sources, clean, and enrich with portfolio %.

    Merge strategy (following USDA bulk/current pattern):
    - For historical quarters (> 2 quarters ago): use bulk data (more complete)
    - For recent quarters (current + last 2): prefer API data (fresher, catches amendments)

    Returns LazyFrame for streaming write.
    """
    partition_key = context.partition_key
    current_quarter = _get_current_quarter()
    quarters_ago = _quarters_ago(partition_key, current_quarter)

    context.log.info(
        f"Processing {partition_key} ({quarters_ago} quarters ago from {current_quarter})"
    )

    # Determine source priority based on recency
    # API data is fresher for recent quarters, bulk is more complete for historical
    is_recent = quarters_ago <= 2

    # Check which sources have data (both are LazyFrames now)
    has_api_data = bronze_form_13f.select(pl.count()).collect().item() > 0
    has_bulk_data = bronze_form_13f_bulk.select(pl.count()).collect().item() > 0

    context.log.info(
        f"API data available: {has_api_data}, Bulk data available: {has_bulk_data}"
    )

    # TODO: Factor out this merge logic -- it is a common pattern -- so we can
    # reuse and validate it properly.
    # Select primary source based on recency and availability
    if is_recent and has_api_data:
        # Recent quarter: prefer API (fresher, catches amendments)
        context.log.info("Using API data (recent quarter)")
        base_lf = bronze_form_13f
        source = "api"
    elif has_bulk_data:
        # Historical or no API data: use bulk
        context.log.info("Using bulk data")
        base_lf = bronze_form_13f_bulk
        source = "bulk"
    elif has_api_data:
        # Fallback to API if bulk not available
        context.log.info("Using API data (bulk not available)")
        base_lf = bronze_form_13f
        source = "api"
    else:
        # No data available
        context.log.warning("No data available from either source")
        return pl.LazyFrame()

    # Calculate percent_of_portfolio per institution/quarter
    result = base_lf.with_columns([
        (
            pl.col("market_value")
            / pl
            .col("market_value")
            .sum()
            .over(["institution_cik", "fiscal_year", "quarter"])
            * 100
        ).alias("percent_of_portfolio"),
    ])

    # Add output metadata (collect minimal stats)
    stats = result.select([
        pl.count().alias("num_holdings"),
        pl.col("institution_cik").n_unique().alias("num_institutions"),
    ]).collect()

    context.add_output_metadata({
        "partition": partition_key,
        "source": source,
        "num_holdings": stats["num_holdings"][0],
        "num_institutions": stats["num_institutions"][0],
    })

    return result


@dg.asset(
    key_prefix=["gold", "institutions", "portfolio"],
    name="holdings",
    group_name=ASSET_GROUP,
    automation_condition=dg.AutomationCondition.all_deps_updated_since_cron(
        "30 * * * *"  # 30 min offset from silver, runs when silver completes
    ),
    ins={
        "silver_holdings": dg.AssetIn(
            key=["silver", "sec", "form_13f_holdings"],
            partition_mapping=dg.AllPartitionMapping(),
        ),
        "institution_registry": dg.AssetIn(
            key=["silver", "sec", "institution_registry"],
        ),
    },
    metadata={
        "layer": "gold",
        "visibility": "llm_accessible",
    },
)
def gold_institutional_holdings(
    context: dg.AssetExecutionContext,
    silver_holdings: dict,
    institution_registry: pd.DataFrame,
) -> pd.DataFrame:
    """LLM-ready institutional holdings combining all quarters, filtered by registry."""
    context.log.info("Creating gold institutional holdings...")

    # Convert inputs to pandas DataFrames for aggregation
    # IOManager may return LazyFrame, DataFrame (Polars), or DataFrame (pandas)
    dfs = []
    for df in silver_holdings.values():
        if isinstance(df, pl.LazyFrame):
            collected = df.collect()
            if collected.height > 0:
                dfs.append(collected.to_pandas())
        elif isinstance(df, pl.DataFrame):
            if df.height > 0:
                dfs.append(df.to_pandas())
        elif isinstance(df, pd.DataFrame) and not df.empty:
            dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)

    # Filter to enabled institutions (from registry)
    enabled_ciks = set(institution_registry["cik"].tolist())  # noqa: F841
    combined = combined.query("institution_cik in @enabled_ciks")

    if combined.empty:
        return pd.DataFrame()

    # Create quarterly summaries with top holdings
    records = []
    for (cik, year, quarter), group in combined.groupby([
        "institution_cik",
        "fiscal_year",
        "quarter",
    ]):
        sorted_holdings = group.sort_values("market_value", ascending=False)
        top_10 = sorted_holdings.head(10)[
            [
                "holding_company_name",
                "cusip",
                "shares",
                "market_value",
                "percent_of_portfolio",
            ]
        ].to_dict("records")

        total_value = group["market_value"].sum()
        holdings_count = len(group)

        records.append({
            "institution_cik": cik,
            "institution_name": group["institution_name"].iloc[0],
            "fiscal_year": year,
            "quarter": quarter,
            "filing_date": group["filing_date"].iloc[0],
            "period_of_report": group["period_of_report"].iloc[0],
            "available": True,
            "holdings_count": holdings_count,
            "total_portfolio_value": total_value,
            "top_10_holdings": top_10,
            "key_takeaway": generate_portfolio_summary(
                institution_name=group["institution_name"].iloc[0],
                year=year,
                quarter=quarter,
                holdings_count=holdings_count,
                total_value=total_value,
                top_holdings=top_10,
            ),
        })

    result = pd.DataFrame(records)
    result = result.sort_values([
        "institution_cik",
        "fiscal_year",
        "quarter",
    ]).reset_index(drop=True)

    context.add_output_metadata({
        "num_quarterly_records": len(result),
        "num_institutions": (
            result["institution_cik"].nunique() if len(result) > 0 else 0
        ),
    })

    return result


__all__ = [
    "bronze_form_13f",
    "bronze_form_13f_bulk",
    "silver_form_13f_holdings",
    "gold_institutional_holdings",
]
