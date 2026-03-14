"""ECB Data Portal assets - medallion architecture.

This package contains ECB exchange rate assets following medallion layers:

Bronze (raw data):
- exchange_rates.py: Daily EUR exchange rates from SDMX API

Silver (enriched):
- exchange_rates.py: Exchange rates with computed metrics (MAs, volatility, USD crosses)

Data refresh strategy:
- Weekly refresh (exchange rates are point-in-time, no historical revisions)
"""

from pipelines.assets.ecb.common import ASSET_GROUP, ECB_CURRENCIES
from pipelines.assets.ecb.exchange_rates import (
    bronze_exchange_rates,
    silver_exchange_rates,
)

__all__ = [
    # Constants
    "ASSET_GROUP",
    "ECB_CURRENCIES",
    # Exchange rate assets
    "bronze_exchange_rates",
    "silver_exchange_rates",
]
