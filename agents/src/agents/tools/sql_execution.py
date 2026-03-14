"""SQL execution tool for agents."""

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class SQLInput(BaseModel):
    """Input schema for SQL execution."""

    query: str = Field(description="SQL query to execute")
    params: dict | None = Field(default=None, description="Query parameters")


class SQLOutput(BaseModel):
    """Output schema for SQL execution."""

    columns: list[str]
    rows: list[dict]
    row_count: int


@tool(args_schema=SQLInput)
def sql_execution(query: str, params: dict | None = None) -> SQLOutput:
    """Execute SQL against the data warehouse.

    This is a placeholder - implementation will connect to DuckDB/warehouse.
    """
    raise NotImplementedError("SQL execution not yet implemented")
