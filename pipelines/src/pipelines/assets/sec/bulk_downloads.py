"""SEC bulk download bronze assets.

This module contains unpartitioned bronze assets that fetch SEC bulk data files:
- company_facts_download: Downloads and caches companyfacts.zip
- company_facts: Parses XBRL financial facts with streaming sharded writes
- submissions_download: Downloads and caches submissions.zip
- submissions: Parses filing metadata by streaming from zip

The download/parse split provides checkpointing - downloads can succeed
independently, and parsing failures don't require re-downloading.

Parsing streams directly from the zip file without extracting to disk,
avoiding the IO bottleneck of creating 19,000+ individual files.

company_facts uses PyArrow ParquetWriter for true streaming writes:
- Row-based sharding (6M rows/shard) for even ~35MB shard sizes
- 10K row batches for minimal memory footprint (~10MB peak)
- Total dataset: ~119M rows across ~20 shards
"""

import json
import zipfile
from collections.abc import Iterator
from pathlib import Path

import dagster as dg
import pandas as pd
import pyarrow as pa

from pipelines.assets.sec.common import ASSET_GROUP
from pipelines.resources import SecEdgarResource
from shared.io.streaming import StreamingParquetSource

# Outlier threshold: 1 quadrillion (10^15)
# Values above this are clearly XBRL scale errors (e.g., CIK 0001164727 Newmont
# reported EntityPublicFloat as $30 quadrillion instead of $30 billion)
VALUE_OUTLIER_THRESHOLD = 1e15

# Write batch size for streaming (rows per write to ParquetWriter)
# Small batches minimize memory usage while being efficient for I/O
WRITE_BATCH_SIZE = 10_000

# Column definitions for DataFrame construction
# Using tuples instead of dicts reduces memory overhead by ~3x
COMPANY_FACTS_COLUMNS = [
    "cik",
    "entity_name",
    "taxonomy",
    "concept",
    "unit",
    "value",
    "start_date",
    "end_date",
    "accession_number",
    "filed_date",
    "form_type",
    "fiscal_year",
    "fiscal_period",
]

# Arrow schema for company_facts parquet files
COMPANY_FACTS_SCHEMA = pa.schema([
    ("cik", pa.string()),
    ("entity_name", pa.string()),
    ("taxonomy", pa.string()),
    ("concept", pa.string()),
    ("unit", pa.string()),
    ("value", pa.float64()),
    ("start_date", pa.string()),  # Keep as string, convert on read
    ("end_date", pa.string()),
    ("accession_number", pa.string()),
    ("filed_date", pa.string()),
    ("form_type", pa.string()),
    ("fiscal_year", pa.int32()),
    ("fiscal_period", pa.string()),
])

SUBMISSIONS_COLUMNS = [
    "cik",
    "entity_name",
    "accession_number",
    "filing_date",
    "report_date",
    "form_type",
    "primary_document",
]


# --- Helper functions for streaming from zip ---


def _create_record_batch(records: list[tuple]) -> pa.RecordBatch:
    """Create Arrow RecordBatch from tuple records.

    Applies transformations:
    - Filters value outliers (> 1 quadrillion)
    - Converts fiscal_year to int (None for invalid)

    Args:
        records: List of tuples matching COMPANY_FACTS_COLUMNS order

    Returns:
        PyArrow RecordBatch ready for streaming write
    """
    if not records:
        return pa.RecordBatch.from_arrays(
            [pa.array([], type=f.type) for f in COMPANY_FACTS_SCHEMA],
            schema=COMPANY_FACTS_SCHEMA,
        )

    # Convert tuples to column arrays
    arrays = []
    for i, field in enumerate(COMPANY_FACTS_SCHEMA):
        col_name = field.name
        col_type = field.type
        values = [r[i] for r in records]

        # Handle value column - filter outliers
        if col_name == "value":
            values = [
                None if v is not None and abs(float(v)) > VALUE_OUTLIER_THRESHOLD else v
                for v in values
            ]

        # Handle fiscal_year - convert to int, None for invalid
        if col_name == "fiscal_year":
            int_values = []
            for v in values:
                if v is None:
                    int_values.append(None)
                elif isinstance(v, int):
                    int_values.append(v)
                else:
                    try:
                        int_values.append(int(v))
                    except (ValueError, TypeError):
                        int_values.append(None)
            values = int_values

        arrays.append(pa.array(values, type=col_type))

    return pa.RecordBatch.from_arrays(arrays, schema=COMPANY_FACTS_SCHEMA)


