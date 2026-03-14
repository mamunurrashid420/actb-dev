"""Asset checks for data quality validation.

This module defines asset checks that validate assets by:
1. Schema validation (using Pandera schemas)
2. Non-empty data validation (partition has data)
3. Completeness checking for partitioned assets (all expected partitions exist)

With blocking=True, failed checks prevent downstream assets from running.

For partitioned assets, checks iterate through each partition individually to:
- Verify partition files exist
- Validate schema per partition
- Report any missing or invalid partitions

Usage:
    Asset checks are automatically discovered and registered in definitions.py.
    They run after asset materialization and report pass/fail status with metadata.
"""

import dagster as dg
import pandas as pd
import pandera.pandas as pa

from pipelines.assets.world_bank import worldbank_country_partitions
from pipelines.checks_nasa import (
    check_nasa_power_daily_completeness,
    check_nasa_power_monthly_completeness,
)
from pipelines.io_managers import FileSystemIOManager
from pipelines.partitions import (
    sec_monthly_partitions,
    sec_quarterly_partitions,
    sec_yearly_partitions,
)
from pipelines.schemas import (
    BlsTimeseriesSchema,
    FredTimeseriesSchema,
    NoaaMonthlySchema,
    WorldBankTimeseriesSchema,
)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _validate_schema(
    df: pd.DataFrame,
    schema: type[pa.DataFrameModel],
    asset_name: str,
) -> dg.AssetCheckResult:
    """Validate schema and non-empty data for a single partition or asset.

    Args:
        df: DataFrame to validate
        schema: Pandera schema class
        asset_name: Name of the asset (for error messages)

    Returns:
        AssetCheckResult with pass/fail and metadata
    """
    if df.empty:
        return dg.AssetCheckResult(
            passed=False,
            metadata={"error": "DataFrame is empty"},
            description=f"{asset_name}: No data found",
        )

    try:
        schema.validate(df, lazy=True)
        return dg.AssetCheckResult(
            passed=True,
            metadata={"num_records": len(df)},
        )
    except pa.errors.SchemaErrors as e:
        failure_cases = e.failure_cases
        return dg.AssetCheckResult(
            passed=False,
            metadata={
                "num_errors": len(failure_cases),
                "error_summary": str(failure_cases.head(10)),
            },
            description=f"{asset_name}: Schema validation failed with {len(failure_cases)} errors",
        )


def _validate_partitioned_asset(
    io_manager: FileSystemIOManager,
    asset_key: dg.AssetKey,
    schema: type[pa.DataFrameModel],
    expected_partitions: set[str],
    asset_name: str,
) -> dg.AssetCheckResult:
    """Validate schema and completeness for a partitioned asset.

    Iterates through each partition individually to:
    - Check if partition file exists
    - Validate schema for each partition
    - Report any missing or invalid partitions with detailed error info

    Args:
        io_manager: FileSystemIOManager instance for loading partitions
        asset_key: Dagster AssetKey for the asset
        schema: Pandera schema class
        expected_partitions: Set of expected partition keys
        asset_name: Name of the asset (for error messages)

    Returns:
        AssetCheckResult with pass/fail and metadata including error details
    """
    missing_partitions = []
    empty_partitions = []
    invalid_partitions = []
    invalid_details = {}  # Store detailed error info per partition
    valid_partitions = []
    total_records = 0

    for partition_key in expected_partitions:
        try:
            df = io_manager.load_asset(asset_key, partition_key)

            if df.empty:
                empty_partitions.append(partition_key)
                continue

            # Validate schema
            try:
                schema.validate(df, lazy=True)
                valid_partitions.append(partition_key)
                total_records += len(df)
            except pa.errors.SchemaErrors as e:
                invalid_partitions.append(partition_key)
                # Capture detailed error info for debugging
                failure_cases = e.failure_cases
                invalid_details[partition_key] = {
                    "num_errors": len(failure_cases),
                    "columns_failed": failure_cases["column"].unique().tolist(),
                    "sample_errors": failure_cases.head(5).to_dict("records"),
                }

        except FileNotFoundError:
            missing_partitions.append(partition_key)

    # Build result
    has_errors = missing_partitions or empty_partitions or invalid_partitions

    if has_errors:
        error_details = []
        if missing_partitions:
            error_details.append(f"missing: {sorted(missing_partitions)}")
        if empty_partitions:
            error_details.append(f"empty: {sorted(empty_partitions)}")
        if invalid_partitions:
            error_details.append(f"invalid schema: {sorted(invalid_partitions)}")

        return dg.AssetCheckResult(
            passed=False,
            metadata={
                "missing_partitions": sorted(missing_partitions),
                "empty_partitions": sorted(empty_partitions),
                "invalid_partitions": sorted(invalid_partitions),
                "invalid_details": invalid_details,  # Detailed error info per partition
                "valid_partitions": sorted(valid_partitions),
                "num_expected": len(expected_partitions),
            },
            description=f"{asset_name}: {'; '.join(error_details)}",
        )

    return dg.AssetCheckResult(
        passed=True,
        metadata={
            "partitions": sorted(valid_partitions),
            "num_partitions": len(valid_partitions),
            "num_records": total_records,
        },
    )


