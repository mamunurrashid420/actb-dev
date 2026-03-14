"""SEC Financial Statement Data Sets (FSDS) bronze asset.

FSDS provides quarterly bulk downloads with structured financial data including
dimensional/segment information that companyfacts.zip lacks.

Each quarterly zip contains 4 tab-delimited files:
- sub.txt: Submission metadata (CIK, company name, form type, dates)
- num.txt: Numeric data with SEGMENTS field (the key differentiator!)
- tag.txt: Tag definitions
- pre.txt: Presentation linkbase

The NUM file is sharded into ~35MB parquet chunks for efficient queries.

Source: https://www.sec.gov/dera/data/financial-statement-data-sets
"""

import zipfile
from pathlib import Path

import dagster as dg
import pandas as pd
import polars as pl
import pyarrow.parquet as pq

from pipelines.assets.sec.common import ASSET_GROUP
from pipelines.partitions import (
    fsds_quarterly_partitions,
    partition_key_to_fsds_filename,
)
from pipelines.resources import SecEdgarResource

# =============================================================================
# SHARDING CONFIGURATION
# =============================================================================

# Batch size for streaming writes
WRITE_BATCH_SIZE = 100_000

# Default rows per shard (~128MB for S3)
# Note: This asset uses manual sharding since it writes multiple outputs (sub, tag, pre, num)
_DEFAULT_ROWS_PER_SHARD = 8_192_000


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _write_sharded_parquet(
    file_handle,
    output_dir: Path,
    context: dg.AssetExecutionContext,
    rows_per_shard: int = _DEFAULT_ROWS_PER_SHARD,
) -> dict:
    """Stream CSV file to sharded parquet files.

    Uses polars for efficient CSV parsing and PyArrow for streaming writes.
    Shards at rows_per_shard boundaries for consistent file sizes.

    Args:
        file_handle: File-like object from zipfile
        output_dir: Directory to write parquet shards
        context: Dagster context for logging
        rows_per_shard: Max rows per shard file. Default 8,192,000 (~128 MB).

    Returns:
        Dict with total_rows and num_shards statistics
    """
    # Clear existing shards
    for old in output_dir.glob("*.parquet"):
        old.unlink()

    # Read CSV with polars (handles large files efficiently)
    df = pl.read_csv(file_handle, separator="\t", infer_schema_length=10000)
    total_rows = len(df)

    if total_rows == 0:
        return {"total_rows": 0, "num_shards": 0}

    # Convert to Arrow for efficient writing
    arrow_table = df.to_arrow()

    # Write in shards
    shard_num = 0
    for start_idx in range(0, total_rows, rows_per_shard):
        end_idx = min(start_idx + rows_per_shard, total_rows)
        shard_table = arrow_table.slice(start_idx, end_idx - start_idx)

        shard_path = output_dir / f"part-{shard_num:04d}.parquet"
        pq.write_table(shard_table, shard_path)

        shard_rows = end_idx - start_idx
        context.log.info(f"Wrote shard {shard_num}: {shard_rows:,} rows")
        shard_num += 1

    return {"total_rows": total_rows, "num_shards": shard_num}


# =============================================================================
# BRONZE ASSET
# =============================================================================


@dg.asset(
    key_prefix=["bronze", "sec"],
    name="fsds",
    partitions_def=fsds_quarterly_partitions,
    group_name=ASSET_GROUP,
    op_tags={"dagster/concurrency_key": "sec_api"},
    metadata={
        "layer": "bronze",
        "source": "sec_edgar",
        "description": "SEC Financial Statement Data Sets with segment data",
    },
)
def bronze_fsds(
    context: dg.AssetExecutionContext,
    sec_edgar: SecEdgarResource,
) -> dict:
    """Download and parse SEC Financial Statement Data Sets for a quarter.

    FSDS provides structured XBRL data including the `segments` field in the
    NUM file, which contains dimensional/axis information for segment reporting
    (geographic, business segment, product line breakdowns).

    Writes to: _data/assets/bronze/sec/fsds/partition={quarter}/
    - sub.parquet: Submission metadata
    - tag.parquet: Tag definitions
    - pre.parquet: Presentation linkbase
    - num/part-NNNN.parquet: Numeric data (sharded)

    Returns:
        Metadata dict with file statistics
    """
    partition_key = context.partition_key  # "2024-Q3"
    sec_filename = partition_key_to_fsds_filename(partition_key)  # "2024q3"

    context.log.info(f"Downloading FSDS for {partition_key} ({sec_filename}.zip)...")
    zip_path = sec_edgar.download_fsds_quarter(sec_filename)

    # Output directory structure
    output_dir = Path(f"_data/assets/bronze/sec/fsds/partition={partition_key}")
    output_dir.mkdir(parents=True, exist_ok=True)

    stats = {"partition": partition_key}

    with zipfile.ZipFile(zip_path, "r") as zf:
        # List files in archive
        file_list = zf.namelist()
        context.log.info(f"Archive contains: {file_list}")

        # Small files: write directly as single parquet
        for filename in ["sub.txt", "tag.txt", "pre.txt"]:
            if filename not in file_list:
                context.log.warning(f"{filename} not found in archive")
                continue

            context.log.info(f"Processing {filename}...")
            with zf.open(filename) as f:
                df = pl.read_csv(f, separator="\t", infer_schema_length=10000)

            parquet_name = filename.replace(".txt", ".parquet")
            df.write_parquet(output_dir / parquet_name)
            stats[filename.replace(".txt", "_rows")] = len(df)
            context.log.info(f"Wrote {parquet_name}: {len(df):,} rows")

        # NUM file: stream with sharding (large file)
        if "num.txt" in file_list:
            context.log.info("Processing num.txt (sharded)...")
            num_dir = output_dir / "num"
            num_dir.mkdir(exist_ok=True)

            with zf.open("num.txt") as f:
                num_stats = _write_sharded_parquet(f, num_dir, context)

            stats["num_rows"] = num_stats["total_rows"]
            stats["num_shards"] = num_stats["num_shards"]
        else:
            context.log.warning("num.txt not found in archive")

    # Add metadata for Dagster UI
    context.add_output_metadata({
        "partition": partition_key,
        "submissions": stats.get("sub_rows", 0),
        "tags": stats.get("tag_rows", 0),
        "presentations": stats.get("pre_rows", 0),
        "num_rows": stats.get("num_rows", 0),
        "num_shards": stats.get("num_shards", 0),
        "output_dir": str(output_dir),
    })

    return stats


