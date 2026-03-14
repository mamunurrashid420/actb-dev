"""NASA POWER asset checks for data quality validation.

Validates schema and completeness by iterating through each partition.
"""

import dagster as dg
import pandera.pandas as pa

from pipelines.io_managers import FileSystemIOManager
from pipelines.partitions import agricultural_locations
from pipelines.schemas import NasaPowerSchema


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
    - Report any missing or invalid partitions

    Args:
        io_manager: FileSystemIOManager instance for loading partitions
        asset_key: Dagster AssetKey for the asset
        schema: Pandera schema class
        expected_partitions: Set of expected partition keys
        asset_name: Name of the asset (for error messages)

    Returns:
        AssetCheckResult with pass/fail and metadata
    """
    missing_partitions = []
    empty_partitions = []
    invalid_partitions = []
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
            except pa.errors.SchemaErrors:
                invalid_partitions.append(partition_key)

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


@dg.asset_check(
    asset=dg.AssetKey(["bronze", "nasa_power", "daily"]),
    required_resource_keys={"io_manager"},
    blocking=True,
)
def check_nasa_power_daily_completeness(
    context: dg.AssetCheckExecutionContext,
) -> dg.AssetCheckResult:
    """Validate NASA POWER daily data schema and completeness."""
    io_manager = context.resources.io_manager
    expected = set(agricultural_locations.get_partition_keys())

    return _validate_partitioned_asset(
        io_manager=io_manager,
        asset_key=dg.AssetKey(["bronze", "nasa_power", "daily"]),
        schema=NasaPowerSchema,
        expected_partitions=expected,
        asset_name="bronze/nasa_power/daily",
    )


@dg.asset_check(
    asset=dg.AssetKey(["bronze", "nasa_power", "monthly"]),
    required_resource_keys={"io_manager"},
    blocking=True,
)
def check_nasa_power_monthly_completeness(
    context: dg.AssetCheckExecutionContext,
) -> dg.AssetCheckResult:
    """Validate NASA POWER monthly data schema and completeness."""
    io_manager = context.resources.io_manager
    expected = set(agricultural_locations.get_partition_keys())

    return _validate_partitioned_asset(
        io_manager=io_manager,
        asset_key=dg.AssetKey(["bronze", "nasa_power", "monthly"]),
        schema=NasaPowerSchema,
        expected_partitions=expected,
        asset_name="bronze/nasa_power/monthly",
    )


__all__ = [
    "check_nasa_power_daily_completeness",
    "check_nasa_power_monthly_completeness",
]
