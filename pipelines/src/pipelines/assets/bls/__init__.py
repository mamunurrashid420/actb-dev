"""BLS (Bureau of Labor Statistics) assets - medallion architecture.

This package contains BLS data assets following medallion layers:

Bronze (raw ingestion):
- api.py: all_series (6 key series via BLS API)
- bulk_downloads.py: Download checkpoints and parsed bulk FTP data
  - cpi_download → cpi (Consumer Price Index)
  - labor_force_download → labor_force (Labor Force Statistics)
  - employment_download → employment (Current Employment Statistics)
  - jolts_download → jolts (Job Openings and Labor Turnover Survey)

The API-based asset fetches a curated set of series via the BLS API,
while bulk downloads fetch complete datasets from BLS FTP for comprehensive
coverage.
"""

# Export shared utilities
# Export API-based assets (curated series)
from pipelines.assets.bls.api import (
    BLS_SERIES_INFO,
    all_series,
)

# Export bulk download assets
from pipelines.assets.bls.bulk_downloads import (
    # Parsed data
    bronze_cpi,
    # Download checkpoints
    bronze_cpi_download,
    bronze_employment,
    bronze_employment_download,
    bronze_jolts,
    bronze_jolts_download,
    bronze_labor_force,
    bronze_labor_force_download,
)
from pipelines.assets.bls.common import (
    ASSET_GROUP,
    BLS_BASE_METADATA,
    DEFAULT_RETRY_POLICY,
    # Polars LazyFrame helpers (preferred)
    add_date_column,
    # Legacy pandas helper
    convert_bls_period_to_date,
    lazy_merge_dimension,
    scan_bls_data_file,
    scan_bls_dimension_file,
    scan_bls_series_file,
)

__all__ = [
    # Constants
    "ASSET_GROUP",
    "BLS_BASE_METADATA",
    "DEFAULT_RETRY_POLICY",
    # API asset metadata
    "BLS_SERIES_INFO",
    # Polars LazyFrame helpers (preferred)
    "add_date_column",
    "lazy_merge_dimension",
    "scan_bls_data_file",
    "scan_bls_dimension_file",
    "scan_bls_series_file",
    # Legacy pandas helper
    "convert_bls_period_to_date",
    # API-based asset (curated series)
    "all_series",
    # Bulk download checkpoint assets
    "bronze_cpi_download",
    "bronze_labor_force_download",
    "bronze_employment_download",
    "bronze_jolts_download",
    # Bulk parsed assets
    "bronze_cpi",
    "bronze_labor_force",
    "bronze_employment",
    "bronze_jolts",
]