# =============================================================================
# FRED CHECKS (unpartitioned asset - schema validation)
# =============================================================================


@dg.asset_check(asset=dg.AssetKey(["bronze", "fred", "series"]), blocking=True)
def check_fred_timeseries_schema(
    bronze_fred_series: pd.DataFrame,
) -> dg.AssetCheckResult:
    """Validate FRED timeseries data against schema."""
    df = bronze_fred_series

    try:
        FredTimeseriesSchema.validate(df, lazy=True)

        metadata = {
            "num_rows": len(df),
            "series_ids": (
                sorted(df["series_id"].unique().tolist()) if len(df) > 0 else []
            ),
            "date_range": (
                f"{df['date'].min()} to {df['date'].max()}" if len(df) > 0 else None
            ),
        }

        return dg.AssetCheckResult(passed=True, metadata=metadata)

    except pa.errors.SchemaErrors as e:
        failure_cases = e.failure_cases
        return dg.AssetCheckResult(
            passed=False,
            metadata={
                "num_errors": len(failure_cases),
                "error_summary": str(failure_cases.head(10)),
            },
            description=f"Schema validation failed with {len(failure_cases)} errors",
        )


# =============================================================================
# BLS CHECKS (unpartitioned asset - schema validation)
# =============================================================================


@dg.asset_check(asset=dg.AssetKey(["bronze", "bls", "all_series"]), blocking=True)
def check_bls_timeseries_schema(
    bronze_bls_all_series: pd.DataFrame,
) -> dg.AssetCheckResult:
    """Validate BLS timeseries data against schema."""
    df = bronze_bls_all_series

    try:
        BlsTimeseriesSchema.validate(df, lazy=True)

        metadata = {
            "num_rows": len(df),
            "series_ids": (
                sorted(df["series_id"].unique().tolist()) if len(df) > 0 else []
            ),
            "date_range": (
                f"{df['date'].min()} to {df['date'].max()}" if len(df) > 0 else None
            ),
        }

        return dg.AssetCheckResult(passed=True, metadata=metadata)

    except pa.errors.SchemaErrors as e:
        failure_cases = e.failure_cases
        return dg.AssetCheckResult(
            passed=False,
            metadata={
                "num_errors": len(failure_cases),
                "error_summary": str(failure_cases.head(10)),
            },
            description=f"Schema validation failed with {len(failure_cases)} errors",
        )


# =============================================================================
# WORLD BANK CHECKS (partitioned - schema + completeness via iteration)
# =============================================================================


@dg.asset_check(
    asset=dg.AssetKey(["bronze", "world_bank", "timeseries"]),
    required_resource_keys={"io_manager"},
    blocking=True,
)
def check_world_bank_timeseries(
    context: dg.AssetCheckExecutionContext,
) -> dg.AssetCheckResult:
    """Validate World Bank timeseries schema and completeness."""
    io_manager = context.resources.io_manager
    expected = set(worldbank_country_partitions.get_partition_keys())

    return _validate_partitioned_asset(
        io_manager=io_manager,
        asset_key=dg.AssetKey(["bronze", "world_bank", "timeseries"]),
        schema=WorldBankTimeseriesSchema,
        expected_partitions=expected,
        asset_name="bronze/world_bank/timeseries",
    )