# =============================================================================
# SILVER ASSET
# =============================================================================


def _get_bronze_fsds_path(partition_key: str) -> Path:
    """Get the bronze FSDS directory path for a partition."""
    return Path(f"_data/assets/bronze/sec/fsds/partition={partition_key}")


@dg.asset(
    key_prefix=["silver", "sec"],
    name="fsds_segments",
    partitions_def=fsds_quarterly_partitions,
    deps=[dg.AssetKey(["bronze", "sec", "fsds"])],
    group_name=ASSET_GROUP,
    metadata={
        "layer": "silver",
        "source": "sec_edgar",
        "description": "FSDS segment financials with parsed axis/member columns",
    },
)
def silver_fsds_segments(
    context: dg.AssetExecutionContext,
) -> "pd.DataFrame":
    """Extract segment financials from FSDS with parsed axis/member columns.

    Joins NUM (with segments) + SUB (for company metadata).
    Filters to rows with non-null segments.
    Parses segments into segment_axis and segment_member columns.

    Output schema:
    - cik: Zero-padded CIK
    - company_name: From SUB.name
    - concept: XBRL tag
    - unit: Unit of measure
    - value: Numeric value
    - accession_number: adsh
    - form_type: From SUB.form
    - fiscal_year: From SUB.fy
    - fiscal_period: From SUB.fp
    - filed_date: From SUB.filed
    - segment_axis: Parsed dimension type (BusinessSegments, GeographicAreas, etc.)
    - segment_member: Parsed member value (AllOther, NorthAmerica, etc.)
    """
    partition_key = context.partition_key
    bronze_dir = _get_bronze_fsds_path(partition_key)

    context.log.info(f"Loading bronze FSDS data for {partition_key}...")

    # Load SUB for company metadata
    sub_path = bronze_dir / "sub.parquet"
    sub = pl.read_parquet(sub_path).select([
        "adsh",
        pl.col("cik").cast(pl.Utf8).str.zfill(10).alias("cik"),
        pl.col("name").alias("company_name"),
        pl.col("form").alias("form_type"),
        pl.col("fy").alias("fiscal_year"),
        pl.col("fp").alias("fiscal_period"),
        pl.col("filed").cast(pl.Utf8).alias("filed_date"),
    ])

    context.log.info(f"Loaded {len(sub):,} submissions from SUB")

    # Load sharded NUM files
    num_dir = bronze_dir / "num"
    num = pl.scan_parquet(num_dir / "*.parquet")

    # Filter to rows with segments and select/rename columns
    segments_df = (
        num
        .filter(pl.col("segments").is_not_null())
        .select([
            "adsh",
            pl.col("tag").alias("concept"),
            pl.col("uom").alias("unit"),
            "value",
            "segments",
        ])
        .collect()
    )

    context.log.info(f"Found {len(segments_df):,} rows with segment data")

    if len(segments_df) == 0:
        context.log.warning("No segment data found in this quarter")
        # Return empty DataFrame with correct schema
        return pd.DataFrame(
            columns=[
                "cik",
                "company_name",
                "concept",
                "unit",
                "value",
                "accession_number",
                "form_type",
                "fiscal_year",
                "fiscal_period",
                "filed_date",
                "segment_axis",
                "segment_member",
            ]
        )

    # Parse segments: "BusinessSegments=AllOther;..." -> axis, member
    # Take first segment pair (most rows have one primary dimension)
    segments_parsed = (
        segments_df
        .with_columns([
            # Split on ';' and take first pair
            pl.col("segments").str.split(";").list.first().alias("_first_pair"),
        ])
        .with_columns([
            # Split on '=' to get axis and member
            pl.col("_first_pair").str.split("=").list.first().alias("segment_axis"),
            pl.col("_first_pair").str.split("=").list.last().alias("segment_member"),
        ])
        .drop(["segments", "_first_pair"])
    )

    # Rename adsh to accession_number for consistency
    segments_parsed = segments_parsed.rename({"adsh": "accession_number"})

    # Join with SUB for company metadata
    result = segments_parsed.join(
        sub.rename({"adsh": "accession_number"}),
        on="accession_number",
        how="left",
    )

    # Reorder columns for consistency
    result = result.select([
        "cik",
        "company_name",
        "concept",
        "unit",
        "value",
        "accession_number",
        "form_type",
        "fiscal_year",
        "fiscal_period",
        "filed_date",
        "segment_axis",
        "segment_member",
    ])

    context.log.info(f"Output: {len(result):,} segment rows")

    # Add metadata
    context.add_output_metadata({
        "partition": partition_key,
        "num_rows": len(result),
        "num_companies": result["cik"].n_unique(),
        "segment_axes": result["segment_axis"].unique().to_list()[:10],
    })

    # Convert to pandas for IO manager compatibility
    return result.to_pandas()


