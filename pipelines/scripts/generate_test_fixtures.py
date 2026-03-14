"""Generate test fixtures from real materialized parquet files.

This script extracts small samples (10 rows) from actual materialized data
and saves them as parquet fixtures for use in unit tests.

Usage:
    uv run python scripts/generate_test_fixtures.py

The script will:
1. Create tests/fixtures/ directory if it doesn't exist
2. Extract 10-row samples from real materialized parquet files
3. Save samples as parquet fixtures with descriptive names
4. Skip sources where files don't exist (with warning)

Generated fixtures:
- tests/fixtures/fred_cpiaucsl.parquet (FRED CPI data)
- tests/fixtures/noaa_nyc_monthly.parquet (NOAA NYC monthly weather)
- tests/fixtures/nasa_power_brazil.parquet (NASA POWER Brazil daily weather)
"""

import pathlib
import sys

import pandas as pd

# Source file paths (relative to data/ directory)
SOURCE_FILES = {
    "fred_cpiaucsl": "_data/assets/fred/raw/timeseries/CPIAUCSL.parquet",
    "noaa_nyc_monthly": "_data/assets/noaa/raw/monthly/USW00094728/USW00094728.parquet",
    "nasa_power_brazil": "_data/assets/nasa/power/raw/daily/brazil_minas_gerais/brazil_minas_gerais.parquet",
}

# Number of rows to sample
SAMPLE_SIZE = 10


def main():
    """Generate test fixtures from real materialized data."""
    # Determine paths
    script_dir = pathlib.Path(__file__).parent
    project_dir = script_dir.parent
    fixtures_dir = project_dir / "tests" / "fixtures"

    print(f"Project directory: {project_dir}")
    print(f"Fixtures directory: {fixtures_dir}")
    print()

    # Create fixtures directory if it doesn't exist
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created fixtures directory: {fixtures_dir}")
    print()

    # Process each source file
    success_count = 0
    skip_count = 0

    for fixture_name, source_path in SOURCE_FILES.items():
        source_file = project_dir / source_path
        fixture_file = fixtures_dir / f"{fixture_name}.parquet"

        print(f"Processing: {fixture_name}")
        print(f"  Source: {source_file}")
        print(f"  Target: {fixture_file}")

        # Check if source file exists
        if not source_file.exists():
            print("  ⚠️  WARNING: Source file does not exist, skipping")
            print()
            skip_count += 1
            continue

        try:
            # Read source data
            df = pd.read_parquet(source_file)
            print(f"  Read {len(df)} rows from source")

            # Take sample (first N rows)
            sample = df.head(SAMPLE_SIZE)
            print(f"  Extracted {len(sample)} rows for fixture")

            # Write fixture
            sample.to_parquet(fixture_file, index=False)
            print(f"  ✓ Wrote fixture to {fixture_file}")
            print()

            success_count += 1

        except Exception as e:
            print(f"  ✗ ERROR: Failed to process {fixture_name}: {e}")
            print()
            continue

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Successfully generated: {success_count} fixtures")
    print(f"Skipped (missing source): {skip_count} fixtures")
    print()

    if skip_count > 0:
        print("To generate skipped fixtures, materialize the source assets first:")
        print(
            '  dg asset materialize --select "bronze/fred/timeseries" --partition "CPIAUCSL"'
        )
        print(
            '  dg asset materialize --select "bronze/noaa/monthly" --partition "USW00094728"'
        )
        print(
            '  dg asset materialize --select "bronze/nasa_power/daily" --partition "brazil_minas_gerais"'
        )
        print()

    if success_count == 0:
        print("ERROR: No fixtures were generated. Materialize source assets first.")
        sys.exit(1)

    print(f"Fixtures saved to: {fixtures_dir}")


if __name__ == "__main__":
    main()