# =============================================================================
# NOAA CHECKS (dynamic partitions - schema only)
# =============================================================================


@dg.asset_check(
    asset=dg.AssetKey(["bronze", "noaa", "monthly"]),
    blocking=True,
)
def check_noaa_monthly_schema(
    bronze_noaa_monthly: pd.DataFrame,
) -> dg.AssetCheckResult:
    """Validate NOAA monthly data schema."""
    return _validate_schema(
        df=bronze_noaa_monthly,
        schema=NoaaMonthlySchema,
        asset_name="bronze/noaa/monthly",
    )


@dg.asset_check(
    asset=dg.AssetKey(["bronze", "noaa", "daily"]),
    blocking=True,
)
def check_noaa_daily_schema(
    bronze_noaa_daily: pd.DataFrame,
) -> dg.AssetCheckResult:
    """Validate NOAA daily data schema."""
    return _validate_schema(
        df=bronze_noaa_daily,
        schema=NoaaMonthlySchema,  # Same schema for all NOAA assets
        asset_name="bronze/noaa/daily",
    )


@dg.asset_check(
    asset=dg.AssetKey(["bronze", "noaa", "annual"]),
    blocking=True,
)
def check_noaa_annual_schema(
    bronze_noaa_annual: pd.DataFrame,
) -> dg.AssetCheckResult:
    """Validate NOAA annual data schema."""
    return _validate_schema(
        df=bronze_noaa_annual,
        schema=NoaaMonthlySchema,  # Same schema for all NOAA assets
        asset_name="bronze/noaa/annual",
    )


# =============================================================================
# SEC TIME-BASED CHECKS
# =============================================================================


@dg.asset_check(
    asset=dg.AssetKey(["bronze", "sec", "form_10k_text"]),
    required_resource_keys={"io_manager"},
    blocking=True,
)
def check_sec_form_10k_text(
    context: dg.AssetCheckExecutionContext,
) -> dg.AssetCheckResult:
    """Validate SEC Form 10-K text (yearly partitions) completeness."""
    io_manager = context.resources.io_manager
    expected = set(sec_yearly_partitions.get_partition_keys())

    # For time-based partitions, we just check existence (no schema yet for text)
    missing_partitions = []
    valid_partitions = []

    for partition_key in expected:
        try:
            df = io_manager.load_asset(
                dg.AssetKey(["bronze", "sec", "form_10k_text"]), partition_key
            )
            if not df.empty:
                valid_partitions.append(partition_key)
            else:
                missing_partitions.append(partition_key)
        except FileNotFoundError:
            missing_partitions.append(partition_key)

    if missing_partitions:
        return dg.AssetCheckResult(
            passed=False,
            metadata={
                "missing_years": sorted(missing_partitions),
                "valid_years": sorted(valid_partitions),
            },
            description=f"Missing years: {sorted(missing_partitions)}",
        )

    return dg.AssetCheckResult(
        passed=True,
        metadata={"valid_years": sorted(valid_partitions)},
    )


@dg.asset_check(
    asset=dg.AssetKey(["bronze", "sec", "form_10q_text"]),
    required_resource_keys={"io_manager"},
    blocking=True,
)
def check_sec_form_10q_text(
    context: dg.AssetCheckExecutionContext,
) -> dg.AssetCheckResult:
    """Validate SEC Form 10-Q text (quarterly partitions) completeness."""
    io_manager = context.resources.io_manager
    expected = set(sec_quarterly_partitions.get_partition_keys())

    missing_partitions = []
    valid_partitions = []

    for partition_key in expected:
        try:
            df = io_manager.load_asset(
                dg.AssetKey(["bronze", "sec", "form_10q_text"]), partition_key
            )
            if not df.empty:
                valid_partitions.append(partition_key)
            else:
                missing_partitions.append(partition_key)
        except FileNotFoundError:
            missing_partitions.append(partition_key)

    if missing_partitions:
        return dg.AssetCheckResult(
            passed=False,
            metadata={
                "missing_quarters": sorted(missing_partitions),
                "valid_quarters": sorted(valid_partitions),
            },
            description=f"Missing {len(missing_partitions)} quarters",
        )

    return dg.AssetCheckResult(
        passed=True,
        metadata={"valid_quarters": sorted(valid_partitions)},
    )