@dg.asset(
    key_prefix=["silver", "sec"],
    name="fsds_financials",
    partitions_def=fsds_quarterly_partitions,
    deps=[dg.AssetKey(["bronze", "sec", "fsds"])],
    group_name=ASSET_GROUP,
    metadata={
        "layer": "silver",
        "source": "sec_edgar",
        "description": "FSDS consolidated financials with statement classification",
    },
)
def silver_fsds_financials(
    context: dg.AssetExecutionContext,
) -> "pd.DataFrame":
    """Extract consolidated financials with statement type (BS/IS/CF/EQ).

    Filters to consolidated rows (no segments, no co-registrants).
    Joins with PRE to get statement classification.

    Output schema:
    - cik, company_name, concept, unit, value, accession_number
    - form_type, fiscal_year, fiscal_period, filed_date
    - statement_type: BS (Balance Sheet), IS (Income Statement), CF (Cash Flow), EQ (Equity)
    """
    partition_key = context.partition_key
    bronze_dir = _get_bronze_fsds_path(partition_key)

    context.log.info(f"Loading bronze FSDS data for {partition_key}...")

    # Load SUB for company metadata
    sub = pl.read_parquet(bronze_dir / "sub.parquet").select([
        "adsh",
        pl.col("cik").cast(pl.Utf8).str.zfill(10).alias("cik"),
        pl.col("name").alias("company_name"),
        pl.col("form").alias("form_type"),
        pl.col("fy").alias("fiscal_year"),
        pl.col("fp").alias("fiscal_period"),
        pl.col("filed").cast(pl.Utf8).alias("filed_date"),
    ])

    # Load PRE for statement classification (adsh + tag -> stmt)
    pre = (
        pl
        .read_parquet(bronze_dir / "pre.parquet")
        .select([
            "adsh",
            "tag",
            pl.col("stmt").alias("statement_type"),
        ])
        .unique(["adsh", "tag"])
    )  # One statement type per concept

    context.log.info(f"Loaded {len(sub):,} submissions, {len(pre):,} presentation rows")

    # Load NUM and filter to consolidated (no segments, no coreg)
    num = pl.scan_parquet(bronze_dir / "num" / "*.parquet")
    consolidated = (
        num
        .filter(pl.col("segments").is_null())
        .filter(pl.col("coreg").is_null())
        .select([
            "adsh",
            pl.col("tag").alias("concept"),
            pl.col("uom").alias("unit"),
            "value",
        ])
        .collect()
    )

    context.log.info(f"Found {len(consolidated):,} consolidated financial rows")

    if len(consolidated) == 0:
        return pd.DataFrame(
            columns=[
                "cik",
                "company_name",
                "concept",
                "unit",
                "value",
                "accession_number",
                "form_type",
                "fiscal_year",
                "fiscal_period",
                "filed_date",
                "statement_type",
            ]
        )

    # Join with PRE to get statement type
    # Note: polars join keeps left columns, right_on columns are just for matching
    with_stmt = consolidated.join(
        pre.rename({"tag": "concept"}),
        on=["adsh", "concept"],
        how="left",
    )

    # Join with SUB for company metadata
    result = with_stmt.rename({"adsh": "accession_number"}).join(
        sub.rename({"adsh": "accession_number"}),
        on="accession_number",
        how="left",
    )

    # Reorder columns
    result = result.select([
        "cik",
        "company_name",
        "concept",
        "unit",
        "value",
        "accession_number",
        "form_type",
        "fiscal_year",
        "fiscal_period",
        "filed_date",
        "statement_type",
    ])

    context.log.info(f"Output: {len(result):,} rows")
    context.add_output_metadata({
        "partition": partition_key,
        "num_rows": len(result),
        "num_companies": result["cik"].n_unique(),
        "statement_types": result["statement_type"]
        .value_counts()
        .to_pandas()
        .to_dict(),
    })

    return result.to_pandas()