def _parse_company_facts_bytes(
    filename: str, data: bytes
) -> tuple[list[tuple], str | None]:
    """Parse company facts JSON from raw bytes.

    Returns tuples instead of dicts for ~3x memory efficiency.
    Tuple order matches COMPANY_FACTS_COLUMNS.

    Returns:
        Tuple of (records list, skipped filename or None if successful)
    """
    try:
        content = json.loads(data)
    except json.JSONDecodeError:
        return [], filename

    if "cik" not in content:
        return [], filename

    cik = str(content["cik"]).zfill(10)
    entity_name = content.get("entityName", "")

    records = []
    # Flatten facts structure: taxonomy -> concept -> units -> values
    for taxonomy, concepts in content.get("facts", {}).items():
        for concept, info in concepts.items():
            for unit, values in info.get("units", {}).items():
                for val in values:
                    # Tuple order matches COMPANY_FACTS_COLUMNS
                    records.append((
                        cik,
                        entity_name,
                        taxonomy,
                        concept,
                        unit,
                        val.get("val"),
                        val.get("start"),
                        val.get("end"),
                        val.get("accn"),
                        val.get("filed"),
                        val.get("form"),
                        val.get("fy"),
                        val.get("fp"),
                    ))

    return records, None


def _parse_submissions_bytes(
    filename: str, data: bytes
) -> tuple[list[tuple], str | None]:
    """Parse submissions JSON from raw bytes.

    Returns tuples instead of dicts for ~3x memory efficiency.
    Tuple order matches SUBMISSIONS_COLUMNS.

    Returns:
        Tuple of (records list, skipped filename or None if successful)
    """
    try:
        content = json.loads(data)
    except json.JSONDecodeError:
        return [], filename

    if "cik" not in content:
        return [], filename

    cik = str(content["cik"]).zfill(10)
    entity_name = content.get("name", "")

    records = []
    # Recent filings are stored as parallel arrays
    recent = content.get("filings", {}).get("recent", {})
    if recent:
        accession_numbers = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        report_dates = recent.get("reportDate", [])
        forms = recent.get("form", [])
        primary_docs = recent.get("primaryDocument", [])

        # Zip parallel arrays into records
        for i in range(len(accession_numbers)):
            # Tuple order matches SUBMISSIONS_COLUMNS
            records.append((
                cik,
                entity_name,
                accession_numbers[i] if i < len(accession_numbers) else None,
                filing_dates[i] if i < len(filing_dates) else None,
                report_dates[i] if i < len(report_dates) else None,
                forms[i] if i < len(forms) else None,
                primary_docs[i] if i < len(primary_docs) else None,
            ))

    return records, None


# --- Download checkpoint assets ---


