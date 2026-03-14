"""Search tools for agents.

These tools provide semantic search capabilities over XLake stores,
including visualization design rules from the CoreContextStore.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain.tools import BaseTool, ToolRuntime, tool

from xlake.models import VizDesignRuleResponse

if TYPE_CHECKING:
    from xlake.api import XLakeClient

from agents.models import AgentContext

# =============================================================================
# SearchTools Class
# =============================================================================


class SearchTools:
    """Search tools initialized with XLakeClient.

    This class holds the XLakeClient instance (app-level dependency) and
    provides search methods that use ToolRuntime for per-request context.

    Example:
        ```python
        from xlake.api import create_xlake_client
        from agents.tools.search_tools import SearchTools, make_viz_rules_search_tool

        client = create_xlake_client()
        search_tools = SearchTools(client)
        viz_search_tool = make_viz_rules_search_tool(search_tools)
        ```
    """

    def __init__(self, client: XLakeClient) -> None:
        """Initialize with XLakeClient.

        Args:
            client: XLakeClient instance for accessing stores.
        """
        self._client = client

    def search_viz_design_rules(
        self,
        query: str,
        runtime: ToolRuntime[AgentContext],
        pipeline_stage: str | None = None,
        chart_types: list[str] | None = None,
        top_k: int = 10,
    ) -> list[VizDesignRuleResponse]:
        """Search for visualization design rules by semantic query.

        Searches the Data Viz Bible knowledge base for relevant rules about
        chart selection, refinement, formatting, and implementation.

        Args:
            query: Natural language query to search for relevant rules.
            runtime: ToolRuntime providing AgentContext with tenant/user.
            pipeline_stage: Filter by stage (selection|refinement|formatting|implementation).
            chart_types: Filter by chart types (e.g., ["line_chart", "bar_chart_vertical"]).
            top_k: Maximum number of results to return.

        Returns:
            List of VizDesignRuleResponse containing rule and retrieval stats.
        """
        ctx = runtime.context
        return self._client.visualization.rules.search(
            query,
            pipeline_stage=pipeline_stage,
            chart_types=chart_types,
            top_k=top_k,
            tenant=ctx.tenant,
            user=ctx.user,
        )


# =============================================================================
# Factory Function
# =============================================================================


def make_viz_rules_search_tool(search_tools: SearchTools) -> BaseTool:
    """Create a LangChain tool for searching viz design rules.

    Args:
        search_tools: SearchTools instance initialized with XLakeClient.

    Returns:
        LangChain tool wrapping search_viz_design_rules method.

    Example:
        ```python
        search_tools = SearchTools(client)
        viz_tool = make_viz_rules_search_tool(search_tools)
        tools = [viz_tool]
        ```
    """
    return tool(search_tools.search_viz_design_rules)