@dg.asset_check(
    asset=dg.AssetKey(["bronze", "sec", "form_4"]),
    required_resource_keys={"io_manager"},
    blocking=True,
)
def check_sec_form_4(context: dg.AssetCheckExecutionContext) -> dg.AssetCheckResult:
    """Validate SEC Form 4 (monthly partitions) completeness."""
    io_manager = context.resources.io_manager
    expected = set(sec_monthly_partitions.get_partition_keys())

    missing_partitions = []
    valid_partitions = []

    for partition_key in expected:
        try:
            df = io_manager.load_asset(
                dg.AssetKey(["bronze", "sec", "form_4"]), partition_key
            )
            if not df.empty:
                valid_partitions.append(partition_key)
            else:
                missing_partitions.append(partition_key)
        except FileNotFoundError:
            missing_partitions.append(partition_key)

    if missing_partitions:
        return dg.AssetCheckResult(
            passed=False,
            metadata={
                "missing_months": sorted(missing_partitions),
                "valid_months": sorted(valid_partitions),
            },
            description=f"Missing {len(missing_partitions)} months",
        )

    return dg.AssetCheckResult(
        passed=True,
        metadata={"valid_months": sorted(valid_partitions)},
    )


@dg.asset_check(
    asset=dg.AssetKey(["bronze", "sec", "form_13f"]),
    required_resource_keys={"io_manager"},
    blocking=True,
)
def check_sec_form_13f(context: dg.AssetCheckExecutionContext) -> dg.AssetCheckResult:
    """Validate SEC Form 13-F (quarterly partitions) completeness."""
    io_manager = context.resources.io_manager
    expected = set(sec_quarterly_partitions.get_partition_keys())

    missing_partitions = []
    valid_partitions = []

    for partition_key in expected:
        try:
            df = io_manager.load_asset(
                dg.AssetKey(["bronze", "sec", "form_13f"]), partition_key
            )
            if not df.empty:
                valid_partitions.append(partition_key)
            else:
                missing_partitions.append(partition_key)
        except FileNotFoundError:
            missing_partitions.append(partition_key)

    if missing_partitions:
        return dg.AssetCheckResult(
            passed=False,
            metadata={
                "missing_quarters": sorted(missing_partitions),
                "valid_quarters": sorted(valid_partitions),
            },
            description=f"Missing {len(missing_partitions)} quarters",
        )

    return dg.AssetCheckResult(
        passed=True,
        metadata={"valid_quarters": sorted(valid_partitions)},
    )


# =============================================================================
# SEC GOLD UNPARTITIONED CHECKS
# =============================================================================


@dg.asset_check(
    asset=dg.AssetKey(["gold", "companies", "financials", "annual_reports"]),
    required_resource_keys={"io_manager"},
    blocking=True,
)
def check_annual_reports(context: dg.AssetCheckExecutionContext) -> dg.AssetCheckResult:
    """Validate annual reports (unpartitioned) has data for enabled companies."""
    io_manager = context.resources.io_manager

    try:
        df = io_manager.load_asset(
            dg.AssetKey(["gold", "companies", "financials", "annual_reports"])
        )

        if df.empty:
            return dg.AssetCheckResult(
                passed=False,
                metadata={"error": "No data found"},
                description="Annual reports is empty",
            )

        tickers = (
            sorted(df["ticker"].unique().tolist()) if "ticker" in df.columns else []
        )
        years = (
            sorted(df["fiscal_year"].unique().tolist())
            if "fiscal_year" in df.columns
            else []
        )

        return dg.AssetCheckResult(
            passed=True,
            metadata={
                "num_records": len(df),
                "tickers": tickers,
                "fiscal_years": years,
            },
        )
    except FileNotFoundError:
        return dg.AssetCheckResult(
            passed=False,
            metadata={"error": "Asset not materialized"},
            description="Annual reports asset not found",
        )