@dg.asset(
    key_prefix=["silver", "sec"],
    name="fsds_subsidiaries",
    partitions_def=fsds_quarterly_partitions,
    deps=[dg.AssetKey(["bronze", "sec", "fsds"])],
    group_name=ASSET_GROUP,
    metadata={
        "layer": "silver",
        "source": "sec_edgar",
        "description": "FSDS co-registrant/subsidiary financials",
    },
)
def silver_fsds_subsidiaries(
    context: dg.AssetExecutionContext,
) -> "pd.DataFrame":
    """Extract co-registrant (subsidiary) financials for conglomerate analysis.

    Output schema:
    - parent_cik, parent_name, subsidiary_name
    - concept, unit, value, accession_number
    - form_type, fiscal_year, fiscal_period
    """
    partition_key = context.partition_key
    bronze_dir = _get_bronze_fsds_path(partition_key)

    context.log.info(f"Loading bronze FSDS data for {partition_key}...")

    # Load SUB for parent company metadata
    sub = pl.read_parquet(bronze_dir / "sub.parquet").select([
        "adsh",
        pl.col("cik").cast(pl.Utf8).str.zfill(10).alias("parent_cik"),
        pl.col("name").alias("parent_name"),
        pl.col("form").alias("form_type"),
        pl.col("fy").alias("fiscal_year"),
        pl.col("fp").alias("fiscal_period"),
    ])

    # Load NUM and filter to co-registrant rows
    num = pl.scan_parquet(bronze_dir / "num" / "*.parquet")
    coreg_rows = (
        num
        .filter(pl.col("coreg").is_not_null())
        .select([
            "adsh",
            pl.col("tag").alias("concept"),
            pl.col("uom").alias("unit"),
            "value",
            pl.col("coreg").alias("subsidiary_name"),
        ])
        .collect()
    )

    context.log.info(f"Found {len(coreg_rows):,} co-registrant rows")

    if len(coreg_rows) == 0:
        return pd.DataFrame(
            columns=[
                "parent_cik",
                "parent_name",
                "subsidiary_name",
                "concept",
                "unit",
                "value",
                "accession_number",
                "form_type",
                "fiscal_year",
                "fiscal_period",
            ]
        )

    # Join with SUB for parent metadata
    result = coreg_rows.rename({"adsh": "accession_number"}).join(
        sub.rename({"adsh": "accession_number"}),
        on="accession_number",
        how="left",
    )

    # Reorder columns
    result = result.select([
        "parent_cik",
        "parent_name",
        "subsidiary_name",
        "concept",
        "unit",
        "value",
        "accession_number",
        "form_type",
        "fiscal_year",
        "fiscal_period",
    ])

    context.log.info(f"Output: {len(result):,} rows")
    context.add_output_metadata({
        "partition": partition_key,
        "num_rows": len(result),
        "num_parents": result["parent_cik"].n_unique(),
        "num_subsidiaries": result["subsidiary_name"].n_unique(),
    })

    return result.to_pandas()


@dg.asset(
    key_prefix=["silver", "sec"],
    name="fsds_footnotes",
    partitions_def=fsds_quarterly_partitions,
    deps=[dg.AssetKey(["bronze", "sec", "fsds"])],
    group_name=ASSET_GROUP,
    metadata={
        "layer": "silver",
        "source": "sec_edgar",
        "description": "FSDS value footnotes for LLM context",
    },
)
def silver_fsds_footnotes(
    context: dg.AssetExecutionContext,
) -> "pd.DataFrame":
    """Extract footnotes providing context for financial values.

    Output schema:
    - cik, company_name, concept, value, footnote
    - accession_number, form_type, fiscal_year, fiscal_period
    """
    partition_key = context.partition_key
    bronze_dir = _get_bronze_fsds_path(partition_key)

    context.log.info(f"Loading bronze FSDS data for {partition_key}...")

    # Load SUB for company metadata
    sub = pl.read_parquet(bronze_dir / "sub.parquet").select([
        "adsh",
        pl.col("cik").cast(pl.Utf8).str.zfill(10).alias("cik"),
        pl.col("name").alias("company_name"),
        pl.col("form").alias("form_type"),
        pl.col("fy").alias("fiscal_year"),
        pl.col("fp").alias("fiscal_period"),
    ])

    # Load NUM and filter to rows with footnotes
    num = pl.scan_parquet(bronze_dir / "num" / "*.parquet")
    footnote_rows = (
        num
        .filter(pl.col("footnote").is_not_null())
        .select([
            "adsh",
            pl.col("tag").alias("concept"),
            "value",
            "footnote",
        ])
        .collect()
    )

    context.log.info(f"Found {len(footnote_rows):,} rows with footnotes")

    if len(footnote_rows) == 0:
        return pd.DataFrame(
            columns=[
                "cik",
                "company_name",
                "concept",
                "value",
                "footnote",
                "accession_number",
                "form_type",
                "fiscal_year",
                "fiscal_period",
            ]
        )

    # Join with SUB for company metadata
    result = footnote_rows.rename({"adsh": "accession_number"}).join(
        sub.rename({"adsh": "accession_number"}),
        on="accession_number",
        how="left",
    )

    # Reorder columns
    result = result.select([
        "cik",
        "company_name",
        "concept",
        "value",
        "footnote",
        "accession_number",
        "form_type",
        "fiscal_year",
        "fiscal_period",
    ])

    context.log.info(f"Output: {len(result):,} rows")
    context.add_output_metadata({
        "partition": partition_key,
        "num_rows": len(result),
        "num_companies": result["cik"].n_unique(),
    })

    return result.to_pandas()


