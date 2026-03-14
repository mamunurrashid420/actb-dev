"""Tests for search tools.

Tests cover:
- SearchTools class initialization and method behavior
- make_viz_rules_search_tool factory function
- Integration with mocked XLakeClient
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from agents.models import AgentContext
from agents.tools.search_tools import SearchTools, make_viz_rules_search_tool
from xlake.core import TenantContext, TenantIdentity, UserContext
from xlake.models import RetrievalStats, VizDesignRule, VizDesignRuleResponse

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tenant_context() -> TenantContext:
    """Create a test TenantContext."""
    return TenantContext(
        identity=TenantIdentity(
            tenant_id="test-tenant",
            tenant_name="Test Tenant",
            industry="technology",
            region="US",
            timezone="America/New_York",
            locale="en_US",
        ),
    )


@pytest.fixture
def user_context() -> UserContext:
    """Create a test UserContext."""
    return UserContext(
        user_id="test-user",
        tenant_id="test-tenant",
        role="analyst",
    )


@pytest.fixture
def agent_context(
    tenant_context: TenantContext, user_context: UserContext
) -> AgentContext:
    """Create a test AgentContext."""
    return AgentContext(tenant=tenant_context, user=user_context)


@pytest.fixture
def viz_design_rule() -> VizDesignRule:
    """Create a test VizDesignRule."""
    now = datetime.now(UTC)
    return VizDesignRule(
        rule_id="rule_001",
        document_type="action-implementation",
        origin_path="/data-viz-bible/selection/selection-line_chart.md",
        pipeline_stage="selection",
        chart_type="line_chart",
        library=None,
        section_path="Selection: Line Chart > When to Use",
        content="Use line charts for showing trends over time.",
        tags=["selection", "line_chart"],
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def viz_design_rule_response(viz_design_rule: VizDesignRule) -> VizDesignRuleResponse:
    """Create a VizDesignRuleResponse with retrieval stats."""
    return VizDesignRuleResponse(
        rule=viz_design_rule,
        stats=RetrievalStats(rank=1, score=0.95),
    )


@pytest.fixture
def mock_xlake_client(viz_design_rule_response: VizDesignRuleResponse) -> Mock:
    """Create a mock XLakeClient."""
    client = Mock()
    client.visualization.rules.search.return_value = [viz_design_rule_response]
    return client


@pytest.fixture
def mock_runtime(agent_context: AgentContext) -> Mock:
    """Create a mock ToolRuntime with AgentContext."""
    runtime = Mock()
    runtime.context = agent_context
    return runtime


# =============================================================================
# SearchTools Tests
# =============================================================================


class TestSearchTools:
    """Tests for SearchTools class."""

    def test_init(self, mock_xlake_client: Mock) -> None:
        """Test SearchTools initialization."""
        search_tools = SearchTools(mock_xlake_client)
        assert search_tools._client is mock_xlake_client

    def test_search_viz_design_rules(
        self,
        mock_xlake_client: Mock,
        mock_runtime: Mock,
        agent_context: AgentContext,
    ) -> None:
        """Test search_viz_design_rules returns VizDesignRuleResponse list."""
        search_tools = SearchTools(mock_xlake_client)

        results = search_tools.search_viz_design_rules(
            query="line chart trends",
            runtime=mock_runtime,
            pipeline_stage="selection",
            top_k=5,
        )

        # Verify the client was called correctly
        mock_xlake_client.visualization.rules.search.assert_called_once_with(
            "line chart trends",
            pipeline_stage="selection",
            chart_types=None,
            top_k=5,
            tenant=agent_context.tenant,
            user=agent_context.user,
        )

        # Verify results
        assert len(results) == 1
        assert hasattr(results[0], "rule")
        assert hasattr(results[0], "stats")
        assert results[0].stats.rank == 1
        assert results[0].stats.score == 0.95

    def test_search_viz_design_rules_with_chart_types(
        self,
        mock_xlake_client: Mock,
        mock_runtime: Mock,
        agent_context: AgentContext,
    ) -> None:
        """Test search_viz_design_rules with chart_types filter."""
        search_tools = SearchTools(mock_xlake_client)

        search_tools.search_viz_design_rules(
            query="bar chart comparison",
            runtime=mock_runtime,
            chart_types=["bar_chart_vertical", "bar_chart_horizontal"],
        )

        mock_xlake_client.visualization.rules.search.assert_called_once_with(
            "bar chart comparison",
            pipeline_stage=None,
            chart_types=["bar_chart_vertical", "bar_chart_horizontal"],
            top_k=10,
            tenant=agent_context.tenant,
            user=agent_context.user,
        )


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestMakeVizRulesSearchTool:
    """Tests for make_viz_rules_search_tool factory function."""

    def test_creates_tool(self, mock_xlake_client: Mock) -> None:
        """Test that factory creates a LangChain tool."""
        search_tools = SearchTools(mock_xlake_client)
        tool = make_viz_rules_search_tool(search_tools)

        # Tool should be a BaseTool
        assert tool is not None
        assert hasattr(tool, "name")
        assert hasattr(tool, "invoke")

    def test_tool_name(self, mock_xlake_client: Mock) -> None:
        """Test that the tool has the expected name."""
        search_tools = SearchTools(mock_xlake_client)
        tool = make_viz_rules_search_tool(search_tools)

        # Tool name comes from the method name
        assert tool.name == "search_viz_design_rules"

    def test_tool_has_description(self, mock_xlake_client: Mock) -> None:
        """Test that the tool has a description from the docstring."""
        search_tools = SearchTools(mock_xlake_client)
        tool = make_viz_rules_search_tool(search_tools)

        # Description should come from the method docstring
        assert tool.description is not None
        assert "visualization design rules" in tool.description.lower()
