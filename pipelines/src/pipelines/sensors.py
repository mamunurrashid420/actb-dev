"""Sensor definitions for detecting external data updates.

Sensors poll external data sources and trigger jobs when new data is available.
This is preferable to fixed schedules when release dates are unpredictable.
"""

import datetime as dt

import dagster as dg
import requests

from pipelines.jobs import (
    bea_nipa_bulk_job,
    bls_cpi_refresh_job,
    bls_employment_refresh_job,
    bls_jolts_refresh_job,
    bls_labor_force_refresh_job,
    patents_refresh_job,
    sec_13f_bulk_refresh_job,
    usda_esr_refresh_job,
    usda_gats_census_exports_job,
    usda_gats_census_imports_job,
    usda_gats_census_reexports_job,
    usda_gats_untrade_exports_job,
    usda_gats_untrade_imports_job,
    usda_psd_bulk_job,
)
from pipelines.resources import (
    BLS_DATASETS,
    BLS_FTP_BASE_URL,
    SecEdgarResource,
    UsdaFasResource,
)

# =============================================================================
# PATENTSVIEW SENSOR
# =============================================================================


@dg.sensor(
    job=patents_refresh_job,
    minimum_interval_seconds=86400,  # Check once per day
    default_status=dg.DefaultSensorStatus.STOPPED,
)
def patentsview_update_sensor(context: dg.SensorEvaluationContext):
    """Detect new PatentsView data releases by checking S3 Last-Modified headers.

    PatentsView releases quarterly snapshots with unpredictable timing (2-3 months
    after quarter end). Rather than use a fixed schedule that may miss releases or
    waste downloads, this sensor polls S3 daily to detect when new data appears.

    Uses HTTP HEAD request to check Last-Modified header without downloading data.
    Stores last-seen timestamp in cursor to avoid duplicate runs.
    """
    url = "https://s3.amazonaws.com/data.patentsview.org/download/g_patent.tsv.zip"

    try:
        response = requests.head(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        context.log.warning(f"Failed to check PatentsView S3: {e}")
        return dg.SkipReason("Could not reach PatentsView S3")

    last_modified_str = response.headers.get("Last-Modified")
    if not last_modified_str:
        return dg.SkipReason("No Last-Modified header from S3")

    # Parse RFC 2822 date format (e.g., "Wed, 10 Sep 2025 12:00:00 GMT")
    remote_mtime = dt.datetime.strptime(last_modified_str, "%a, %d %b %Y %H:%M:%S %Z")

    cursor = context.cursor
    if cursor:
        last_seen = dt.datetime.fromisoformat(cursor)
        if remote_mtime <= last_seen:
            return dg.SkipReason(
                f"No new data. Remote: {remote_mtime}, Last seen: {last_seen}"
            )

    # New data available - update cursor and trigger refresh
    context.update_cursor(remote_mtime.isoformat())

    return dg.RunRequest(
        run_key=f"patentsview-{remote_mtime.date()}",
        run_config={},
        tags={"trigger": "sensor", "remote_mtime": str(remote_mtime)},
    )


# =============================================================================
# BLS SENSORS
# =============================================================================

# Primary data files to monitor for each dataset
BLS_DATA_FILES = {
    "cpi": "cu.data.1.AllItems",
    "labor_force": "ln.data.1.AllData",
    "employment": "ce.data.0.AllCESSeries",
    "jolts": "jt.data.1.AllItems",
}

# Map dataset to its job
BLS_JOBS = {
    "cpi": bls_cpi_refresh_job,
    "labor_force": bls_labor_force_refresh_job,
    "employment": bls_employment_refresh_job,
    "jolts": bls_jolts_refresh_job,
}

# User-Agent required by BLS (will be overridden by env var in production)
BLS_SENSOR_USER_AGENT = "actBI Pipeline (sensor check)"


def _check_bls_last_modified(dataset: str) -> dt.datetime | None:
    """Check Last-Modified header for a BLS dataset's primary data file."""
    directory = BLS_DATASETS.get(dataset)
    filename = BLS_DATA_FILES.get(dataset)
    if not directory or not filename:
        return None

    url = f"{BLS_FTP_BASE_URL}/{directory}/{filename}"

    try:
        response = requests.head(
            url,
            headers={"User-Agent": BLS_SENSOR_USER_AGENT},
            timeout=30,
        )
        response.raise_for_status()

        last_modified_str = response.headers.get("Last-Modified")
        if last_modified_str:
            # Parse RFC 2822 format: "Wed, 10 Sep 2025 12:00:00 GMT"
            return dt.datetime.strptime(last_modified_str, "%a, %d %b %Y %H:%M:%S %Z")
    except (requests.RequestException, ValueError):
        pass

    return None


def _create_bls_sensor(dataset: str, description: str):
    """Factory to create BLS update sensors."""

    @dg.sensor(
        name=f"bls_{dataset}_update_sensor",
        job=BLS_JOBS[dataset],
        minimum_interval_seconds=86400,  # Check once per day
        default_status=dg.DefaultSensorStatus.STOPPED,
        description=f"Detect BLS {description} updates by checking FTP Last-Modified headers.",
    )
    def bls_sensor(context: dg.SensorEvaluationContext):
        remote_mtime = _check_bls_last_modified(dataset)

        if remote_mtime is None:
            return dg.SkipReason(f"Could not check BLS {dataset} Last-Modified")

        cursor = context.cursor
        if cursor:
            last_seen = dt.datetime.fromisoformat(cursor)
            if remote_mtime <= last_seen:
                return dg.SkipReason(
                    f"No new {dataset} data. Remote: {remote_mtime}, Last seen: {last_seen}"
                )

        # New data available - update cursor and trigger refresh
        context.update_cursor(remote_mtime.isoformat())

        return dg.RunRequest(
            run_key=f"bls-{dataset}-{remote_mtime.date()}",
            run_config={},
            tags={
                "trigger": "sensor",
                "source": "bls",
                "dataset": dataset,
                "remote_mtime": str(remote_mtime),
            },
        )

    return bls_sensor


# Create sensors for each BLS dataset
bls_cpi_update_sensor = _create_bls_sensor("cpi", "Consumer Price Index")
bls_labor_force_update_sensor = _create_bls_sensor(
    "labor_force", "Labor Force Statistics"
)
bls_employment_update_sensor = _create_bls_sensor("employment", "Employment Statistics")
bls_jolts_update_sensor = _create_bls_sensor("jolts", "JOLTS")


# =============================================================================
# BEA NIPA SENSOR
# =============================================================================

# BEA NIPA flat file URL (use annual file as update indicator)
BEA_NIPA_CHECK_URL = "https://apps.bea.gov/national/Release/TXT/NipaDataA.txt"


@dg.sensor(
    job=bea_nipa_bulk_job,
    minimum_interval_seconds=86400,  # Check once per day
    default_status=dg.DefaultSensorStatus.STOPPED,
    description="Detect BEA NIPA bulk data updates via HTTP Last-Modified header.",
)
def bea_nipa_update_sensor(context: dg.SensorEvaluationContext):
    """Detect BEA NIPA bulk data updates by checking Last-Modified header.

    BEA releases NIPA data monthly with GDP estimates. Rather than use a fixed
    schedule that may miss releases or waste downloads, this sensor polls daily
    to detect when new data appears.

    Uses HTTP HEAD request to check Last-Modified header without downloading data.
    Stores last-seen timestamp in cursor to avoid duplicate runs.
    """
    try:
        response = requests.head(BEA_NIPA_CHECK_URL, timeout=30)
        response.raise_for_status()
    except requests.Timeout:
        context.log.warning(f"Timeout checking {BEA_NIPA_CHECK_URL}")
        return dg.SkipReason("Request timed out")
    except requests.RequestException as e:
        context.log.warning(f"Failed to check BEA NIPA: {e}")
        return dg.SkipReason("Could not reach BEA servers")

    last_modified_str = response.headers.get("Last-Modified")
    if not last_modified_str:
        return dg.SkipReason("No Last-Modified header from BEA")

    # Parse RFC 2822 date format (e.g., "Wed, 10 Sep 2025 12:00:00 GMT")
    remote_mtime = dt.datetime.strptime(last_modified_str, "%a, %d %b %Y %H:%M:%S %Z")

    cursor = context.cursor
    if cursor:
        last_seen = dt.datetime.fromisoformat(cursor)
        if remote_mtime <= last_seen:
            return dg.SkipReason(
                f"No new data. Remote: {remote_mtime}, Last seen: {last_seen}"
            )

    # New data available - update cursor and trigger refresh
    context.update_cursor(remote_mtime.isoformat())

    return dg.RunRequest(
        run_key=f"bea-nipa-{remote_mtime.date()}",
        run_config={},
        tags={"trigger": "sensor", "source": "bea", "remote_mtime": str(remote_mtime)},
    )


# =============================================================================
# USDA PSD SENSOR
# =============================================================================

# USDA PSD bulk CSV URL
USDA_PSD_CHECK_URL = "https://apps.fas.usda.gov/psdonline/downloads/psd_alldata_csv.zip"


@dg.sensor(
    job=usda_psd_bulk_job,
    minimum_interval_seconds=86400,  # Check once per day
    default_status=dg.DefaultSensorStatus.STOPPED,
    description="Detect USDA PSD bulk data updates via HTTP Last-Modified header.",
)
def usda_psd_update_sensor(context: dg.SensorEvaluationContext):
    """Detect USDA PSD bulk data updates by checking Last-Modified header.

    USDA releases PSD updates roughly monthly with WASDE reports, but timing
    varies. This sensor polls daily to detect when new bulk data appears.

    Uses HTTP HEAD request to check Last-Modified header without downloading data.
    Stores last-seen timestamp in cursor to avoid duplicate runs.
    """
    try:
        response = requests.head(USDA_PSD_CHECK_URL, timeout=30)
        response.raise_for_status()
    except requests.Timeout:
        context.log.warning(f"Timeout checking {USDA_PSD_CHECK_URL}")
        return dg.SkipReason("Request timed out")
    except requests.RequestException as e:
        context.log.warning(f"Failed to check USDA PSD: {e}")
        return dg.SkipReason("Could not reach USDA servers")

    last_modified_str = response.headers.get("Last-Modified")
    if not last_modified_str:
        return dg.SkipReason("No Last-Modified header from USDA")

    # Parse RFC 2822 date format (e.g., "Wed, 10 Sep 2025 12:00:00 GMT")
    remote_mtime = dt.datetime.strptime(last_modified_str, "%a, %d %b %Y %H:%M:%S %Z")

    cursor = context.cursor
    if cursor:
        last_seen = dt.datetime.fromisoformat(cursor)
        if remote_mtime <= last_seen:
            return dg.SkipReason(
                f"No new data. Remote: {remote_mtime}, Last seen: {last_seen}"
            )

    # New data available - update cursor and trigger refresh
    context.update_cursor(remote_mtime.isoformat())

    return dg.RunRequest(
        run_key=f"usda-psd-{remote_mtime.date()}",
        run_config={},
        tags={"trigger": "sensor", "source": "usda", "remote_mtime": str(remote_mtime)},
    )


# =============================================================================
# USDA ESR SENSOR
# =============================================================================


@dg.sensor(
    job=usda_esr_refresh_job,
    minimum_interval_seconds=86400,  # Check once per day
    default_status=dg.DefaultSensorStatus.STOPPED,
    description="Detect USDA ESR data updates via dataReleaseDates API endpoint.",
)
def usda_esr_update_sensor(
    context: dg.SensorEvaluationContext,
    usda_fas: UsdaFasResource,
):
    """Detect USDA ESR data updates via the dataReleaseDates API.

    ESR data is published weekly on Thursdays at 8:30 AM ET. This sensor
    checks the dataReleaseDates endpoint to detect when new commodity data
    is available, triggering a refresh only for changed data.

    Uses cursor to track last-seen release dates per commodity to avoid
    duplicate runs and enable incremental updates.
    """
    try:
        release_dates_lf = usda_fas.get_esr_data_release_dates()
        release_dates = release_dates_lf.collect()
    except Exception as e:
        context.log.warning(f"Failed to check ESR data release dates: {e}")
        return dg.SkipReason("Could not reach USDA ESR API")

    if len(release_dates) == 0:
        return dg.SkipReason("No release date data from ESR API")

    # Parse cursor (JSON dict of commodity_code -> last_release_date)
    import json

    cursor_data = {}
    if context.cursor:
        try:
            cursor_data = json.loads(context.cursor)
        except json.JSONDecodeError:
            context.log.warning("Invalid cursor format, treating as fresh start")

    # Find commodities with new data
    changed_commodities = []
    new_cursor_data = {}

    for row in release_dates.iter_rows(named=True):
        commodity_code = row["commodity_code"]
        release_date = row["release_date"]
        new_cursor_data[commodity_code] = release_date

        last_seen = cursor_data.get(commodity_code)
        if last_seen is None or release_date > last_seen:
            changed_commodities.append(commodity_code)

    if not changed_commodities:
        return dg.SkipReason(
            f"No new ESR data. Checked {len(release_dates)} commodities."
        )

    # Update cursor and trigger refresh
    context.update_cursor(json.dumps(new_cursor_data))

    return dg.RunRequest(
        run_key=f"usda-esr-{dt.datetime.now().strftime('%Y%m%d')}",
        run_config={},
        tags={
            "trigger": "sensor",
            "source": "usda_esr",
            "changed_commodities": str(len(changed_commodities)),
        },
    )


# =============================================================================
# USDA GATS SENSORS
# =============================================================================


def _get_census_partition_key() -> str:
    """Calculate the partition key for the most recently released Census data.

    Census trade data is released monthly with ~2 month lag.
    For example, December 2025 release contains October 2025 data.
    """
    today = dt.datetime.now()
    # Go back 2 months for the data month
    data_year = today.year if today.month > 2 else today.year - 1
    data_month = today.month - 2 if today.month > 2 else today.month + 10
    return f"{data_year}-{data_month:02d}"


@dg.sensor(
    job=usda_gats_census_imports_job,
    minimum_interval_seconds=86400,  # Check once per day
    default_status=dg.DefaultSensorStatus.STOPPED,
    description="Detect USDA GATS Census imports updates via dataReleaseDates API.",
)
def usda_gats_census_imports_sensor(
    context: dg.SensorEvaluationContext,
    usda_fas: UsdaFasResource,
):
    """Detect GATS Census import data updates via the dataReleaseDates API.

    Checks the Census imports release dates endpoint and triggers refresh
    when new data is available. Only refreshes the specific month partition
    that was just released (~200 API calls instead of ~2,400).
    """
    import json

    try:
        release_dates_lf = usda_fas.get_gats_census_imports_release_dates()
        release_dates = release_dates_lf.collect()
    except Exception as e:
        context.log.warning(f"Failed to check GATS Census imports release dates: {e}")
        return dg.SkipReason("Could not reach USDA GATS API")

    if len(release_dates) == 0:
        return dg.SkipReason("No release date data from GATS Census imports API")

    # Parse cursor (JSON dict of partner_code -> last_release_date)
    cursor_data = {}
    if context.cursor:
        try:
            cursor_data = json.loads(context.cursor)
        except json.JSONDecodeError:
            context.log.warning("Invalid cursor format, treating as fresh start")

    # Find partners with new data
    changed_partners = []
    new_cursor_data = {}

    for row in release_dates.iter_rows(named=True):
        partner_code = row["partner_code"]
        release_date = row["release_date"]
        new_cursor_data[partner_code] = release_date

        last_seen = cursor_data.get(partner_code)
        if last_seen is None or release_date > last_seen:
            changed_partners.append(partner_code)

    if not changed_partners:
        return dg.SkipReason(
            f"No new GATS Census imports data. Checked {len(release_dates)} partners."
        )

    context.update_cursor(json.dumps(new_cursor_data))

    # Determine which month partition to refresh
    partition_key = _get_census_partition_key()

    return dg.RunRequest(
        partition_key=partition_key,
        run_key=f"gats-census-imports-{partition_key}",
        run_config={},
        tags={
            "trigger": "sensor",
            "source": "usda_gats",
            "partition": partition_key,
            "changed_partners": str(len(changed_partners)),
        },
    )


@dg.sensor(
    job=usda_gats_census_exports_job,
    minimum_interval_seconds=86400,  # Check once per day
    default_status=dg.DefaultSensorStatus.STOPPED,
    description="Detect USDA GATS Census exports updates via dataReleaseDates API.",
)
def usda_gats_census_exports_sensor(
    context: dg.SensorEvaluationContext,
    usda_fas: UsdaFasResource,
):
    """Detect GATS Census export data updates via the dataReleaseDates API.

    Only refreshes the specific month partition that was just released.
    """
    import json

    try:
        release_dates_lf = usda_fas.get_gats_census_exports_release_dates()
        release_dates = release_dates_lf.collect()
    except Exception as e:
        context.log.warning(f"Failed to check GATS Census exports release dates: {e}")
        return dg.SkipReason("Could not reach USDA GATS API")

    if len(release_dates) == 0:
        return dg.SkipReason("No release date data from GATS Census exports API")

    cursor_data = {}
    if context.cursor:
        try:
            cursor_data = json.loads(context.cursor)
        except json.JSONDecodeError:
            context.log.warning("Invalid cursor format, treating as fresh start")

    changed_partners = []
    new_cursor_data = {}

    for row in release_dates.iter_rows(named=True):
        partner_code = row["partner_code"]
        release_date = row["release_date"]
        new_cursor_data[partner_code] = release_date

        last_seen = cursor_data.get(partner_code)
        if last_seen is None or release_date > last_seen:
            changed_partners.append(partner_code)

    if not changed_partners:
        return dg.SkipReason(
            f"No new GATS Census exports data. Checked {len(release_dates)} partners."
        )

    context.update_cursor(json.dumps(new_cursor_data))

    # Determine which month partition to refresh
    partition_key = _get_census_partition_key()

    return dg.RunRequest(
        partition_key=partition_key,
        run_key=f"gats-census-exports-{partition_key}",
        run_config={},
        tags={
            "trigger": "sensor",
            "source": "usda_gats",
            "partition": partition_key,
            "changed_partners": str(len(changed_partners)),
        },
    )


@dg.sensor(
    job=usda_gats_census_reexports_job,
    minimum_interval_seconds=86400,  # Check once per day
    default_status=dg.DefaultSensorStatus.STOPPED,
    description="Detect USDA GATS Census re-exports updates via dataReleaseDates API.",
)
def usda_gats_census_reexports_sensor(
    context: dg.SensorEvaluationContext,
    usda_fas: UsdaFasResource,
):
    """Detect GATS Census re-export data updates via the dataReleaseDates API.

    Only refreshes the specific month partition that was just released.
    """
    import json

    try:
        release_dates_lf = usda_fas.get_gats_census_reexports_release_dates()
        release_dates = release_dates_lf.collect()
    except Exception as e:
        context.log.warning(
            f"Failed to check GATS Census re-exports release dates: {e}"
        )
        return dg.SkipReason("Could not reach USDA GATS API")

    if len(release_dates) == 0:
        return dg.SkipReason("No release date data from GATS Census re-exports API")

    cursor_data = {}
    if context.cursor:
        try:
            cursor_data = json.loads(context.cursor)
        except json.JSONDecodeError:
            context.log.warning("Invalid cursor format, treating as fresh start")

    changed_partners = []
    new_cursor_data = {}

    for row in release_dates.iter_rows(named=True):
        partner_code = row["partner_code"]
        release_date = row["release_date"]
        new_cursor_data[partner_code] = release_date

        last_seen = cursor_data.get(partner_code)
        if last_seen is None or release_date > last_seen:
            changed_partners.append(partner_code)

    if not changed_partners:
        return dg.SkipReason(
            f"No new GATS Census re-exports data. Checked {len(release_dates)} partners."
        )

    context.update_cursor(json.dumps(new_cursor_data))

    # Determine which month partition to refresh
    partition_key = _get_census_partition_key()

    return dg.RunRequest(
        partition_key=partition_key,
        run_key=f"gats-census-reexports-{partition_key}",
        run_config={},
        tags={
            "trigger": "sensor",
            "source": "usda_gats",
            "partition": partition_key,
            "changed_partners": str(len(changed_partners)),
        },
    )


@dg.sensor(
    job=usda_gats_untrade_imports_job,
    minimum_interval_seconds=86400,  # Check once per day
    default_status=dg.DefaultSensorStatus.STOPPED,
    description="Detect USDA GATS UN Trade imports updates via dataReleaseDates API.",
)
def usda_gats_untrade_imports_sensor(
    context: dg.SensorEvaluationContext,
    usda_fas: UsdaFasResource,
):
    """Detect GATS UN Trade import data updates via the dataReleaseDates API."""
    import json

    try:
        release_dates_lf = usda_fas.get_gats_untrade_imports_release_dates()
        release_dates = release_dates_lf.collect()
    except Exception as e:
        context.log.warning(f"Failed to check GATS UN Trade imports release dates: {e}")
        return dg.SkipReason("Could not reach USDA GATS API")

    if len(release_dates) == 0:
        return dg.SkipReason("No release date data from GATS UN Trade imports API")

    cursor_data = {}
    if context.cursor:
        try:
            cursor_data = json.loads(context.cursor)
        except json.JSONDecodeError:
            context.log.warning("Invalid cursor format, treating as fresh start")

    changed_reporters = []
    new_cursor_data = {}

    for row in release_dates.iter_rows(named=True):
        reporter_code = row["reporter_code"]
        release_date = row["release_date"]
        new_cursor_data[reporter_code] = release_date

        last_seen = cursor_data.get(reporter_code)
        if last_seen is None or release_date > last_seen:
            changed_reporters.append(reporter_code)

    if not changed_reporters:
        return dg.SkipReason(
            f"No new GATS UN Trade imports data. Checked {len(release_dates)} reporters."
        )

    context.update_cursor(json.dumps(new_cursor_data))

    return dg.RunRequest(
        run_key=f"gats-untrade-imports-{dt.datetime.now().strftime('%Y%m%d')}",
        run_config={},
        tags={
            "trigger": "sensor",
            "source": "usda_gats",
            "changed_reporters": str(len(changed_reporters)),
        },
    )


@dg.sensor(
    job=usda_gats_untrade_exports_job,
    minimum_interval_seconds=86400,  # Check once per day
    default_status=dg.DefaultSensorStatus.STOPPED,
    description="Detect USDA GATS UN Trade exports updates via dataReleaseDates API.",
)
def usda_gats_untrade_exports_sensor(
    context: dg.SensorEvaluationContext,
    usda_fas: UsdaFasResource,
):
    """Detect GATS UN Trade export data updates via the dataReleaseDates API."""
    import json

    try:
        release_dates_lf = usda_fas.get_gats_untrade_exports_release_dates()
        release_dates = release_dates_lf.collect()
    except Exception as e:
        context.log.warning(f"Failed to check GATS UN Trade exports release dates: {e}")
        return dg.SkipReason("Could not reach USDA GATS API")

    if len(release_dates) == 0:
        return dg.SkipReason("No release date data from GATS UN Trade exports API")

    cursor_data = {}
    if context.cursor:
        try:
            cursor_data = json.loads(context.cursor)
        except json.JSONDecodeError:
            context.log.warning("Invalid cursor format, treating as fresh start")

    changed_reporters = []
    new_cursor_data = {}

    for row in release_dates.iter_rows(named=True):
        reporter_code = row["reporter_code"]
        release_date = row["release_date"]
        new_cursor_data[reporter_code] = release_date

        last_seen = cursor_data.get(reporter_code)
        if last_seen is None or release_date > last_seen:
            changed_reporters.append(reporter_code)

    if not changed_reporters:
        return dg.SkipReason(
            f"No new GATS UN Trade exports data. Checked {len(release_dates)} reporters."
        )

    context.update_cursor(json.dumps(new_cursor_data))

    return dg.RunRequest(
        run_key=f"gats-untrade-exports-{dt.datetime.now().strftime('%Y%m%d')}",
        run_config={},
        tags={
            "trigger": "sensor",
            "source": "usda_gats",
            "changed_reporters": str(len(changed_reporters)),
        },
    )


# =============================================================================
# SEC FORM 13F SENSOR
# =============================================================================


def _get_expected_13f_quarter() -> str:
    """Calculate the expected quarter for Form 13F data based on current date.

    DERA publishes Form 13F data ~45 days after quarter end (13F filing deadline).
    The publication covers filings from the PREVIOUS quarter.

    Returns:
        Quarter string like "2024-Q3" representing the expected available quarter.
    """
    today = dt.datetime.now()
    # Filing deadline is 45 days after quarter end
    # So if we're in mid-Feb, Q4 data should be available
    # If we're in mid-May, Q1 data should be available, etc.

    # Calculate current quarter
    current_quarter = (today.month - 1) // 3 + 1

    # Data is for the previous quarter
    if current_quarter == 1:
        return f"{today.year - 1}-Q4"
    else:
        return f"{today.year}-Q{current_quarter - 1}"


@dg.sensor(
    job=sec_13f_bulk_refresh_job,
    minimum_interval_seconds=86400,  # Check once per day
    default_status=dg.DefaultSensorStatus.STOPPED,
    description="Detect new SEC Form 13F Data Sets via HTTP HEAD.",
)
def sec_form_13f_bulk_update_sensor(
    context: dg.SensorEvaluationContext,
    sec_edgar: SecEdgarResource,
):
    """Detect new Form 13F bulk data by checking if quarterly ZIP exists.

    DERA publishes Form 13F data quarterly after 13F filing deadlines
    (45 days after quarter end). This sensor checks if the expected ZIP file
    for the most recent quarter exists, then triggers refresh for that partition.

    Uses HTTP HEAD to avoid downloading until data is confirmed available.
    """
    import json

    expected_quarter = _get_expected_13f_quarter()

    context.log.info(f"Checking for Form 13F data set: {expected_quarter}")

    is_available, last_modified = sec_edgar.check_form_13f_dataset_available(
        expected_quarter
    )

    if not is_available:
        return dg.SkipReason(f"No Form 13F data set for {expected_quarter} yet")

    # Check cursor to avoid duplicate runs
    cursor = context.cursor
    if cursor:
        try:
            cursor_data = json.loads(cursor)
            if cursor_data.get(expected_quarter) == last_modified:
                return dg.SkipReason(f"{expected_quarter} already processed")
        except json.JSONDecodeError:
            pass  # Invalid cursor, proceed with fresh state

    # Update cursor and trigger refresh for this partition
    new_cursor = json.dumps({expected_quarter: last_modified})
    context.update_cursor(new_cursor)

    context.log.info(
        f"Form 13F data set available for {expected_quarter}, triggering refresh"
    )

    return dg.RunRequest(
        run_key=f"sec-13f-bulk-{expected_quarter}",
        run_config={
            "ops": {
                "bronze_form_13f_bulk": {"config": {"partition_key": expected_quarter}}
            }
        },
        tags={
            "trigger": "sensor",
            "source": "sec_dera",
            "quarter": expected_quarter,
        },
    )


# =============================================================================
# SENSOR REGISTRY
# =============================================================================

ALL_SENSORS = [
    # PatentsView
    patentsview_update_sensor,
    # BLS
    bls_cpi_update_sensor,
    bls_labor_force_update_sensor,
    bls_employment_update_sensor,
    bls_jolts_update_sensor,
    # BEA
    bea_nipa_update_sensor,
    # USDA
    usda_psd_update_sensor,
    usda_esr_update_sensor,
    usda_gats_census_imports_sensor,
    usda_gats_census_exports_sensor,
    usda_gats_census_reexports_sensor,
    usda_gats_untrade_imports_sensor,
    usda_gats_untrade_exports_sensor,
    # SEC
    sec_form_13f_bulk_update_sensor,
]