@dg.asset(
    key_prefix=["silver", "sec"],
    name="fsds_company_metadata",
    partitions_def=fsds_quarterly_partitions,
    deps=[dg.AssetKey(["bronze", "sec", "fsds"])],
    group_name=ASSET_GROUP,
    metadata={
        "layer": "silver",
        "source": "sec_edgar",
        "description": "FSDS company metadata (SIC, filer status, WKSI)",
    },
)
def silver_fsds_company_metadata(
    context: dg.AssetExecutionContext,
) -> "pd.DataFrame":
    """Extract rich company metadata from FSDS SUB file.

    Output schema:
    - cik, company_name, sic_code, filer_status, wksi
    - country_business, state_business, country_incorporation
    - fiscal_year_end, form_type
    """
    partition_key = context.partition_key
    bronze_dir = _get_bronze_fsds_path(partition_key)

    context.log.info(f"Loading bronze FSDS SUB data for {partition_key}...")

    # Load SUB with all metadata fields
    sub = pl.read_parquet(bronze_dir / "sub.parquet").select([
        pl.col("cik").cast(pl.Utf8).str.zfill(10).alias("cik"),
        pl.col("name").alias("company_name"),
        pl.col("sic").alias("sic_code"),
        pl.col("afs").alias("filer_status"),  # 1-LAF, 2-ACC, 4-NON
        pl.col("wksi"),  # Well-known seasoned issuer
        pl.col("countryba").alias("country_business"),
        pl.col("stprba").alias("state_business"),
        pl.col("countryinc").alias("country_incorporation"),
        pl.col("fye").alias("fiscal_year_end"),
        pl.col("form").alias("form_type"),
        pl.col("filed").cast(pl.Utf8).alias("filed_date"),
    ])

    # Keep one row per CIK (most recent filing)
    result = sub.sort("filed_date", descending=True).unique(
        subset=["cik"], keep="first"
    )

    context.log.info(f"Output: {len(result):,} unique companies")
    context.add_output_metadata({
        "partition": partition_key,
        "num_companies": len(result),
        "filer_status_breakdown": result["filer_status"]
        .value_counts()
        .to_pandas()
        .to_dict(),
    })

    return result.to_pandas()


# =============================================================================
# GOLD ASSETS
# =============================================================================

# Segment axis normalization mapping
# Maps FSDS segment_axis values (from DIM file) to semantic types
# Values from SEC FSDS DIM file - over 1,200 unique values exist
# This maps the most common (~90% of data) to semantic categories
SEGMENT_AXIS_MAPPING = {
    # Business segments (~340K rows)
    "BusinessSegments": "business",
    "OperatingSegments": "business",
    "Segments": "business",
    "SegmentConsolidationItems": "business",
    # Geographic segments (~65K rows)
    "Geographical": "geographic",
    "GeographicalAreas": "geographic",
    "GeographicAreas": "geographic",
    "Countries": "geographic",
    # Product/service segments (~90K rows)
    "ProductOrService": "product",
    "Products": "product",
    "ProductsAndServices": "product",
    # Legal entity segments (~95K rows)
    "LegalEntity": "legal_entity",
    "Subsidiaries": "legal_entity",
    "SignificantInvestmentsInSubsidiaries": "legal_entity",
    # Consolidation (~180K rows)
    "ConsolidatedEntities": "consolidation",
    "ConsolidationItems": "consolidation",
    # Equity / ownership (~1.35M rows)
    "EquityComponents": "equity",
    "ClassOfStock": "equity",
    "ComponentsOfEquity": "equity",
    "CapitalUnitsByClass": "equity",
    "PartnerTypeOfPartnersCapitalAccount": "equity",
    # Investment identifiers (~1M rows)
    "InvestmentIdentifier": "investment",
    "InvestmentType": "investment",
    "InvestmentIssuerName": "investment",
    "EquitySecuritiesByIndustry": "investment",
    "EquityMethodInvestmentNonconsolidatedInvestee": "investment",
    "SignificantInvestmentsInAssociates": "investment",
    "ScheduleOfEquityMethodInvestmentEquityMethodInvesteeName": "investment",
}

# Filer status code mapping
FILER_STATUS_MAPPING = {
    "1-LAF": "Large Accelerated Filer",
    "2-ACC": "Accelerated Filer",
    "3-SRA": "Smaller Reporting Accelerated",
    "4-NON": "Non-accelerated Filer",
    "5-SRA": "Smaller Reporting Company",
}

