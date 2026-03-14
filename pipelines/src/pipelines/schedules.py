"""Schedule definitions for actBI data pipeline.

This module defines weekly schedules for automated data refresh:
- Source data schedules (FRED, BLS, World Bank, NASA POWER) - fetch from external APIs
- Published layer schedules - transform and publish data for LLM consumption

All schedules start in STOPPED state and must be manually enabled.
"""

import dagster as dg

from pipelines.jobs import (
    agriculture_indicators_job,
    nasa_power_raw_job,
    sec_10k_refresh_job,
    sec_10q_refresh_job,
    sec_13f_refresh_job,
    sec_bulk_downloads_job,
    sec_form4_refresh_job,
    sec_fsds_refresh_job,
    sec_registry_refresh_job,
)

# =============================================================================
# SOURCE DATA SCHEDULES - Fetch data from external APIs
# =============================================================================

weekly_fred_schedule = dg.ScheduleDefinition(
    name="weekly_fred_refresh",
    cron_schedule="0 2 * * 1",  # Monday 2 AM Eastern
    target=dg.AssetSelection.groups("fred"),
    execution_timezone="US/Eastern",
    description="Fetch FRED economic data (GDP, unemployment, CPI) every Monday morning",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)

weekly_bls_schedule = dg.ScheduleDefinition(
    name="weekly_bls_refresh",
    cron_schedule="0 7 * * 5",  # Friday 7 AM Eastern
    target=dg.AssetSelection.groups("bls"),
    execution_timezone="US/Eastern",
    description="Fetch BLS labor market data (job openings, wages, etc.) every Friday morning",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)

weekly_world_bank_schedule = dg.ScheduleDefinition(
    name="weekly_world_bank_refresh",
    cron_schedule="0 2 * * 0",  # Sunday 2 AM Eastern
    target=dg.AssetSelection.groups("world_bank"),
    execution_timezone="US/Eastern",
    description="Fetch World Bank country indicators (20 countries × 6 indicators) every Sunday",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)


# =============================================================================
# PUBLISHED LAYER SCHEDULES - Transform and publish data
# =============================================================================

weekly_combined_indicators_schedule = dg.ScheduleDefinition(
    name="weekly_combined_indicators",
    cron_schedule="0 4 * * 1",  # Monday 4 AM Eastern (after all source data refreshes)
    target=dg.AssetSelection.groups("country_indicators"),
    execution_timezone="US/Eastern",
    description="Refresh country-level economic indicators every Monday (depends on FRED, BLS, and World Bank data)",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)

weekly_fiscal_indicators_schedule = dg.ScheduleDefinition(
    name="weekly_fiscal_indicators",
    cron_schedule="0 4 * * 1",  # Monday 4 AM Eastern (same as country indicators)
    target=dg.AssetSelection.groups("fiscal_indicators"),
    execution_timezone="US/Eastern",
    description="Refresh fiscal indicators (government debt) every Monday - subset of countries with available data",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)

weekly_monetary_indicators_schedule = dg.ScheduleDefinition(
    name="weekly_monetary_indicators",
    cron_schedule="0 4 * * 1",  # Monday 4 AM Eastern (same as country indicators)
    target=dg.AssetSelection.groups("monetary_indicators"),
    execution_timezone="US/Eastern",
    description="Refresh monetary indicators (interest rate) every Monday - subset of countries with available data",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)

# =============================================================================
# AGRICULTURE SCHEDULES - NASA POWER weather data pipeline
# =============================================================================

weekly_nasa_power_schedule = dg.ScheduleDefinition(
    name="weekly_nasa_power_refresh",
    cron_schedule="0 3 * * 1",  # Monday 3 AM Eastern
    job=nasa_power_raw_job,
    execution_timezone="US/Eastern",
    description="Fetch NASA POWER agricultural weather data for all coffee-growing locations every Monday",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)

