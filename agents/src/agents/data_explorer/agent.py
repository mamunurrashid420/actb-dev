"""DataExplorer agent implementation."""

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from agents.abstract_agent import BaseAgent
from agents.data_explorer.schemas import DataExplorerInput, DataExplorerOutput
from agents.llm import LLMClient
from agents.tools import DISCOVERY_TOOLS

DEFAULT_PROMPT = """You are a data exploration expert for ActBI's data platform.

Your role is to help users discover and understand available datasets.

## Available Data Sources

The platform provides analysis-ready data from 11+ external sources:

- **Economic**: FRED (GDP, unemployment), BLS (CPI, labor), BEA (NIPA), World Bank, ECB
- **Corporate**: SEC EDGAR (financials, segments, Form 4, 13-F)
- **Agricultural**: USDA (production), NASA POWER (weather)
- **Other**: PatentsView, NOAA

All data is accessible via the gold/ asset path prefix.

## Your Process

1. **Search**: Use search_assets to find relevant datasets by keyword
2. **Describe**: Use describe_asset to understand schema and structure
3. **Retrieve**: Use get_data to fetch sample data when helpful
4. **Respond**: When done exploring, call the respond tool with your findings

## Guidelines

- Start with search_assets to discover relevant assets
- Focus on gold/ assets (analysis-ready data)
- Use describe_asset to understand partitioned vs non-partitioned assets
- For partitioned assets, partition key is required for get_data
- Always finish by calling the respond tool with structured results"""


# Response tool - when called, terminates the agent loop
@tool(args_schema=DataExplorerOutput)
def respond(
    assets_found: list,
    recommended_asset: str | None,
    sample_data: dict | None,
    rationale: str,
) -> str:
    """Call this tool to provide your final response with discovered assets.

    Use this after exploring with search_assets, describe_asset, and get_data.
    Provide a complete summary of relevant assets found and your recommendation.
    """
    return "Response recorded"


# All tools including the response tool
ALL_TOOLS = DISCOVERY_TOOLS + [respond]


class DataExplorer(BaseAgent[DataExplorerInput, DataExplorerOutput]):
    """Explores and retrieves data from external sources.

    Uses LangGraph's create_react_agent for the ReAct loop,
    with a respond tool that terminates execution with structured output.
    """

    def __init__(
        self,
        prompt_override: str | None = None,
        model: str | None = None,
        llm: LLMClient | None = None,
        max_iterations: int = 5,
    ):
        super().__init__(prompt_override=prompt_override, model=model, llm=llm)
        self.max_iterations = max_iterations

        # Create LangGraph react agent with all tools
        self._agent = create_react_agent(
            self.llm_client.llm,
            tools=ALL_TOOLS,
            prompt=self.prompt,
        )

    def default_prompt(self) -> str:
        return DEFAULT_PROMPT

    async def arun(self, input: DataExplorerInput) -> DataExplorerOutput:
        """Run the data exploration agent."""
        # Build user message
        user_message = f"Query: {input.query}"
        if input.focus_areas:
            user_message += f"\nFocus areas: {', '.join(input.focus_areas)}"
        user_message += f"\nMax results: {input.max_results}"

        # Run the agent
        result = await self._agent.ainvoke(
            {"messages": [HumanMessage(content=user_message)]},
            {"recursion_limit": self.max_iterations * 2},
        )

        # Extract output from respond tool call
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc["name"] == "respond":
                        return DataExplorerOutput(**tc["args"])

        # Fallback: no respond tool was called
        messages = result.get("messages", [])
        if messages:
            last_msg = messages[-1]
            rationale = getattr(last_msg, "content", None) or "No response generated"
        else:
            rationale = "No response generated"

        return DataExplorerOutput(assets_found=[], rationale=rationale)
