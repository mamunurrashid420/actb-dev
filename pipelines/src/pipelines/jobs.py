"""Job definitions for actBI data pipeline.

This module defines asset-based jobs for targeted execution of
related asset groups. Jobs provide:
- Named, reusable execution units
- Manual triggering via UI or CLI
- Partition-specific configurations
- Better separation of concerns (job definition vs. schedule)

Usage:
    # Execute via CLI
    dg job execute agriculture_full_pipeline

    # Execute specific partitions
    dg job execute nasa_power_raw_job --partition brazil_minas_gerais

    # SEC company filings pipeline
    dg job execute sec_company_filings_pipeline --partition AAPL
"""

import dagster as dg

# =============================================================================
# NASA POWER → AGRICULTURE JOBS
# =============================================================================

nasa_power_raw_job = dg.define_asset_job(
    name="nasa_power_raw_refresh",
    description="Fetch raw agricultural weather data from NASA POWER API for all locations",
    selection=dg.AssetSelection.groups("nasa_power"),
    tags={"layer": "raw", "source": "nasa_power"},
)

agriculture_indicators_job = dg.define_asset_job(
    name="agriculture_indicators_refresh",
    description="Refresh published agricultural weather indicators for all locations",
    selection=dg.AssetSelection.groups("agriculture_indicators"),
    tags={"layer": "published", "domain": "agriculture"},
)

agriculture_full_pipeline_job = dg.define_asset_job(
    name="agriculture_full_pipeline",
    description="Execute complete agriculture weather pipeline (NASA POWER raw → published)",
    selection=(
        dg.AssetSelection.groups("nasa_power")
        | dg.AssetSelection.groups("agriculture_indicators")
    ),
    tags={"pipeline": "agriculture"},
)

# Example: Regional subset job (Brazil coffee regions only)
# Note: Use partition selection at runtime rather than redefining partitions_def
# since assets must share the same partition definition
brazil_coffee_job = dg.define_asset_job(
    name="brazil_coffee_refresh",
    description="Refresh weather data for Brazil coffee regions only",
    selection=(
        dg.AssetSelection.groups("nasa_power")
        | dg.AssetSelection.groups("agriculture_indicators")
    ),
    tags={"region": "brazil", "domain": "agriculture"},
)


# =============================================================================
# SEC FILING JOBS
# =============================================================================

# Foundation: Bulk downloads (run first, large downloads)
# Execute: dg job execute sec_bulk_downloads_refresh
sec_bulk_downloads_job = dg.define_asset_job(
    name="sec_bulk_downloads_refresh",
    description="Download SEC bulk data files (submissions.zip + companyfacts.zip)",
    selection=dg.AssetSelection.assets(
        dg.AssetKey(["bronze", "sec", "submissions"]),
        dg.AssetKey(["silver", "sec", "company_facts"]),
    ),
    tags={"layer": "bronze", "source": "sec", "type": "bulk"},
)

# Foundation: Registries (quick, run after bulk downloads or independently)
# Execute: dg job execute sec_registry_refresh
sec_registry_refresh_job = dg.define_asset_job(
    name="sec_registry_refresh",
    description="Refresh SEC filer registry and filtered registries",
    selection=dg.AssetSelection.assets(
        dg.AssetKey(["bronze", "sec", "sec_filer_registry"]),
        dg.AssetKey(["silver", "sec", "company_registry"]),
        dg.AssetKey(["silver", "sec", "institution_registry"]),
    ),
    tags={"layer": "registry", "source": "sec"},
)

# Form 4: Insider trading (monthly partitions)
# Execute: dg job execute sec_form4_refresh --partition "2024-12"
# Backfill: dg job execute sec_form4_refresh (no partition = all months)
sec_form4_refresh_job = dg.define_asset_job(
    name="sec_form4_refresh",
    description="Refresh Form 4 insider trading (bronze → silver)",
    selection=dg.AssetSelection.assets(
        dg.AssetKey(["bronze", "sec", "form_4"]),
        dg.AssetKey(["silver", "sec", "form_4_transactions"]),
    ),
    tags={"layer": "pipeline", "source": "sec", "form": "4"},
)

