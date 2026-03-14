"""Data discovery tools for agents.

These tools wrap the shared.data library to provide data discovery
capabilities to agents via LangChain tool calling.
"""

import pandas as pd
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from shared.data import AssetMetadata, describe, get, search


class SearchInput(BaseModel):
    """Input for asset search."""

    query: str = Field(
        description="Keyword to search for in asset paths and partitions"
    )


class SearchOutput(BaseModel):
    """Output from asset search."""

    matches: list[str] = Field(description="Matching asset paths")
    match_count: int = Field(description="Total number of matches found")


@tool(args_schema=SearchInput)
def search_assets(query: str) -> dict:
    """Search for assets by keyword across all data sources.

    Searches asset paths and partition names. Use for discovering
    relevant datasets based on topics like 'gdp', 'revenue', 'weather'.

    Returns matching asset paths sorted by relevance.

    Examples:
        - search_assets("gdp") -> finds GDP-related economic data
        - search_assets("sec") -> finds SEC EDGAR corporate filings
        - search_assets("unemployment") -> finds labor market data
    """
    matches = search(query)
    return {"matches": matches[:20], "match_count": len(matches)}


class DescribeInput(BaseModel):
    """Input for asset description."""

    asset_path: str = Field(
        description="Full asset path (e.g., 'gold/economic/growth/gdp', 'gold/sec/financials')"
    )


class DescribeOutput(BaseModel):
    """Output from asset description."""

    asset_path: str = Field(description="The asset path that was described")
    is_partitioned: bool = Field(description="Whether the asset has partitions")
    partition_count: int | None = Field(
        description="Number of partitions, if partitioned"
    )
    partitions: list[str] = Field(
        default_factory=list, description="First 10 partition keys"
    )
    columns_schema: dict[str, str] | None = Field(
        default=None, description="Column name -> data type mapping"
    )
    sample_data: dict | None = Field(default=None, description="First row as example")
    asset_type: str = Field(description="Type of asset: 'dataframe' or 'dict'")


@tool(args_schema=DescribeInput)
def describe_asset(asset_path: str) -> dict:
    """Get detailed metadata about a specific asset.

    Returns schema information, sample data, and partition details.
    Use after search_assets to understand an asset's structure before
    retrieving data.

    For partitioned assets, you'll need to specify a partition key
    when calling get_data.

    Examples:
        - describe_asset("gold/sec/financials") -> schema of financial statements
        - describe_asset("gold/economic/growth/gdp") -> shows partitions like 'USA', 'CHN'
    """
    metadata: AssetMetadata = describe(asset_path)
    return {
        "asset_path": metadata.asset_path,
        "is_partitioned": metadata.is_partitioned,
        "partition_count": metadata.partition_count,
        "partitions": metadata.partitions,
        "columns_schema": metadata.schema,
        "sample_data": metadata.sample_data,
        "asset_type": metadata.asset_type,
    }


class GetDataInput(BaseModel):
    """Input for data retrieval."""

    asset_path: str = Field(description="Full asset path")
    partition: str | None = Field(
        default=None,
        description="Partition key for partitioned assets (required if partitioned)",
    )
    limit: int = Field(default=10, description="Maximum rows to return (max 100)")


class GetDataOutput(BaseModel):
    """Output from data retrieval."""

    columns: list[str] = Field(description="Column names in the data")
    rows: list[dict] = Field(description="Data rows as list of dictionaries")
    row_count: int = Field(description="Number of rows returned")
    total_rows: int = Field(description="Total rows in the dataset")


@tool(args_schema=GetDataInput)
def get_data(asset_path: str, partition: str | None = None, limit: int = 10) -> dict:
    """Retrieve actual data from an asset.

    For partitioned assets, you must provide the partition key.
    Use describe_asset first to see available partitions.

    Returns up to 100 rows of data as a list of dictionaries.

    Examples:
        - get_data("gold/sec/financials") -> sample of SEC financial data
        - get_data("gold/economic/growth/gdp", partition="USA") -> US GDP data
    """
    limit = min(limit, 100)  # Cap at 100 rows

    data = get(asset_path, partition=partition)

    if isinstance(data, pd.DataFrame):
        total_rows = len(data)
        sample = data.head(limit)
        return {
            "columns": list(sample.columns),
            "rows": sample.to_dict(orient="records"),
            "row_count": len(sample),
            "total_rows": total_rows,
        }
    elif isinstance(data, dict):
        # For dict-type assets
        return {
            "columns": list(data.keys()),
            "rows": [data],
            "row_count": 1,
            "total_rows": 1,
        }
    else:
        return {
            "columns": [],
            "rows": [],
            "row_count": 0,
            "total_rows": 0,
        }
