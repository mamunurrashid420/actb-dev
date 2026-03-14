"""BEA (Bureau of Economic Analysis) assets - medallion architecture.

This package contains BEA NIPA (National Income and Product Accounts) assets
following medallion layers:

Bronze (raw data):
- nipa.py: nipa_bulk (quarterly ZIP), nipa_current (weekly API)

Silver (merged + enriched):
- nipa.py: nipa_data (merged with computed metrics)

Data refresh strategy:
- nipa_bulk: Quarterly refresh from bulk ZIP download (catches annual revisions)
- nipa_current: Weekly refresh via API (current year, catches GDP estimates)
- Merge logic: nipa_current wins for overlapping periods (fresher data)

Key NIPA tables included:
- T10105: GDP and Components (Nominal)
- T10106: GDP and Components (Real)
- T10101: GDP Growth Rates
- T20100: Personal Income and Outlays
- T20804: PCE Price Indexes
- T30100: Government Spending
"""

from pipelines.assets.bea.common import ASSET_GROUP
from pipelines.assets.bea.nipa import (
    bronze_nipa_bulk,
    bronze_nipa_current,
    silver_nipa_data,
)

__all__ = [
    # Constants
    "ASSET_GROUP",
    # NIPA data assets
    "bronze_nipa_bulk",
    "bronze_nipa_current",
    "silver_nipa_data",
]