# 10-K: Annual reports (yearly partitions)
# Execute: dg job execute sec_10k_refresh --partition "2024"
# Backfill: dg job execute sec_10k_refresh (no partition = all years)
sec_10k_refresh_job = dg.define_asset_job(
    name="sec_10k_refresh",
    description="Refresh 10-K annual reports (bronze → silver)",
    selection=dg.AssetSelection.assets(
        dg.AssetKey(["bronze", "sec", "form_10k_text"]),
        dg.AssetKey(["silver", "sec", "form_10k_sections"]),
    ),
    tags={"layer": "pipeline", "source": "sec", "form": "10-K"},
)

# 10-Q: Quarterly reports (quarterly partitions)
# Execute: dg job execute sec_10q_refresh --partition "2024-Q4"
# Backfill: dg job execute sec_10q_refresh (no partition = all quarters)
sec_10q_refresh_job = dg.define_asset_job(
    name="sec_10q_refresh",
    description="Refresh 10-Q quarterly reports (bronze → silver)",
    selection=dg.AssetSelection.assets(
        dg.AssetKey(["bronze", "sec", "form_10q_text"]),
        dg.AssetKey(["silver", "sec", "form_10q_sections"]),
    ),
    tags={"layer": "pipeline", "source": "sec", "form": "10-Q"},
)

# 13-F: Institutional holdings (quarterly partitions)
# Execute: dg job execute sec_13f_refresh --partition "2024-Q4"
# Backfill: dg job execute sec_13f_refresh (no partition = all quarters)
sec_13f_refresh_job = dg.define_asset_job(
    name="sec_13f_refresh",
    description="Refresh 13-F institutional holdings (bronze API → silver)",
    selection=dg.AssetSelection.assets(
        dg.AssetKey(["bronze", "sec", "form_13f"]),
        dg.AssetKey(["silver", "sec", "form_13f_holdings"]),
    ),
    tags={"layer": "pipeline", "source": "sec", "form": "13-F"},
)

# 13-F Bulk: DERA Form 13F Data Sets (quarterly partitions)
# Execute: dg job execute sec_13f_bulk_refresh --partition "2024-Q4"
# Backfill: dg job execute sec_13f_bulk_refresh (no partition = all quarters)
sec_13f_bulk_refresh_job = dg.define_asset_job(
    name="sec_13f_bulk_refresh",
    description="Refresh 13-F holdings from DERA bulk data sets",
    selection=dg.AssetSelection.assets(
        dg.AssetKey(["bronze", "sec", "form_13f_bulk"]),
    ),
    tags={"layer": "bronze", "source": "sec_dera", "form": "13-F"},
)

# Financials: Extract from bulk company facts (unpartitioned)
# Execute: dg job execute sec_financials_refresh
sec_financials_refresh_job = dg.define_asset_job(
    name="sec_financials_refresh",
    description="Extract financials from bulk company facts (10-K + 10-Q)",
    selection=dg.AssetSelection.assets(
        dg.AssetKey(["silver", "sec", "form_10k_financials"]),
        dg.AssetKey(["silver", "sec", "form_10q_financials"]),
    ),
    tags={"layer": "silver", "source": "sec", "type": "financials"},
)

# Gold: All SEC gold layer assets (unpartitioned)
# Execute: dg job execute sec_gold_refresh
sec_gold_refresh_job = dg.define_asset_job(
    name="sec_gold_refresh",
    description="Refresh all SEC gold layer assets",
    selection=dg.AssetSelection.assets(
        dg.AssetKey(["gold", "sec", "financials"]),
        dg.AssetKey(["gold", "sec", "segments"]),
        dg.AssetKey(["gold", "sec", "company_profiles"]),
        dg.AssetKey(["gold", "companies", "financials", "annual_reports"]),
        dg.AssetKey(["gold", "companies", "financials", "quarterly_reports"]),
        dg.AssetKey(["gold", "companies", "insider", "insider_activity"]),
        dg.AssetKey(["gold", "institutions", "portfolio", "holdings"]),
    ),
    tags={"layer": "gold", "source": "sec"},
)