weekly_agriculture_indicators_schedule = dg.ScheduleDefinition(
    name="weekly_agriculture_refresh",
    cron_schedule="0 5 * * 1",  # Monday 5 AM Eastern (after NASA POWER fetch)
    job=agriculture_indicators_job,
    execution_timezone="US/Eastern",
    description="Refresh published agriculture weather indicators every Monday (after NASA POWER)",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)


# =============================================================================
# ECB SCHEDULES - Exchange rate data
# =============================================================================

weekly_ecb_exchange_rates_schedule = dg.ScheduleDefinition(
    name="weekly_ecb_exchange_rates_refresh",
    cron_schedule="0 3 * * 1",  # Monday 3 AM Eastern
    target=dg.AssetSelection.groups("ecb"),
    execution_timezone="US/Eastern",
    description="Fetch ECB exchange rates weekly (EUR rates for ~30 currencies)",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)


# =============================================================================
# USDA SCHEDULES - Agricultural commodity data (PSD)
# =============================================================================

# Quarterly bulk refresh - catches historical revisions and methodology updates
quarterly_usda_bulk_schedule = dg.ScheduleDefinition(
    name="quarterly_usda_bulk_refresh",
    cron_schedule="0 3 1 1,4,7,10 *",  # 1st of Jan/Apr/Jul/Oct at 3 AM Eastern
    target=dg.AssetSelection.assets(["bronze", "usda", "psd_bulk"]),
    execution_timezone="US/Eastern",
    description="Download USDA PSD bulk data quarterly (catches historical revisions)",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)

# Weekly current refresh - catches monthly WASDE updates
weekly_usda_current_schedule = dg.ScheduleDefinition(
    name="weekly_usda_current_refresh",
    cron_schedule="0 4 * * 1",  # Monday 4 AM Eastern
    target=dg.AssetSelection.assets(["bronze", "usda", "psd_current"]),
    execution_timezone="US/Eastern",
    description="Fetch current-year USDA PSD data weekly via API (rolling window)",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)

# Monthly registry refresh - stable reference data
monthly_usda_registry_schedule = dg.ScheduleDefinition(
    name="monthly_usda_registry_refresh",
    cron_schedule="0 2 1 * *",  # 1st of each month at 2 AM Eastern
    target=dg.AssetSelection.assets(
        ["bronze", "usda", "commodities"],
        ["bronze", "usda", "countries"],
    ),
    execution_timezone="US/Eastern",
    description="Refresh USDA commodity and country registries monthly",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)


# =============================================================================
# BEA SCHEDULES - Bureau of Economic Analysis NIPA data
# =============================================================================

# Quarterly bulk refresh - catches annual revisions (late September) and updated estimates
quarterly_bea_bulk_schedule = dg.ScheduleDefinition(
    name="quarterly_bea_bulk_refresh",
    cron_schedule="0 3 1 1,4,7,10 *",  # 1st of Jan/Apr/Jul/Oct at 3 AM Eastern
    target=dg.AssetSelection.assets(["bronze", "bea", "nipa_bulk"]),
    execution_timezone="US/Eastern",
    description="Download BEA NIPA bulk data quarterly (catches GDP revisions and annual updates)",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)

# Weekly current refresh - catches advance/second/third GDP estimates (~30/60/90 days post-quarter)
weekly_bea_current_schedule = dg.ScheduleDefinition(
    name="weekly_bea_current_refresh",
    cron_schedule="0 5 * * 1",  # Monday 5 AM Eastern
    target=dg.AssetSelection.assets(["bronze", "bea", "nipa_current"]),
    execution_timezone="US/Eastern",
    description="Fetch current-year BEA NIPA data weekly via API (GDP estimates)",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)


# =============================================================================
# SEC SCHEDULES - SEC filing data pipeline (time-based partitions)
# =============================================================================

# Daily Form 4 refresh - high-volume insider trading data
daily_form4_schedule = dg.ScheduleDefinition(
    name="daily_sec_form4_refresh",
    cron_schedule="0 6 * * *",  # Daily 6 AM Eastern
    job=sec_form4_refresh_job,
    execution_timezone="US/Eastern",
    description="Refresh Form 4 insider trading data daily (current month partition)",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)

