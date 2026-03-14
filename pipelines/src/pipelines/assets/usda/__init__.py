"""USDA FAS assets - medallion architecture.

This package contains USDA Foreign Agricultural Service assets:

PSD (Production, Supply, Distribution):
- Bronze: psd_bulk (quarterly CSV), psd_current (weekly API)
- Silver: psd_data (merged with computed metrics)

ESR (Export Sales Reports):
- Bronze: esr_regions, esr_countries, esr_commodities, esr_units, esr_exports
  (partitioned by market year 1990-present)
- Silver: esr_data (aggregated with computed metrics)
- Weekly US export sales data (published Thursdays)

GATS (Global Agricultural Trade System):
- Bronze: gats_regions, gats_countries, gats_commodities, gats_hs6_commodities,
          gats_units, gats_customs_districts (reference data)
- Bronze: gats_census_imports, gats_census_exports, gats_census_reexports
          (US Census monthly trade data)
- Bronze: gats_untrade_imports, gats_untrade_exports, gats_untrade_reexports
          (UN ComTrade annual data)

All assets share 'usda_fas_api' concurrency key to respect 1,000 req/hr rate limit.
"""

from pipelines.assets.usda.common import ASSET_GROUP
from pipelines.assets.usda.esr import (
    bronze_esr_commodities,
    bronze_esr_countries,
    bronze_esr_exports,
    bronze_esr_regions,
    bronze_esr_units,
    silver_esr_data,
)
from pipelines.assets.usda.gats import (
    bronze_gats_census_exports,
    bronze_gats_census_imports,
    bronze_gats_census_reexports,
    bronze_gats_commodities,
    bronze_gats_countries,
    bronze_gats_customs_districts,
    bronze_gats_hs6_commodities,
    bronze_gats_regions,
    bronze_gats_units,
    bronze_gats_untrade_exports,
    bronze_gats_untrade_imports,
    bronze_gats_untrade_reexports,
    silver_gats_census_data,
)
from pipelines.assets.usda.psd import (
    bronze_psd_bulk,
    bronze_psd_current,
    silver_psd_data,
)
from pipelines.assets.usda.registry import (
    bronze_commodities,
    bronze_countries,
)

__all__ = [
    # Constants
    "ASSET_GROUP",
    # PSD Registry assets
    "bronze_commodities",
    "bronze_countries",
    # PSD data assets
    "bronze_psd_bulk",
    "bronze_psd_current",
    "silver_psd_data",
    # ESR assets
    "bronze_esr_regions",
    "bronze_esr_countries",
    "bronze_esr_commodities",
    "bronze_esr_units",
    "bronze_esr_exports",
    "silver_esr_data",
    # GATS Reference assets
    "bronze_gats_regions",
    "bronze_gats_countries",
    "bronze_gats_commodities",
    "bronze_gats_hs6_commodities",
    "bronze_gats_units",
    "bronze_gats_customs_districts",
    # GATS Census trade data (bronze)
    "bronze_gats_census_imports",
    "bronze_gats_census_exports",
    "bronze_gats_census_reexports",
    # GATS Census trade data (silver)
    "silver_gats_census_data",
    # GATS UN Trade data
    "bronze_gats_untrade_imports",
    "bronze_gats_untrade_exports",
    "bronze_gats_untrade_reexports",
]