# FSDS: Financial Statement Data Sets with segment data (quarterly partitions)
# Execute: dg job execute sec_fsds_refresh --partition "2024-Q3"
# Backfill: dg job execute sec_fsds_refresh (no partition = all quarters from 2009)
sec_fsds_refresh_job = dg.define_asset_job(
    name="sec_fsds_refresh",
    description="Refresh SEC Financial Statement Data Sets (bronze → silver)",
    selection=dg.AssetSelection.assets(
        dg.AssetKey(["bronze", "sec", "fsds"]),
        dg.AssetKey(["silver", "sec", "fsds_segments"]),
        dg.AssetKey(["silver", "sec", "fsds_financials"]),
        dg.AssetKey(["silver", "sec", "fsds_company_metadata"]),
        dg.AssetKey(["silver", "sec", "fsds_subsidiaries"]),
        dg.AssetKey(["silver", "sec", "fsds_footnotes"]),
    ),
    tags={"layer": "pipeline", "source": "sec", "type": "fsds"},
)


# =============================================================================
# PATENTSVIEW JOBS
# =============================================================================

patents_refresh_job = dg.define_asset_job(
    name="patents_refresh",
    description="Download and parse all PatentsView patent data (~5.4 GB)",
    selection=dg.AssetSelection.groups("patents"),
    tags={"layer": "bronze", "source": "patentsview"},
)


# =============================================================================
# BLS BULK DOWNLOAD JOBS
# =============================================================================

# BLS CPI: Consumer Price Index
# Execute: dg job execute bls_cpi_refresh
bls_cpi_refresh_job = dg.define_asset_job(
    name="bls_cpi_refresh",
    description="Refresh BLS Consumer Price Index (CPI-U) data from FTP",
    selection=dg.AssetSelection.assets(
        dg.AssetKey(["bronze", "bls", "cpi_download"]),
        dg.AssetKey(["bronze", "bls", "cpi"]),
    ),
    tags={"layer": "bronze", "source": "bls", "dataset": "cpi"},
)

# BLS Labor Force: Labor Force Statistics
# Execute: dg job execute bls_labor_force_refresh
bls_labor_force_refresh_job = dg.define_asset_job(
    name="bls_labor_force_refresh",
    description="Refresh BLS Labor Force Statistics from FTP",
    selection=dg.AssetSelection.assets(
        dg.AssetKey(["bronze", "bls", "labor_force_download"]),
        dg.AssetKey(["bronze", "bls", "labor_force"]),
    ),
    tags={"layer": "bronze", "source": "bls", "dataset": "labor_force"},
)

# BLS Employment: Current Employment Statistics (CES)
# Execute: dg job execute bls_employment_refresh
bls_employment_refresh_job = dg.define_asset_job(
    name="bls_employment_refresh",
    description="Refresh BLS Current Employment Statistics (CES) from FTP",
    selection=dg.AssetSelection.assets(
        dg.AssetKey(["bronze", "bls", "employment_download"]),
        dg.AssetKey(["bronze", "bls", "employment"]),
    ),
    tags={"layer": "bronze", "source": "bls", "dataset": "employment"},
)

# BLS JOLTS: Job Openings and Labor Turnover Survey
# Execute: dg job execute bls_jolts_refresh
bls_jolts_refresh_job = dg.define_asset_job(
    name="bls_jolts_refresh",
    description="Refresh BLS JOLTS data from FTP",
    selection=dg.AssetSelection.assets(
        dg.AssetKey(["bronze", "bls", "jolts_download"]),
        dg.AssetKey(["bronze", "bls", "jolts"]),
    ),
    tags={"layer": "bronze", "source": "bls", "dataset": "jolts"},
)