@dg.asset(
    key_prefix=["bronze", "sec"],
    name="company_facts_download",
    group_name=ASSET_GROUP,
    op_tags={"dagster/concurrency_key": "sec_api"},
    retry_policy=dg.RetryPolicy(max_retries=3, delay=60),
    metadata={"layer": "bronze", "source": "sec_edgar", "visibility": "internal"},
)
def bronze_company_facts_download(
    context: dg.AssetExecutionContext,
    sec_edgar: SecEdgarResource,
) -> pd.DataFrame:
    """Download companyfacts.zip and return zip path metadata.

    Downloads ~3 GB of XBRL financial data for all public companies.
    Uses local cache at ~/.cache/sec_edgar/ with 24-hour TTL.
    Does NOT extract - parsing streams directly from the zip file.

    Returns:
        DataFrame with zip metadata (path, file count, download timestamp).
    """
    context.log.info("Downloading companyfacts.zip from SEC...")
    zip_path = sec_edgar.download_company_facts_zip()

    # Count files without extracting
    with zipfile.ZipFile(zip_path, "r") as zf:
        json_files = [
            n for n in zf.namelist() if n.startswith("CIK") and n.endswith(".json")
        ]
        file_count = len(json_files)

    context.add_output_metadata({
        "file_count": file_count,
        "zip_path": str(zip_path),
    })

    return pd.DataFrame({
        "zip_path": [str(zip_path)],
        "file_count": [file_count],
        "downloaded_at": [pd.Timestamp.now()],
    })


@dg.asset(
    key_prefix=["bronze", "sec"],
    name="submissions_download",
    group_name=ASSET_GROUP,
    op_tags={"dagster/concurrency_key": "sec_api"},
    retry_policy=dg.RetryPolicy(max_retries=3, delay=60),
    metadata={"layer": "bronze", "source": "sec_edgar", "visibility": "internal"},
)
def bronze_submissions_download(
    context: dg.AssetExecutionContext,
    sec_edgar: SecEdgarResource,
) -> pd.DataFrame:
    """Download submissions.zip and return zip path metadata.

    Downloads ~1 GB of filing metadata for all public companies.
    Uses local cache at ~/.cache/sec_edgar/ with 24-hour TTL.
    Does NOT extract - parsing streams directly from the zip file.

    Returns:
        DataFrame with zip metadata (path, file count, download timestamp).
    """
    context.log.info("Downloading submissions.zip from SEC...")
    zip_path = sec_edgar.download_submissions_zip()

    # Count files without extracting
    with zipfile.ZipFile(zip_path, "r") as zf:
        json_files = [
            n for n in zf.namelist() if n.startswith("CIK") and n.endswith(".json")
        ]
        file_count = len(json_files)

    context.add_output_metadata({
        "file_count": file_count,
        "zip_path": str(zip_path),
    })

    return pd.DataFrame({
        "zip_path": [str(zip_path)],
        "file_count": [file_count],
        "downloaded_at": [pd.Timestamp.now()],
    })


# --- Parse assets (depend on downloads) ---


def _iter_company_facts_batches(zip_path: Path) -> Iterator[pa.Table]:
    """Iterate over company facts data as PyArrow tables.

    Streams directly from zip without extracting to disk.
    Yields batches of WRITE_BATCH_SIZE rows as PyArrow tables.

    Args:
        zip_path: Path to companyfacts.zip file

    Yields:
        PyArrow tables of parsed company facts data
    """
    pending_records: list[tuple] = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        json_files = [
            n for n in zf.namelist() if n.startswith("CIK") and n.endswith(".json")
        ]

        for filename in json_files:
            data = zf.read(filename)
            records, _ = _parse_company_facts_bytes(filename, data)
            pending_records.extend(records)

            # Yield in WRITE_BATCH_SIZE chunks for streaming
            while len(pending_records) >= WRITE_BATCH_SIZE:
                batch = pending_records[:WRITE_BATCH_SIZE]
                pending_records = pending_records[WRITE_BATCH_SIZE:]
                record_batch = _create_record_batch(batch)
                yield pa.Table.from_batches([record_batch])

    # Yield any remaining records
    if pending_records:
        record_batch = _create_record_batch(pending_records)
        yield pa.Table.from_batches([record_batch])


