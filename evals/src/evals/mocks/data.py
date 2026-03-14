"""Mock data assets for DataExplorer integration tests."""

import pandas as pd

from shared.data import AssetMetadata

# GDP - Partitioned economic data
MOCK_GDP_METADATA = AssetMetadata(
    asset_path="gold/economic/growth/gdp",
    is_partitioned=True,
    partition_count=50,
    partitions=["USA", "CHN", "JPN"],
    schema={"date": "datetime64[ns]", "value": "float64"},
    sample_data={"date": "2023-01-01", "value": 25000.0},
    asset_type="dataframe",
)

MOCK_GDP_DATA = pd.DataFrame({
    "date": pd.date_range("2020-01-01", periods=5, freq="QE"),
    "value": [22000.0, 23000.0, 24000.0, 25000.0, 25500.0],
})

# SEC Financials - Non-partitioned corporate data
MOCK_SEC_METADATA = AssetMetadata(
    asset_path="gold/sec/financials",
    is_partitioned=False,
    partition_count=None,
    partitions=[],
    schema={"ticker": "object", "revenue": "float64", "year": "int64"},
    sample_data={"ticker": "AAPL", "revenue": 394328000000.0, "year": 2023},
    asset_type="dataframe",
)

MOCK_SEC_DATA = pd.DataFrame({
    "ticker": ["AAPL", "MSFT", "GOOGL"],
    "revenue": [394328000000.0, 211915000000.0, 307394000000.0],
    "year": [2023, 2023, 2023],
})

# All mock assets in one dict for lookup
MOCK_ASSETS = {
    "gold/economic/growth/gdp": {"metadata": MOCK_GDP_METADATA, "data": MOCK_GDP_DATA},
    "gold/sec/financials": {"metadata": MOCK_SEC_METADATA, "data": MOCK_SEC_DATA},
}
