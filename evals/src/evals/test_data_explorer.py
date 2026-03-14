"""Integration tests for DataExplorer agent with mock data layer.

These tests use a real LLM with a mocked data layer to test the full agent flow.
Run with: pytest src/agents/evals/ -v -m integration
"""

import pytest

from agents.data_explorer.schemas import DataExplorerInput


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gdp_discovery(data_explorer_agent, mock_data_layer):
    """Test agent discovers GDP data correctly."""
    inp = DataExplorerInput(query="Find GDP data for economic analysis")
    result = await data_explorer_agent.arun(inp)

    assert len(result.assets_found) >= 1
    assert any("gdp" in a.asset_path.lower() for a in result.assets_found)
    assert result.rationale


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sec_financials_discovery(data_explorer_agent, mock_data_layer):
    """Test agent discovers SEC financial data correctly."""
    inp = DataExplorerInput(query="Find company revenue data from SEC filings")
    result = await data_explorer_agent.arun(inp)

    assert len(result.assets_found) >= 1
    assert any("sec" in a.asset_path.lower() for a in result.assets_found)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_no_results_handled(data_explorer_agent, mock_data_layer):
    """Test agent handles empty search gracefully."""
    inp = DataExplorerInput(query="Find xyz123 nonexistent weather satellite data")
    result = await data_explorer_agent.arun(inp)

    # Agent should handle empty results gracefully
    assert result.rationale  # Should explain no results


@pytest.mark.integration
@pytest.mark.asyncio
async def test_partitioned_asset_described(data_explorer_agent, mock_data_layer):
    """Test agent correctly identifies and describes partitioned assets."""
    inp = DataExplorerInput(query="Find GDP data", focus_areas=["economic"])
    result = await data_explorer_agent.arun(inp)

    # Find the GDP asset in results
    gdp_asset = next((a for a in result.assets_found if "gdp" in a.asset_path), None)
    if gdp_asset:
        assert gdp_asset.is_partitioned
        assert len(gdp_asset.partitions) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_recommendation_provided(data_explorer_agent, mock_data_layer):
    """Test agent provides a recommendation when assets are found."""
    inp = DataExplorerInput(query="Find economic growth data")
    result = await data_explorer_agent.arun(inp)

    # When assets are found, agent should make a recommendation
    if result.assets_found:
        assert result.recommended_asset is not None
        assert result.recommended_asset in [a.asset_path for a in result.assets_found]