@dg.asset(
    key_prefix=["silver", "sec"],
    name="company_facts",
    group_name=ASSET_GROUP,
    metadata={"layer": "silver", "source": "sec_edgar", "visibility": "internal"},
    ins={
        "company_facts_download": dg.AssetIn(
            key=["bronze", "sec", "company_facts_download"]
        )
    },
)
def silver_company_facts(
    context: dg.AssetExecutionContext,
    company_facts_download: pd.DataFrame,
) -> StreamingParquetSource:
    """Parse companyfacts JSON with streaming row-based sharded parquet writes.

    Streams directly from zip without extracting to disk. Returns a
    StreamingParquetSource that the IO manager uses to write sharded
    parquet files.

    Uses Hive-standard sharding pattern compatible with:
    - Polars: pl.scan_parquet("path/*.parquet")
    - DuckDB: read_parquet("path/*.parquet")

    Returns:
        StreamingParquetSource wrapping the batch iterator.
        IO manager handles streaming writes to sharded parquet.
    """
    zip_path = Path(company_facts_download["zip_path"].iloc[0])

    # Count files for metadata
    with zipfile.ZipFile(zip_path, "r") as zf:
        json_files = [
            n for n in zf.namelist() if n.startswith("CIK") and n.endswith(".json")
        ]
        total_files = len(json_files)

    context.log.info(
        f"Returning StreamingParquetSource for {total_files} company facts files"
    )
    context.add_output_metadata({
        "num_source_files": total_files,
        "batch_size": WRITE_BATCH_SIZE,
    })

    # Return StreamingParquetSource - IO manager handles the streaming write
    return StreamingParquetSource(
        batch_iterator=lambda: _iter_company_facts_batches(zip_path)
    )


@dg.asset(
    key_prefix=["bronze", "sec"],
    name="submissions",
    group_name=ASSET_GROUP,
    metadata={"layer": "bronze", "source": "sec_edgar", "visibility": "internal"},
    ins={
        "submissions_download": dg.AssetIn(
            key=["bronze", "sec", "submissions_download"]
        )
    },
)
def bronze_submissions(
    context: dg.AssetExecutionContext,
    submissions_download: pd.DataFrame,
) -> pd.DataFrame:
    """Parse submissions JSON files by streaming from zip.

    Depends on submissions_download to ensure zip is cached.
    Streams directly from zip without extracting to disk.
    Skips malformed files (empty JSON objects) with warning.

    Returns:
        DataFrame with columns:
        - cik: Zero-padded CIK (10 chars)
        - entity_name: Company name
        - accession_number: SEC accession number
        - filing_date: Filing date
        - report_date: Report date
        - form_type: Form type (10-K, 10-Q, 8-K, etc.)
        - primary_document: Primary document filename
    """
    zip_path = Path(submissions_download["zip_path"].iloc[0])

    all_records = []
    skipped = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        json_files = [
            n for n in zf.namelist() if n.startswith("CIK") and n.endswith(".json")
        ]
        total_files = len(json_files)

        context.log.info(f"Streaming {total_files} submission JSON files from zip...")

        for i, filename in enumerate(json_files, 1):
            # Log progress every 1000 files
            if i % 1000 == 0:
                pct = (i / total_files) * 100
                context.log.info(f"Processed {i}/{total_files} files ({pct:.1f}%)...")

            data = zf.read(filename)
            records, skipped_file = _parse_submissions_bytes(filename, data)
            all_records.extend(records)
            if skipped_file:
                skipped.append(skipped_file)

    context.log.info(f"Completed parsing {total_files} submission files")

    if skipped:
        context.log.warning(f"Skipped {len(skipped)} malformed files")

    context.log.info("Converting to DataFrame...")
    df = pd.DataFrame(all_records, columns=SUBMISSIONS_COLUMNS)

    # Convert date columns
    df["filing_date"] = pd.to_datetime(df["filing_date"], errors="coerce")
    df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")

    context.add_output_metadata({
        "num_records": len(df),
        "num_companies": df["cik"].nunique(),
        "num_form_types": df["form_type"].nunique(),
        "num_skipped": len(skipped),
        "date_range_start": str(df["filing_date"].min()),
        "date_range_end": str(df["filing_date"].max()),
    })

    return df


__all__ = [
    "bronze_company_facts_download",
    "bronze_submissions_download",
    "silver_company_facts",
    "bronze_submissions",
]