# BLS Full: All bulk datasets (run in sequence)
# Execute: dg job execute bls_bulk_refresh
bls_bulk_refresh_job = dg.define_asset_job(
    name="bls_bulk_refresh",
    description="Refresh all BLS bulk FTP datasets (CPI, Labor Force, Employment, JOLTS)",
    selection=dg.AssetSelection.groups("bls"),
    tags={"layer": "bronze", "source": "bls", "type": "bulk"},
)


# =============================================================================
# BEA NIPA JOBS
# =============================================================================

# BEA NIPA bulk: Download historical NIPA flat files
# Execute: dg job execute bea_nipa_bulk_refresh
bea_nipa_bulk_job = dg.define_asset_job(
    name="bea_nipa_bulk_refresh",
    description="Download BEA NIPA bulk flat files (annual, quarterly, monthly)",
    selection=dg.AssetSelection.assets(dg.AssetKey(["bronze", "bea", "nipa_bulk"])),
    tags={"layer": "bronze", "source": "bea", "type": "bulk"},
)


# =============================================================================
# USDA JOBS
# =============================================================================

# USDA PSD bulk: Download complete PSD CSV data
# Execute: dg job execute usda_psd_bulk_refresh
usda_psd_bulk_job = dg.define_asset_job(
    name="usda_psd_bulk_refresh",
    description="Download USDA PSD bulk CSV data (all commodities and countries)",
    selection=dg.AssetSelection.assets(dg.AssetKey(["bronze", "usda", "psd_bulk"])),
    tags={"layer": "bronze", "source": "usda", "type": "bulk"},
)

# USDA ESR: Weekly export sales data
# Execute: dg job execute usda_esr_refresh
usda_esr_refresh_job = dg.define_asset_job(
    name="usda_esr_refresh",
    description="Fetch USDA ESR weekly export sales data (all commodities)",
    selection=(
        dg.AssetSelection.assets(dg.AssetKey(["bronze", "usda", "esr_regions"]))
        | dg.AssetSelection.assets(dg.AssetKey(["bronze", "usda", "esr_countries"]))
        | dg.AssetSelection.assets(dg.AssetKey(["bronze", "usda", "esr_commodities"]))
        | dg.AssetSelection.assets(dg.AssetKey(["bronze", "usda", "esr_units"]))
        | dg.AssetSelection.assets(dg.AssetKey(["bronze", "usda", "esr_exports"]))
    ),
    tags={"layer": "bronze", "source": "usda", "type": "api"},
)

# USDA GATS: Reference data (quick refresh)
# Execute: dg job execute usda_gats_reference_refresh
usda_gats_reference_job = dg.define_asset_job(
    name="usda_gats_reference_refresh",
    description="Fetch USDA GATS reference data (regions, countries, commodities, etc.)",
    selection=(
        dg.AssetSelection.assets(dg.AssetKey(["bronze", "usda", "gats_regions"]))
        | dg.AssetSelection.assets(dg.AssetKey(["bronze", "usda", "gats_countries"]))
        | dg.AssetSelection.assets(dg.AssetKey(["bronze", "usda", "gats_commodities"]))
        | dg.AssetSelection.assets(
            dg.AssetKey(["bronze", "usda", "gats_hs6_commodities"])
        )
        | dg.AssetSelection.assets(dg.AssetKey(["bronze", "usda", "gats_units"]))
        | dg.AssetSelection.assets(
            dg.AssetKey(["bronze", "usda", "gats_customs_districts"])
        )
    ),
    tags={"layer": "bronze", "source": "usda", "type": "reference"},
)

# USDA GATS Census: US trade data (monthly, rolling 12-month window)
# Execute: dg job execute usda_gats_census_imports_refresh
# Note: Each job takes 2-3 hours due to ~2,400 API calls
usda_gats_census_imports_job = dg.define_asset_job(
    name="usda_gats_census_imports_refresh",
    description="Fetch USDA GATS Census US import data (rolling 12-month window)",
    selection=dg.AssetSelection.assets(
        dg.AssetKey(["bronze", "usda", "gats_census_imports"])
    ),
    tags={"layer": "bronze", "source": "usda", "type": "census"},
)

