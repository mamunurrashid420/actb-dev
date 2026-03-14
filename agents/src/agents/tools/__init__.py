"""Tool registry for agents."""

from agents.tools.base import ToolBuilder
from agents.tools.data_discovery import (
    DescribeInput,
    DescribeOutput,
    GetDataInput,
    GetDataOutput,
    SearchInput,
    SearchOutput,
    describe_asset,
    get_data,
    search_assets,
)
from agents.tools.search_tools import (
    SearchTools,
    make_viz_rules_search_tool,
)
from agents.tools.sql_execution import SQLInput, SQLOutput, sql_execution

# All tools available for agents
TOOLS = [sql_execution, search_assets, describe_asset, get_data]

# Discovery tools subset for DataExplorer agent
DISCOVERY_TOOLS = [search_assets, describe_asset, get_data]

__all__ = [
    "TOOLS",
    "DISCOVERY_TOOLS",
    # Base
    "ToolBuilder",
    # SQL
    "sql_execution",
    "SQLInput",
    "SQLOutput",
    # Discovery
    "search_assets",
    "SearchInput",
    "SearchOutput",
    "describe_asset",
    "DescribeInput",
    "DescribeOutput",
    "get_data",
    "GetDataInput",
    "GetDataOutput",
    # Search tools (XLake-backed)
    "SearchTools",
    "make_viz_rules_search_tool",
]
