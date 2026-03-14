"""I/O schemas for DataExplorer agent."""

from pydantic import BaseModel, Field


class DataExplorerInput(BaseModel):
    """Input for data exploration queries."""

    query: str = Field(description="Natural language query about data needs")
    focus_areas: list[str] | None = Field(
        default=None,
        description="Optional focus areas: 'economic', 'corporate', 'agricultural'",
    )
    max_results: int = Field(
        default=5, description="Maximum number of assets to return"
    )


class ColumnSchema(BaseModel):
    """Schema for a single column."""

    name: str = Field(description="Column name")
    dtype: str = Field(description="Data type (e.g., 'int64', 'object', 'float64')")
    sample_value: str | None = Field(
        default=None, description="Example value from first row"
    )


class AssetInfo(BaseModel):
    """Information about a discovered asset."""

    asset_path: str = Field(
        description="Full asset path (e.g., 'gold/economic/growth/gdp')"
    )
    description: str = Field(description="Human-readable description of the asset")
    source: str = Field(description="Data source (e.g., 'FRED', 'SEC EDGAR', 'BLS')")
    is_partitioned: bool = Field(description="Whether the asset has partitions")
    partitions: list[str] = Field(
        default_factory=list, description="First 10 partition keys"
    )
    partition_count: int | None = Field(
        default=None, description="Total number of partitions"
    )
    columns_schema: list[ColumnSchema] = Field(
        default_factory=list, description="Column schema"
    )


class DataSample(BaseModel):
    """Sample data from an asset."""

    asset_path: str = Field(description="Asset this sample is from")
    partition: str | None = Field(
        default=None, description="Partition key if applicable"
    )
    columns: list[str] = Field(description="Column names")
    rows: list[dict] = Field(description="Sample rows as list of dictionaries")
    row_count: int = Field(description="Number of rows in sample")
    total_rows: int = Field(description="Total rows in the dataset")


class DataExplorerOutput(BaseModel):
    """Output from data exploration."""

    assets_found: list[AssetInfo] = Field(
        default_factory=list, description="Discovered relevant assets"
    )
    recommended_asset: str | None = Field(
        default=None, description="Best matching asset path for the query"
    )
    sample_data: DataSample | None = Field(
        default=None, description="Sample data from recommended asset"
    )
    rationale: str = Field(description="Explanation of discovery and recommendations")