usda_gats_census_exports_job = dg.define_asset_job(
    name="usda_gats_census_exports_refresh",
    description="Fetch USDA GATS Census US export data (rolling 12-month window)",
    selection=dg.AssetSelection.assets(
        dg.AssetKey(["bronze", "usda", "gats_census_exports"])
    ),
    tags={"layer": "bronze", "source": "usda", "type": "census"},
)

usda_gats_census_reexports_job = dg.define_asset_job(
    name="usda_gats_census_reexports_refresh",
    description="Fetch USDA GATS Census US re-export data (rolling 12-month window)",
    selection=dg.AssetSelection.assets(
        dg.AssetKey(["bronze", "usda", "gats_census_reexports"])
    ),
    tags={"layer": "bronze", "source": "usda", "type": "census"},
)

# USDA GATS UN Trade: Global trade data (annual, top 50 reporters)
# Execute: dg job execute usda_gats_untrade_imports_refresh
# Note: Each job takes ~30 minutes due to ~150 API calls
usda_gats_untrade_imports_job = dg.define_asset_job(
    name="usda_gats_untrade_imports_refresh",
    description="Fetch USDA GATS UN Trade import data (top 50 reporters, 3 years)",
    selection=dg.AssetSelection.assets(
        dg.AssetKey(["bronze", "usda", "gats_untrade_imports"])
    ),
    tags={"layer": "bronze", "source": "usda", "type": "untrade"},
)

usda_gats_untrade_exports_job = dg.define_asset_job(
    name="usda_gats_untrade_exports_refresh",
    description="Fetch USDA GATS UN Trade export data (top 50 reporters, 3 years)",
    selection=dg.AssetSelection.assets(
        dg.AssetKey(["bronze", "usda", "gats_untrade_exports"])
    ),
    tags={"layer": "bronze", "source": "usda", "type": "untrade"},
)

usda_gats_untrade_reexports_job = dg.define_asset_job(
    name="usda_gats_untrade_reexports_refresh",
    description="Fetch USDA GATS UN Trade re-export data (top 50 reporters, 3 years)",
    selection=dg.AssetSelection.assets(
        dg.AssetKey(["bronze", "usda", "gats_untrade_reexports"])
    ),
    tags={"layer": "bronze", "source": "usda", "type": "untrade"},
)


# =============================================================================
# JOB REGISTRY
# =============================================================================

ALL_JOBS = [
    # Agriculture jobs
    nasa_power_raw_job,
    agriculture_indicators_job,
    agriculture_full_pipeline_job,
    brazil_coffee_job,
    # SEC jobs
    sec_bulk_downloads_job,
    sec_registry_refresh_job,
    sec_form4_refresh_job,
    sec_10k_refresh_job,
    sec_10q_refresh_job,
    sec_13f_refresh_job,
    sec_13f_bulk_refresh_job,
    sec_financials_refresh_job,
    sec_gold_refresh_job,
    sec_fsds_refresh_job,
    # BLS jobs
    bls_cpi_refresh_job,
    bls_labor_force_refresh_job,
    bls_employment_refresh_job,
    bls_jolts_refresh_job,
    bls_bulk_refresh_job,
    # BEA jobs
    bea_nipa_bulk_job,
    # USDA jobs
    usda_psd_bulk_job,
    usda_esr_refresh_job,
    usda_gats_reference_job,
    usda_gats_census_imports_job,
    usda_gats_census_exports_job,
    usda_gats_census_reexports_job,
    usda_gats_untrade_imports_job,
    usda_gats_untrade_exports_job,
    usda_gats_untrade_reexports_job,
    # PatentsView jobs
    patents_refresh_job,
]
