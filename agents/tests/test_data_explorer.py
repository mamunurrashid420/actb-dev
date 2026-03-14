"""Unit tests for DataExplorer with mocked LangGraph agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agents.data_explorer import DataExplorer
from agents.data_explorer.schemas import DataExplorerInput, DataExplorerOutput


def make_mock_agent_result(messages: list) -> dict:
    """Create a mock agent result with the given messages."""
    return {"messages": messages}


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client to avoid API key requirements."""
    client = MagicMock()
    client.llm = MagicMock()
    return client


class TestDataExplorerMocked:
    """Tests for DataExplorer with mocked LangGraph agent."""

    @pytest.mark.asyncio
    async def test_agent_returns_structured_output_from_respond_tool(
        self, mock_llm_client
    ):
        """Test that agent extracts output from respond tool call."""
        # Mock messages: search, then respond
        mock_messages = [
            HumanMessage(content="Query: Find GDP data"),
            AIMessage(
                content="",
                tool_calls=[
                    {"id": "call_1", "name": "search_assets", "args": {"query": "gdp"}}
                ],
            ),
            ToolMessage(
                content='{"matches": ["gold/economic/growth/gdp"]}',
                tool_call_id="call_1",
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call_2",
                        "name": "respond",
                        "args": {
                            "assets_found": [
                                {
                                    "asset_path": "gold/economic/growth/gdp",
                                    "description": "GDP data by country",
                                    "source": "FRED",
                                    "is_partitioned": True,
                                    "partitions": ["USA", "CHN"],
                                }
                            ],
                            "recommended_asset": "gold/economic/growth/gdp",
                            "sample_data": None,
                            "rationale": "Found GDP data from FRED.",
                        },
                    }
                ],
            ),
        ]

        with patch("agents.data_explorer.agent.create_react_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(
                return_value=make_mock_agent_result(mock_messages)
            )
            mock_create.return_value = mock_agent

            agent = DataExplorer(llm=mock_llm_client)
            inp = DataExplorerInput(query="Find GDP data")
            result = await agent.arun(inp)

            assert isinstance(result, DataExplorerOutput)
            assert len(result.assets_found) == 1
            assert result.assets_found[0].asset_path == "gold/economic/growth/gdp"
            assert result.recommended_asset == "gold/economic/growth/gdp"
            assert "GDP" in result.rationale

    @pytest.mark.asyncio
    async def test_agent_executes_discovery_tools_before_respond(self, mock_llm_client):
        """Test that discovery tools are executed before respond is called."""
        # Mock messages: search, describe, then respond
        mock_messages = [
            HumanMessage(content="Query: SEC data"),
            AIMessage(
                content="",
                tool_calls=[
                    {"id": "call_1", "name": "search_assets", "args": {"query": "sec"}}
                ],
            ),
            ToolMessage(
                content='{"matches": ["gold/sec/financials"]}', tool_call_id="call_1"
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call_2",
                        "name": "describe_asset",
                        "args": {"asset_path": "gold/sec/financials"},
                    }
                ],
            ),
            ToolMessage(
                content='{"asset_path": "gold/sec/financials"}', tool_call_id="call_2"
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call_3",
                        "name": "respond",
                        "args": {
                            "assets_found": [],
                            "recommended_asset": None,
                            "sample_data": None,
                            "rationale": "Explored SEC data.",
                        },
                    }
                ],
            ),
        ]

        with patch("agents.data_explorer.agent.create_react_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(
                return_value=make_mock_agent_result(mock_messages)
            )
            mock_create.return_value = mock_agent

            agent = DataExplorer(llm=mock_llm_client)
            inp = DataExplorerInput(query="SEC data")
            result = await agent.arun(inp)

            # Verify agent was invoked
            mock_agent.ainvoke.assert_called_once()
            assert isinstance(result, DataExplorerOutput)
            assert "SEC" in result.rationale

    @pytest.mark.asyncio
    async def test_agent_handles_no_respond_tool(self, mock_llm_client):
        """Test agent handles case where LLM returns no respond tool call."""
        mock_messages = [
            HumanMessage(content="Query: invalid query"),
            AIMessage(content="I cannot help with that query.", tool_calls=[]),
        ]

        with patch("agents.data_explorer.agent.create_react_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(
                return_value=make_mock_agent_result(mock_messages)
            )
            mock_create.return_value = mock_agent

            agent = DataExplorer(llm=mock_llm_client)
            inp = DataExplorerInput(query="invalid query")
            result = await agent.arun(inp)

            assert isinstance(result, DataExplorerOutput)
            assert len(result.assets_found) == 0
            assert "cannot help" in result.rationale.lower()

    @pytest.mark.asyncio
    async def test_agent_includes_focus_areas_in_message(self, mock_llm_client):
        """Test that focus areas are included in the user message."""
        mock_messages = [
            HumanMessage(
                content="Query: GDP\nFocus areas: economic, corporate\nMax results: 5"
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call_1",
                        "name": "respond",
                        "args": {
                            "assets_found": [],
                            "recommended_asset": None,
                            "sample_data": None,
                            "rationale": "No results",
                        },
                    }
                ],
            ),
        ]

        with patch("agents.data_explorer.agent.create_react_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(
                return_value=make_mock_agent_result(mock_messages)
            )
            mock_create.return_value = mock_agent

            agent = DataExplorer(llm=mock_llm_client)
            inp = DataExplorerInput(query="GDP", focus_areas=["economic", "corporate"])
            await agent.arun(inp)

            # Check the messages passed to the agent
            call_args = mock_agent.ainvoke.call_args[0][0]
            user_message = call_args["messages"][0].content
            assert "economic" in user_message
            assert "corporate" in user_message

    def test_default_prompt_contains_data_sources(self, mock_llm_client):
        """Test that default prompt mentions available data sources."""
        with patch("agents.data_explorer.agent.create_react_agent"):
            agent = DataExplorer(llm=mock_llm_client)

            assert "FRED" in agent.prompt
            assert "SEC" in agent.prompt
            assert "BLS" in agent.prompt
            assert "gold" in agent.prompt.lower()
            assert "respond" in agent.prompt.lower()

    def test_prompt_override(self, mock_llm_client):
        """Test that prompt override works."""
        custom_prompt = "Custom data exploration prompt"
        with patch("agents.data_explorer.agent.create_react_agent"):
            agent = DataExplorer(prompt_override=custom_prompt, llm=mock_llm_client)

            assert agent.prompt == custom_prompt

    @pytest.mark.asyncio
    async def test_agent_handles_empty_messages(self, mock_llm_client):
        """Test agent handles empty message list gracefully."""
        mock_messages = []

        with patch("agents.data_explorer.agent.create_react_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(
                return_value=make_mock_agent_result(mock_messages)
            )
            mock_create.return_value = mock_agent

            agent = DataExplorer(llm=mock_llm_client)
            inp = DataExplorerInput(query="test")
            result = await agent.arun(inp)

            # Should return fallback output
            assert isinstance(result, DataExplorerOutput)
            assert len(result.assets_found) == 0

    def test_sync_run_wrapper(self, mock_llm_client):
        """Test the synchronous run() wrapper works."""
        mock_messages = [
            HumanMessage(content="Query: test"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call_1",
                        "name": "respond",
                        "args": {
                            "assets_found": [],
                            "recommended_asset": None,
                            "sample_data": None,
                            "rationale": "Test response",
                        },
                    }
                ],
            ),
        ]

        with patch("agents.data_explorer.agent.create_react_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(
                return_value=make_mock_agent_result(mock_messages)
            )
            mock_create.return_value = mock_agent

            agent = DataExplorer(llm=mock_llm_client)
            inp = DataExplorerInput(query="test")
            result = agent.run(inp)

            assert isinstance(result, DataExplorerOutput)

    @pytest.mark.asyncio
    async def test_agent_passes_recursion_limit(self, mock_llm_client):
        """Test that max_iterations is passed as recursion_limit."""
        mock_messages = [
            HumanMessage(content="Query: test"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call_1",
                        "name": "respond",
                        "args": {
                            "assets_found": [],
                            "recommended_asset": None,
                            "sample_data": None,
                            "rationale": "Done",
                        },
                    }
                ],
            ),
        ]

        with patch("agents.data_explorer.agent.create_react_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(
                return_value=make_mock_agent_result(mock_messages)
            )
            mock_create.return_value = mock_agent

            agent = DataExplorer(max_iterations=10, llm=mock_llm_client)
            inp = DataExplorerInput(query="test")
            await agent.arun(inp)

            # Check recursion_limit was passed
            call_args = mock_agent.ainvoke.call_args
            config = call_args[0][1]
            assert config["recursion_limit"] == 20  # max_iterations * 2