# =============================================================================
# SEGMENT NAME NORMALIZATION (Native Polars - fast!)
# =============================================================================
#
# Patterns are evaluated in order - first match wins.
# Format: (regex_pattern, canonical_name)
# - Use (?i) prefix for case-insensitive matching
# - '_FILTER_OUT_' means filter out the row (meta-segments)

SEGMENT_NAME_PATTERNS = [
    # US variations (most specific first)
    (r"(?i)^U\.S\.Market$", "us"),
    (r"(?i)^USMarket$", "us"),
    (r"(?i)^UnitedStates(OfAmerica)?$", "us"),
    (r"(?i)^U\.S\.$", "us"),
    (r"(?i)^US$", "us"),
    (r"(?i)^Domestic$", "us"),
    # International/Non-US
    (r"(?i)^Non-?US$", "international"),
    (r"(?i)^NonUs$", "international"),
    (r"(?i)^International$", "international"),
    (r"(?i)^ForeignCountries$", "international"),
    (r"(?i)^OtherCountries$", "international"),
    (r"(?i)^OtherInternational$", "international"),
    # China
    (r"(?i)^GreaterChina$", "china"),
    (r"(?i)^China$", "china"),
    (r"(?i)^PRC$", "china"),
    (r"(?i)^CN$", "china"),
    # Europe
    (r"(?i)^EuropeMiddleEastAndAfrica$", "europe"),
    (r"(?i)^EuropeMiddleEastAfrica$", "europe"),
    (r"(?i)^EMEA$", "europe"),
    (r"(?i)^Europe$", "europe"),
    # Asia Pacific
    (r"(?i)^AsiaPacific$", "asia_pacific"),
    (r"(?i)^RestOfAsiaPacific$", "asia_pacific"),
    (r"(?i)^APAC$", "asia_pacific"),
    (r"(?i)^Asia$", "asia_pacific"),
    # Americas
    (r"(?i)^Americas$", "americas"),
    (r"(?i)^NorthAmerica$", "americas"),
    (r"(?i)^NAmerica$", "americas"),
    # Latin America
    (r"(?i)^LatinAmerica$", "latin_america"),
    (r"(?i)^SouthAmerica$", "latin_america"),
    (r"(?i)^LATAM$", "latin_america"),
    # Rest of World
    (r"(?i)^RestOfWorld$", "rest_of_world"),
    (r"(?i)^RestOfTheWorld$", "rest_of_world"),
    (r"(?i)^AllOtherCountries$", "rest_of_world"),
    # Corporate
    (r"(?i)^CorporateAndOther$", "corporate"),
    (r"(?i)^CorporateNon$", "corporate"),
    (r"(?i)^Corporate$", "corporate"),
    # Other/All Other (careful - "Other" is generic)
    (r"(?i)^AllOtherSegments$", "other"),
    (r"(?i)^AllOther$", "other"),
    (r"(?i)^Other$", "other"),
    (r"(?i)^Others$", "other"),
    # Meta-segments to filter out
    (r"(?i)^OperatingSegments$", "_FILTER_OUT_"),
    (r"(?i)^ReportableSegments$", "_FILTER_OUT_"),
    (r"(?i)^Reportable$", "_FILTER_OUT_"),
    (r"(?i)^SingleReportable$", "_FILTER_OUT_"),
    # Eliminations (contains match)
    (r"(?i)Elimination", "eliminations"),
    # International patterns (contains match - order matters!)
    (r"(?i)International.*Operated.*Markets?", "intl_operated"),
    (r"(?i)International.*Licensed.*Markets?", "intl_licensed"),
    (r"(?i)International.*Lead.*Markets?", "intl_lead"),
    (r"(?i)International.*Development", "intl_development"),
]


def build_segment_name_expr(col_name: str = "segment_name") -> pl.Expr:
    """Build Polars when/then/otherwise expression for segment normalization.

    Evaluates patterns in order - first match wins.
    Returns expression that maps segment_name to canonical snake_case name.
    """
    col = pl.col(col_name)

    # Fallback: convert to snake_case
    # Order matters:
    # 1. Insert underscores for CamelCase boundaries FIRST
    # 2. Then remove Member suffix (XBRL convention, not meaningful)
    # 3. Then shorten common words and lowercase
    fallback = (
        col.str
        .replace_all(r"([a-z])([A-Z])", r"${1}_${2}")
        .str.replace(r"_?Member$", "")
        .str.replace_all("International", "intl")
        .str.replace_all("And", "_")
        .str.to_lowercase()
        .str.strip_chars("_")
        .str.replace_all(r"_+", "_")
    )

    # Build expression chain (reverse order since we're wrapping)
    expr = fallback
    for pattern, canonical in reversed(SEGMENT_NAME_PATTERNS):
        expr = (
            pl.when(col.str.contains(pattern)).then(pl.lit(canonical)).otherwise(expr)
        )

    return expr