@dg.asset_check(
    asset=dg.AssetKey(["gold", "companies", "financials", "quarterly_reports"]),
    required_resource_keys={"io_manager"},
    blocking=True,
)
def check_quarterly_reports(
    context: dg.AssetCheckExecutionContext,
) -> dg.AssetCheckResult:
    """Validate quarterly reports (unpartitioned) has data for enabled companies."""
    io_manager = context.resources.io_manager

    try:
        df = io_manager.load_asset(
            dg.AssetKey(["gold", "companies", "financials", "quarterly_reports"])
        )

        if df.empty:
            return dg.AssetCheckResult(
                passed=False,
                metadata={"error": "No data found"},
                description="Quarterly reports is empty",
            )

        tickers = (
            sorted(df["ticker"].unique().tolist()) if "ticker" in df.columns else []
        )

        return dg.AssetCheckResult(
            passed=True,
            metadata={
                "num_records": len(df),
                "tickers": tickers,
            },
        )
    except FileNotFoundError:
        return dg.AssetCheckResult(
            passed=False,
            metadata={"error": "Asset not materialized"},
            description="Quarterly reports asset not found",
        )


@dg.asset_check(
    asset=dg.AssetKey(["gold", "companies", "insider", "insider_activity"]),
    required_resource_keys={"io_manager"},
    blocking=True,
)
def check_insider_activity(
    context: dg.AssetCheckExecutionContext,
) -> dg.AssetCheckResult:
    """Validate insider activity (unpartitioned) has data for enabled companies."""
    io_manager = context.resources.io_manager

    try:
        df = io_manager.load_asset(
            dg.AssetKey(["gold", "companies", "insider", "insider_activity"])
        )

        if df.empty:
            return dg.AssetCheckResult(
                passed=False,
                metadata={"error": "No data found"},
                description="Insider activity is empty",
            )

        tickers = (
            sorted(df["ticker"].unique().tolist()) if "ticker" in df.columns else []
        )

        return dg.AssetCheckResult(
            passed=True,
            metadata={
                "num_records": len(df),
                "tickers": tickers,
            },
        )
    except FileNotFoundError:
        return dg.AssetCheckResult(
            passed=False,
            metadata={"error": "Asset not materialized"},
            description="Insider activity asset not found",
        )


@dg.asset_check(
    asset=dg.AssetKey(["gold", "institutions", "portfolio", "holdings"]),
    required_resource_keys={"io_manager"},
    blocking=True,
)
def check_portfolio_holdings(
    context: dg.AssetCheckExecutionContext,
) -> dg.AssetCheckResult:
    """Validate portfolio holdings (unpartitioned) has data for enabled institutions."""
    io_manager = context.resources.io_manager

    try:
        df = io_manager.load_asset(
            dg.AssetKey(["gold", "institutions", "portfolio", "holdings"])
        )

        if df.empty:
            return dg.AssetCheckResult(
                passed=False,
                metadata={"error": "No data found"},
                description="Portfolio holdings is empty",
            )

        institutions = (
            sorted(df["institution_name"].unique().tolist())
            if "institution_name" in df.columns
            else []
        )

        return dg.AssetCheckResult(
            passed=True,
            metadata={
                "num_records": len(df),
                "institutions": institutions,
            },
        )
    except FileNotFoundError:
        return dg.AssetCheckResult(
            passed=False,
            metadata={"error": "Asset not materialized"},
            description="Portfolio holdings asset not found",
        )


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # Schema validation checks (unpartitioned)
    "check_fred_timeseries_schema",
    "check_bls_timeseries_schema",
    # Schema + completeness checks (partitioned)
    "check_world_bank_timeseries",
    "check_noaa_monthly_schema",
    "check_noaa_daily_schema",
    "check_noaa_annual_schema",
    # SEC checks (time-based partitions)
    "check_sec_form_10k_text",
    "check_sec_form_10q_text",
    "check_sec_form_4",
    "check_sec_form_13f",
    # Gold SEC checks (unpartitioned)
    "check_annual_reports",
    "check_quarterly_reports",
    "check_insider_activity",
    "check_portfolio_holdings",
    # NASA POWER checks (imported from checks_nasa.py)
    "check_nasa_power_daily_completeness",
    "check_nasa_power_monthly_completeness",
]