# Weekly SEC 10-K refresh
weekly_sec_10k_schedule = dg.ScheduleDefinition(
    name="weekly_sec_10k_refresh",
    cron_schedule="0 2 * * 1",  # Monday 2 AM Eastern
    job=sec_10k_refresh_job,
    execution_timezone="US/Eastern",
    description="Refresh 10-K annual reports weekly (current year partition)",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)

# Weekly SEC 10-Q refresh
weekly_sec_10q_schedule = dg.ScheduleDefinition(
    name="weekly_sec_10q_refresh",
    cron_schedule="0 2 * * 1",  # Monday 2 AM Eastern
    job=sec_10q_refresh_job,
    execution_timezone="US/Eastern",
    description="Refresh 10-Q quarterly reports weekly (current quarter partition)",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)

# Weekly SEC 13-F refresh
weekly_sec_13f_schedule = dg.ScheduleDefinition(
    name="weekly_sec_13f_refresh",
    cron_schedule="0 2 * * 1",  # Monday 2 AM Eastern
    job=sec_13f_refresh_job,
    execution_timezone="US/Eastern",
    description="Refresh 13-F institutional holdings weekly (current quarter partition)",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)

# NOTE: daily_sec_gold_refresh schedule removed - SEC gold assets now use
# AutomationCondition.all_deps_updated_since_cron() for automatic triggering

# Weekly SEC registry refresh
weekly_sec_registry_schedule = dg.ScheduleDefinition(
    name="weekly_sec_registry_refresh",
    cron_schedule="0 1 * * 0",  # Sunday 1 AM Eastern
    job=sec_registry_refresh_job,
    execution_timezone="US/Eastern",
    description="Refresh SEC filer registry and filtered registries weekly",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)

# Weekly SEC bulk downloads - submissions.zip + companyfacts.zip
# SEC updates these daily, but weekly refresh is sufficient for most use cases
weekly_sec_bulk_schedule = dg.ScheduleDefinition(
    name="weekly_sec_bulk_refresh",
    cron_schedule="0 2 * * 0",  # Sunday 2 AM Eastern (after registry)
    job=sec_bulk_downloads_job,
    execution_timezone="US/Eastern",
    description="Download SEC bulk data files (submissions.zip + companyfacts.zip) weekly",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)

# Quarterly FSDS refresh - Financial Statement Data Sets with segment data
# Runs on the 15th of Jan/Apr/Jul/Oct (~2 weeks after quarter end when data is available)
quarterly_fsds_schedule = dg.ScheduleDefinition(
    name="quarterly_fsds_refresh",
    cron_schedule="0 3 15 1,4,7,10 *",  # 15th of Jan/Apr/Jul/Oct at 3 AM Eastern
    job=sec_fsds_refresh_job,
    execution_timezone="US/Eastern",
    description="Download SEC Financial Statement Data Sets quarterly (includes segment data)",
    default_status=dg.DefaultScheduleStatus.STOPPED,
)


# =============================================================================
# SCHEDULE REGISTRY
# =============================================================================

ALL_SCHEDULES = [
    # Source data schedules
    weekly_fred_schedule,
    weekly_bls_schedule,
    weekly_world_bank_schedule,
    weekly_nasa_power_schedule,
    # ECB schedules
    weekly_ecb_exchange_rates_schedule,
    # USDA schedules
    quarterly_usda_bulk_schedule,
    weekly_usda_current_schedule,
    monthly_usda_registry_schedule,
    # BEA schedules
    quarterly_bea_bulk_schedule,
    weekly_bea_current_schedule,
    # Published layer schedules
    weekly_combined_indicators_schedule,
    weekly_fiscal_indicators_schedule,
    weekly_monetary_indicators_schedule,
    weekly_agriculture_indicators_schedule,
    # SEC schedules
    daily_form4_schedule,
    weekly_sec_10k_schedule,
    weekly_sec_10q_schedule,
    weekly_sec_13f_schedule,
    weekly_sec_registry_schedule,
    weekly_sec_bulk_schedule,
    quarterly_fsds_schedule,
]