def normalize_segment_name(raw_name: str) -> str | None:
    """Normalize a single segment name using Polars.

    This is a convenience wrapper around build_segment_name_expr for testing
    and single-value normalization. For bulk operations, use the expression
    directly with DataFrame.with_columns().

    Returns None if segment should be filtered out (meta-segments).
    """
    df = pl.DataFrame({"segment_name": [raw_name]})
    result = df.with_columns(build_segment_name_expr().alias("canonical"))["canonical"][
        0
    ]

    if result == "_FILTER_OUT_":
        return None
    return result


@dg.asset(
    key_prefix=["gold", "sec"],
    name="segments",
    group_name=ASSET_GROUP,
    automation_condition=dg.AutomationCondition.all_deps_updated_since_cron(
        "30 * * * *"  # 30 min offset from silver, runs when silver completes
    ),
    ins={
        "sec_filer_registry": dg.AssetIn(key=["bronze", "sec", "sec_filer_registry"]),
    },
    deps=[dg.AssetKey(["silver", "sec", "fsds_segments"])],
    metadata={
        "layer": "gold",
        "visibility": "llm_accessible",
        "questions_answered": [
            "What is {company}'s revenue by region?",
            "How does {company}'s iPhone revenue compare to Services?",
            "What is {company}'s revenue breakdown by segment?",
            "What are {company}'s geographic segments?",
            "What products does {company} report separately?",
        ],
    },
)
def gold_sec_segments(
    context: dg.AssetExecutionContext,
    sec_filer_registry: pd.DataFrame,
) -> dict:
    """Segment financials with ticker enrichment and normalized segment types.

    Aggregates all quarterly FSDS segment data and enriches with:
    - ticker from SEC filer registry
    - normalized segment_type (geographic, product, business)
    - cleaned segment_name (strips 'Member' suffix)
    - label from FSDS TAG file
    """
    context.log.info("Building gold/sec/segments...")

    # Load all silver segment partitions
    silver_dir = Path("_data/assets/silver/sec/fsds_segments")
    partition_dirs = list(silver_dir.glob("partition=*/data.parquet"))

    if not partition_dirs:
        context.log.warning("No silver segment partitions found")
        return {"total_rows": 0, "num_shards": 0}

    context.log.info(f"Loading {len(partition_dirs)} partitions...")
    segments = pl.scan_parquet([str(p) for p in partition_dirs])

    # Load TAG files for labels (from most recent quarter)
    bronze_dirs = sorted(Path("_data/assets/bronze/sec/fsds").glob("partition=*"))
    if bronze_dirs:
        latest_bronze = bronze_dirs[-1]
        tag_path = latest_bronze / "tag.parquet"
        if tag_path.exists():
            tag_df = (
                pl
                .read_parquet(tag_path)
                .select([
                    pl.col("tag").alias("concept"),
                    pl.col("tlabel").alias("label"),
                ])
                .unique("concept")
            )
            context.log.info(f"Loaded {len(tag_df):,} labels from TAG")
        else:
            tag_df = None
    else:
        tag_df = None

    # Convert registry to Polars
    lf_registry = pl.from_pandas(sec_filer_registry).lazy().select(["cik", "ticker"])

    # Build query
    lf = (
        segments
        # Join with registry for ticker
        .join(lf_registry, on="cik", how="left")
        # Filter to companies with tickers
        .filter(pl.col("ticker").is_not_null())
        # Normalize segment_axis to segment_type
        .with_columns([
            pl
            .col("segment_axis")
            .replace(SEGMENT_AXIS_MAPPING, default="other")
            .alias("segment_type"),
            # Clean segment_member: strip 'Member' suffix
            pl
            .col("segment_member")
            .str.replace("Member$", "")
            .str.replace("Segment$", "")
            .alias("segment_name"),
        ])
    )

    # Apply segment name normalization (native Polars - fast!)
    context.log.info("Normalizing segment names...")
    lf = lf.with_columns(
        build_segment_name_expr("segment_name").alias("segment_name_canonical")
    )

    # Filter out meta-segments (where canonical name is _FILTER_OUT_)
    lf = lf.filter(pl.col("segment_name_canonical") != "_FILTER_OUT_")

    # Collect
    context.log.info("Collecting results...")
    df = lf.collect()

    # Join with TAG for labels if available
    if tag_df is not None:
        df = df.join(tag_df, on="concept", how="left")
    else:
        df = df.with_columns(pl.lit(None).alias("label"))

    # Select final columns
    df = df.select([
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
        "segment_type",
        "segment_name",
        "segment_name_canonical",
    ]).sort(["ticker", "fiscal_year", "fiscal_period", "segment_type", "concept"])

    total_rows = len(df)
    context.log.info(f"Collected {total_rows:,} rows")

    # Write output
    output_dir = Path("_data/assets/gold/sec/segments")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clean old files
    for old_file in output_dir.glob("*.parquet"):
        old_file.unlink()

    # Write as single file (segments data is smaller than financials)
    output_path = output_dir / "data.parquet"
    df.write_parquet(output_path)
    context.log.info(f"Wrote {output_path}")

    num_companies = df["ticker"].n_unique()
    segment_types = df["segment_type"].value_counts().to_pandas().to_dict()

    context.add_output_metadata({
        "num_records": total_rows,
        "num_companies": num_companies,
        "segment_types": segment_types,
        "output_path": str(output_path),
    })

    return {
        "total_rows": total_rows,
        "num_companies": num_companies,
    }


@dg.asset(
    key_prefix=["gold", "sec"],
    name="company_profiles",
    group_name=ASSET_GROUP,
    automation_condition=dg.AutomationCondition.all_deps_updated_since_cron(
        "30 * * * *"  # 30 min offset from silver, runs when silver completes
    ),
    ins={
        "sec_filer_registry": dg.AssetIn(key=["bronze", "sec", "sec_filer_registry"]),
    },
    deps=[dg.AssetKey(["silver", "sec", "fsds_company_metadata"])],
    metadata={
        "layer": "gold",
        "visibility": "llm_accessible",
        "questions_answered": [
            "What industry is {company} in?",
            "Is {company} a large-cap company?",
            "Where is {company} headquartered?",
            "When does {company}'s fiscal year end?",
            "Is {company} a well-known seasoned issuer?",
        ],
    },
)
def gold_sec_company_profiles(
    context: dg.AssetExecutionContext,
    sec_filer_registry: pd.DataFrame,
) -> dict:
    """Company profiles with ticker enrichment and human-readable fields.

    Aggregates FSDS company metadata across all quarters and enriches with:
    - ticker from SEC filer registry
    - human-readable filer_category
    - fiscal_year_end_month (1-12)
    """
    context.log.info("Building gold/sec/company_profiles...")

    # Load all silver metadata partitions
    silver_dir = Path("_data/assets/silver/sec/fsds_company_metadata")
    partition_dirs = list(silver_dir.glob("partition=*/data.parquet"))

    if not partition_dirs:
        context.log.warning("No silver company metadata partitions found")
        return {"total_rows": 0}

    context.log.info(f"Loading {len(partition_dirs)} partitions...")
    # Read each partition and normalize schema before concat
    # Numeric columns can be Int64 or Float64 depending on null values per partition
    dfs = []
    for p in partition_dirs:
        df_part = pl.read_parquet(str(p))
        # Cast numeric columns to Float64 to normalize schema across partitions
        cast_exprs = []
        for col in ["fiscal_year_end", "sic_code"]:
            if col in df_part.columns:
                cast_exprs.append(pl.col(col).cast(pl.Float64, strict=False))
        if cast_exprs:
            df_part = df_part.with_columns(cast_exprs)
        dfs.append(df_part)
    metadata = pl.concat(dfs).lazy()

    # Convert registry to Polars
    lf_registry = pl.from_pandas(sec_filer_registry).lazy().select(["cik", "ticker"])

    # Build query - deduplicate by CIK (take most recent)
    lf = (
        metadata
        # Join with registry for ticker
        .join(lf_registry, on="cik", how="left")
        # Filter to companies with tickers
        .filter(pl.col("ticker").is_not_null())
        # Map filer_status to human-readable
        .with_columns([
            pl
            .col("filer_status")
            .replace(FILER_STATUS_MAPPING, default="Unknown")
            .alias("filer_category"),
            # Convert WKSI to boolean
            pl.col("wksi").cast(pl.Boolean).alias("is_wksi"),
            # Extract month from fiscal_year_end (MMDD format)
            # Column is now Float64 after schema normalization, convert to string
            pl
            .col("fiscal_year_end")
            .cast(pl.Int64, strict=False)  # Float64 -> Int64 (removes decimal)
            .cast(pl.Utf8)
            .str.slice(0, 2)
            .cast(pl.Int32)
            .alias("fiscal_year_end_month"),
        ])
    )

    # Collect and deduplicate
    context.log.info("Collecting results...")
    df = lf.collect()

    # Keep most recent per CIK
    df = df.sort("filed_date", descending=True).unique(subset=["cik"], keep="first")

    # Select final columns
    df = df.select([
        "ticker",
        "company_name",
        "cik",
        "sic_code",
        "filer_category",
        "is_wksi",
        "country_business",
        "state_business",
        "country_incorporation",
        "fiscal_year_end_month",
    ]).sort("ticker")

    total_rows = len(df)
    context.log.info(f"Collected {total_rows:,} company profiles")

    # Write output
    output_dir = Path("_data/assets/gold/sec/company_profiles")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "data.parquet"
    df.write_parquet(output_path)
    context.log.info(f"Wrote {output_path}")

    filer_breakdown = df["filer_category"].value_counts().to_pandas().to_dict()

    context.add_output_metadata({
        "num_companies": total_rows,
        "filer_breakdown": filer_breakdown,
        "output_path": str(output_path),
    })

    return {
        "num_companies": total_rows,
    }


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    "bronze_fsds",
    "silver_fsds_segments",
    "silver_fsds_financials",
    "silver_fsds_subsidiaries",
    "silver_fsds_footnotes",
    "silver_fsds_company_metadata",
    "gold_sec_segments",
    "gold_sec_company_profiles",
    # Normalization utilities
    "normalize_segment_name",
    "build_segment_name_expr",
    "SEGMENT_NAME_PATTERNS",
]
