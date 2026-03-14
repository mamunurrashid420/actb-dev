"""Tests for VisualizationClient and its sub-clients."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import Mock

import pytest

from xlake.api.visualization_client import (
    ChartsVisualizationClient,
    DashboardsVisualizationClient,
    RulesVisualizationClient,
    StacksVisualizationClient,
    VisualizationClient,
)
from xlake.core import (
    Permissions,
    Preferences,
    TenantContext,
    TenantIdentity,
    UserContext,
)
from xlake.models import RetrievalStats, VizDesignRule, VizDesignRuleResponse

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tenant_context() -> TenantContext:
    """Create a test TenantContext."""
    return TenantContext(
        identity=TenantIdentity(
            tenant_id="test-tenant-001",
            tenant_name="Test Tenant",
            industry="technology",
            region="EU",
            timezone="Europe/Rome",
            locale="en_US",
        ),
    )


@pytest.fixture
def user_context() -> UserContext:
    """Create a test UserContext with full permissions."""
    return UserContext(
        user_id="test-user-001",
        tenant_id="test-tenant-001",
        role="admin",
        permissions=Permissions(
            can_view_fields=["*"],
            can_view_tables=["*"],
            can_view_kpis=["*"],
            can_view_dashboards=["*"],
            can_run_queries=True,
            can_modify_schema=True,
        ),
        preferences=Preferences(
            units="EUR",
            timezone="Europe/Rome",
            verbosity="concise",
        ),
    )


@pytest.fixture
def mock_chart() -> Mock:
    """Create a mock Chart protobuf object."""
    chart = Mock()
    chart.id = "chart_001"
    chart.title = "Revenue Chart"
    chart.chart_type = "bar_chart_vertical"
    chart.version = 1
    chart.CopyFrom = Mock()
    return chart


@pytest.fixture
def mock_dashboard() -> Mock:
    """Create a mock Dashboard protobuf object."""
    dashboard = Mock()
    dashboard.id = "dashboard_001"
    dashboard.title = "Sales Dashboard"
    dashboard.description = "Sales overview dashboard"
    dashboard.CopyFrom = Mock()
    return dashboard


@pytest.fixture
def mock_chart_stack() -> Mock:
    """Create a mock ChartStack protobuf object."""
    stack = Mock()
    stack.id = "stack_001"
    stack.title = "Revenue Stack"
    return stack


@pytest.fixture
def mock_viz_design_rule() -> Mock:
    """Create a mock VizDesignRule object."""
    rule = Mock()
    rule.rule_id = "rule_001"
    rule.document_type = "action-implementation"
    rule.origin_path = "/data-viz-bible/selection/selection-line_chart.md"
    rule.pipeline_stage = "selection"
    rule.chart_type = "line_chart"
    rule.section_path = "Selection: Line Chart > When to Use"
    rule.content = "[Line Chart - Selection - When to Use]\nShows trends..."
    rule.tags = ["selection", "line_chart"]
    return rule


@pytest.fixture
def mock_blueprint_rule() -> Mock:
    """Create a mock VizDesignRule for a blueprint document."""
    rule = Mock()
    rule.rule_id = "blueprint_selection"
    rule.document_type = "action-interface"
    rule.origin_path = "/data-viz-bible/selection/selection.md"
    rule.pipeline_stage = "selection"
    rule.chart_type = None
    rule.section_path = "Selection"
    rule.content = "The Selection action determines which chart type..."
    rule.tags = ["selection", "decision-tree"]
    return rule


@pytest.fixture
def mock_chart_store(
    mock_chart: Mock, mock_dashboard: Mock, mock_chart_stack: Mock
) -> Mock:
    """Create a mock CustomerChartStore."""
    store = Mock()
    store.upsert_chart.return_value = mock_chart
    store.get_chart.return_value = mock_chart
    store.delete_chart.return_value = None
    store.get_chart_data.return_value = {
        "series": [{"name": "revenue", "data": [100, 200, 300]}]
    }
    store.upsert_dashboard.return_value = mock_dashboard
    store.get_dashboard.return_value = mock_dashboard
    store.delete_dashboard.return_value = None
    store.upsert_chart_stack.return_value = mock_chart_stack
    store.get_chart_stack.return_value = mock_chart_stack
    return store


@pytest.fixture
def real_viz_design_rule() -> VizDesignRule:
    """Create a real VizDesignRule for use in VizDesignRuleResponse."""
    now = datetime.now(UTC)
    return VizDesignRule(
        rule_id="rule_001",
        document_type="action-implementation",
        origin_path="/data-viz-bible/selection/selection-line_chart.md",
        pipeline_stage="selection",
        chart_type="line_chart",
        section_path="Selection: Line Chart > When to Use",
        content="[Line Chart - Selection - When to Use]\nShows trends...",
        tags=["selection", "line_chart"],
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_viz_design_rule_response(
    real_viz_design_rule: VizDesignRule,
) -> VizDesignRuleResponse:
    """Create a VizDesignRuleResponse with retrieval stats."""
    return VizDesignRuleResponse(
        rule=real_viz_design_rule,
        stats=RetrievalStats(rank=1, score=0.95),
    )


@pytest.fixture
def mock_core_context_store(
    mock_viz_design_rule: Mock,
    mock_blueprint_rule: Mock,
    mock_viz_design_rule_response: VizDesignRuleResponse,
) -> Mock:
    """Create a mock CoreContextStore."""
    store = Mock()
    store.get_viz_design_rule.return_value = mock_viz_design_rule
    store.get_blueprint_rule.return_value = mock_blueprint_rule
    store.get_chart_rules.return_value = [mock_viz_design_rule]
    store.get_foundation_rules.return_value = [mock_viz_design_rule]
    store.search_viz_design_rules.return_value = [mock_viz_design_rule_response]
    return store


# =============================================================================
# ChartsVisualizationClient Tests
# =============================================================================


class TestChartsVisualizationClient:
    """Tests for ChartsVisualizationClient."""

    def test_create_chart(
        self,
        mock_chart_store: Mock,
        mock_chart: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test creating a new chart."""
        client = ChartsVisualizationClient(chart_store=mock_chart_store)

        result = client.create(mock_chart, tenant=tenant_context, user=user_context)

        assert result.id == "chart_001"
        mock_chart_store.upsert_chart.assert_called_once_with(
            mock_chart, tenant=tenant_context, user=user_context
        )

    def test_update_chart(
        self,
        mock_chart_store: Mock,
        mock_chart: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test updating an existing chart."""
        client = ChartsVisualizationClient(chart_store=mock_chart_store)

        result = client.update(
            "chart_001", mock_chart, tenant=tenant_context, user=user_context
        )

        assert result.id == "chart_001"
        mock_chart_store.upsert_chart.assert_called_once()

    def test_update_chart_id_mismatch(
        self,
        mock_chart_store: Mock,
        mock_chart: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test updating a chart with mismatched ID corrects the ID."""
        client = ChartsVisualizationClient(chart_store=mock_chart_store)
        mock_chart.id = "different_id"

        client.update("chart_001", mock_chart, tenant=tenant_context, user=user_context)

        # The ID should be corrected
        assert mock_chart.id == "chart_001"

    def test_get_chart(
        self,
        mock_chart_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting a chart by ID."""
        client = ChartsVisualizationClient(chart_store=mock_chart_store)

        result = client.get("chart_001", tenant=tenant_context, user=user_context)

        assert result.id == "chart_001"
        mock_chart_store.get_chart.assert_called_once_with(
            "chart_001", version=None, tenant=tenant_context, user=user_context
        )

    def test_get_chart_with_version(
        self,
        mock_chart_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting a specific version of a chart."""
        client = ChartsVisualizationClient(chart_store=mock_chart_store)

        client.get("chart_001", version=2, tenant=tenant_context, user=user_context)

        mock_chart_store.get_chart.assert_called_once_with(
            "chart_001", version=2, tenant=tenant_context, user=user_context
        )

    def test_list_charts(
        self,
        mock_chart_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test listing charts returns empty list (placeholder)."""
        client = ChartsVisualizationClient(chart_store=mock_chart_store)

        result = client.list(tenant=tenant_context, user=user_context)

        assert result == []

    def test_delete_chart(
        self,
        mock_chart_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test deleting a chart."""
        client = ChartsVisualizationClient(chart_store=mock_chart_store)

        client.delete("chart_001", version=1, tenant=tenant_context, user=user_context)

        mock_chart_store.delete_chart.assert_called_once_with(
            "chart_001", 1, tenant=tenant_context, user=user_context
        )

    def test_get_chart_data(
        self,
        mock_chart_store: Mock,
        mock_chart: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting data for a chart."""
        client = ChartsVisualizationClient(chart_store=mock_chart_store)
        mock_chart.version = 1

        result = client.get_data("chart_001", tenant=tenant_context, user=user_context)

        assert "series" in result
        mock_chart_store.get_chart_data.assert_called_once()


# =============================================================================
# DashboardsVisualizationClient Tests
# =============================================================================


class TestDashboardsVisualizationClient:
    """Tests for DashboardsVisualizationClient."""

    def test_create_dashboard(
        self,
        mock_chart_store: Mock,
        mock_dashboard: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test creating a new dashboard."""
        client = DashboardsVisualizationClient(chart_store=mock_chart_store)

        result = client.create(mock_dashboard, tenant=tenant_context, user=user_context)

        assert result.id == "dashboard_001"
        mock_chart_store.upsert_dashboard.assert_called_once()

    def test_update_dashboard(
        self,
        mock_chart_store: Mock,
        mock_dashboard: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test updating an existing dashboard."""
        client = DashboardsVisualizationClient(chart_store=mock_chart_store)

        result = client.update(
            "dashboard_001", mock_dashboard, tenant=tenant_context, user=user_context
        )

        assert result.id == "dashboard_001"

    def test_update_dashboard_id_mismatch(
        self,
        mock_chart_store: Mock,
        mock_dashboard: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test updating a dashboard with mismatched ID corrects the ID."""
        client = DashboardsVisualizationClient(chart_store=mock_chart_store)
        mock_dashboard.id = "different_id"

        client.update(
            "dashboard_001", mock_dashboard, tenant=tenant_context, user=user_context
        )

        assert mock_dashboard.id == "dashboard_001"

    def test_get_dashboard(
        self,
        mock_chart_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting a dashboard by ID."""
        client = DashboardsVisualizationClient(chart_store=mock_chart_store)

        result = client.get("dashboard_001", tenant=tenant_context, user=user_context)

        assert result.id == "dashboard_001"
        mock_chart_store.get_dashboard.assert_called_once_with(
            "dashboard_001", tenant=tenant_context, user=user_context
        )

    def test_list_dashboards(
        self,
        mock_chart_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test listing dashboards returns empty list (placeholder)."""
        client = DashboardsVisualizationClient(chart_store=mock_chart_store)

        result = client.list(tenant=tenant_context, user=user_context)

        assert result == []

    def test_clone_dashboard(
        self,
        mock_chart_store: Mock,
        mock_dashboard: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test cloning a dashboard."""
        client = DashboardsVisualizationClient(chart_store=mock_chart_store)

        # Create a real Dashboard-like mock for cloning
        from xlake.models import Dashboard

        original = Dashboard()
        original.id = "dashboard_001"
        original.title = "Original Dashboard"
        mock_chart_store.get_dashboard.return_value = original

        # Mock upsert to return the modified dashboard
        def capture_upsert(dashboard: Dashboard, **kwargs: Any) -> Dashboard:
            return dashboard

        mock_chart_store.upsert_dashboard.side_effect = capture_upsert

        result = client.clone("dashboard_001", tenant=tenant_context, user=user_context)

        assert result.id != "dashboard_001"  # New ID should be different
        assert "(Copy)" in result.title

    def test_publish_dashboard(
        self,
        mock_chart_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test publishing a dashboard (no-op placeholder)."""
        client = DashboardsVisualizationClient(chart_store=mock_chart_store)

        # Should not raise
        client.publish("dashboard_001", tenant=tenant_context, user=user_context)

        mock_chart_store.get_dashboard.assert_called_once()

    def test_delete_dashboard(
        self,
        mock_chart_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test deleting a dashboard."""
        client = DashboardsVisualizationClient(chart_store=mock_chart_store)

        client.delete("dashboard_001", tenant=tenant_context, user=user_context)

        mock_chart_store.delete_dashboard.assert_called_once_with(
            "dashboard_001", tenant=tenant_context, user=user_context
        )


# =============================================================================
# StacksVisualizationClient Tests
# =============================================================================


class TestStacksVisualizationClient:
    """Tests for StacksVisualizationClient."""

    def test_create_stack(
        self,
        mock_chart_store: Mock,
        mock_chart_stack: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test creating a new chart stack."""
        client = StacksVisualizationClient(chart_store=mock_chart_store)

        result = client.create(
            mock_chart_stack, tenant=tenant_context, user=user_context
        )

        assert result.id == "stack_001"
        mock_chart_store.upsert_chart_stack.assert_called_once()

    def test_update_stack(
        self,
        mock_chart_store: Mock,
        mock_chart_stack: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test updating an existing stack."""
        client = StacksVisualizationClient(chart_store=mock_chart_store)

        result = client.update(
            "stack_001", mock_chart_stack, tenant=tenant_context, user=user_context
        )

        assert result.id == "stack_001"

    def test_update_stack_id_mismatch(
        self,
        mock_chart_store: Mock,
        mock_chart_stack: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test updating a stack with mismatched ID corrects the ID."""
        client = StacksVisualizationClient(chart_store=mock_chart_store)
        mock_chart_stack.id = "different_id"

        client.update(
            "stack_001", mock_chart_stack, tenant=tenant_context, user=user_context
        )

        assert mock_chart_stack.id == "stack_001"

    def test_get_stack(
        self,
        mock_chart_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting a stack by ID."""
        client = StacksVisualizationClient(chart_store=mock_chart_store)

        result = client.get("stack_001", tenant=tenant_context, user=user_context)

        assert result.id == "stack_001"
        mock_chart_store.get_chart_stack.assert_called_once_with(
            "stack_001", tenant=tenant_context, user=user_context
        )

    def test_list_stacks(
        self,
        mock_chart_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test listing stacks returns empty list (placeholder)."""
        client = StacksVisualizationClient(chart_store=mock_chart_store)

        result = client.list(tenant=tenant_context, user=user_context)

        assert result == []

    def test_delete_stack_not_implemented(
        self,
        mock_chart_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test deleting a stack raises NotImplementedError."""
        client = StacksVisualizationClient(chart_store=mock_chart_store)

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            client.delete("stack_001", tenant=tenant_context, user=user_context)


# =============================================================================
# RulesVisualizationClient Tests
# =============================================================================


class TestRulesVisualizationClient:
    """Tests for RulesVisualizationClient."""

    def test_get_rule(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting a design rule by ID."""
        client = RulesVisualizationClient(core_context_store=mock_core_context_store)

        result = client.get("rule_001", tenant=tenant_context, user=user_context)

        assert result.rule_id == "rule_001"
        mock_core_context_store.get_viz_design_rule.assert_called_once_with(
            "rule_001", tenant=tenant_context, user=user_context
        )

    def test_get_blueprint(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting a blueprint (interface document) for a pipeline stage."""
        client = RulesVisualizationClient(core_context_store=mock_core_context_store)

        result = client.get_blueprint(
            "selection", tenant=tenant_context, user=user_context
        )

        assert result.document_type == "action-interface"
        assert result.pipeline_stage == "selection"
        mock_core_context_store.get_blueprint_rule.assert_called_once_with(
            "selection", tenant=tenant_context, user=user_context
        )

    def test_get_for_chart(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting rules for a specific chart type at a pipeline stage."""
        client = RulesVisualizationClient(core_context_store=mock_core_context_store)

        result = client.get_for_chart(
            "selection", "line_chart", tenant=tenant_context, user=user_context
        )

        assert len(result) == 1
        mock_core_context_store.get_chart_rules.assert_called_once_with(
            "selection",
            "line_chart",
            library=None,
            tenant=tenant_context,
            user=user_context,
        )

    def test_get_for_chart_with_library(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting implementation rules with library specified."""
        client = RulesVisualizationClient(core_context_store=mock_core_context_store)

        result = client.get_for_chart(
            "implementation",
            "line_chart",
            library="recharts",
            tenant=tenant_context,
            user=user_context,
        )

        assert len(result) == 1
        mock_core_context_store.get_chart_rules.assert_called_once_with(
            "implementation",
            "line_chart",
            library="recharts",
            tenant=tenant_context,
            user=user_context,
        )

    def test_get_foundation(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test getting foundation/reference document rules."""
        client = RulesVisualizationClient(core_context_store=mock_core_context_store)

        result = client.get_foundation(
            category="schema", tenant=tenant_context, user=user_context
        )

        assert len(result) == 1
        mock_core_context_store.get_foundation_rules.assert_called_once_with(
            category="schema", tenant=tenant_context, user=user_context
        )

    def test_search_rules(
        self,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test searching rules by semantic query."""
        client = RulesVisualizationClient(core_context_store=mock_core_context_store)

        result = client.search(
            "best chart for time data",
            pipeline_stage="selection",
            tenant=tenant_context,
            user=user_context,
        )

        assert len(result) == 1
        # Verify the result contains VizDesignRuleResponse with rule and stats
        assert hasattr(result[0], "rule")
        assert hasattr(result[0], "stats")
        assert result[0].stats.rank == 1
        assert result[0].stats.score == 0.95
        mock_core_context_store.search_viz_design_rules.assert_called_once_with(
            "best chart for time data",
            pipeline_stage="selection",
            chart_types=None,
            priorities=None,
            top_k=10,
            tenant=tenant_context,
            user=user_context,
        )


# =============================================================================
# VisualizationClient (Facade) Tests
# =============================================================================


class TestVisualizationClient:
    """Tests for the VisualizationClient facade."""

    def test_initialization(
        self,
        mock_chart_store: Mock,
        mock_core_context_store: Mock,
    ) -> None:
        """Test VisualizationClient initializes sub-clients correctly."""
        client = VisualizationClient(
            chart_store=mock_chart_store,
            core_context_store=mock_core_context_store,
        )

        assert hasattr(client, "charts")
        assert hasattr(client, "dashboards")
        assert hasattr(client, "stacks")
        assert hasattr(client, "rules")
        assert isinstance(client.charts, ChartsVisualizationClient)
        assert isinstance(client.dashboards, DashboardsVisualizationClient)
        assert isinstance(client.stacks, StacksVisualizationClient)
        assert isinstance(client.rules, RulesVisualizationClient)

    def test_charts_via_facade(
        self,
        mock_chart_store: Mock,
        mock_core_context_store: Mock,
        mock_chart: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test accessing charts through the facade."""
        client = VisualizationClient(
            chart_store=mock_chart_store,
            core_context_store=mock_core_context_store,
        )

        result = client.charts.get(
            "chart_001", tenant=tenant_context, user=user_context
        )

        assert result.id == "chart_001"
        mock_chart_store.get_chart.assert_called_once()

    def test_dashboards_via_facade(
        self,
        mock_chart_store: Mock,
        mock_core_context_store: Mock,
        mock_dashboard: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test accessing dashboards through the facade."""
        client = VisualizationClient(
            chart_store=mock_chart_store,
            core_context_store=mock_core_context_store,
        )

        result = client.dashboards.get(
            "dashboard_001", tenant=tenant_context, user=user_context
        )

        assert result.id == "dashboard_001"
        mock_chart_store.get_dashboard.assert_called_once()

    def test_rules_via_facade(
        self,
        mock_chart_store: Mock,
        mock_core_context_store: Mock,
        tenant_context: TenantContext,
        user_context: UserContext,
    ) -> None:
        """Test accessing rules through the facade."""
        client = VisualizationClient(
            chart_store=mock_chart_store,
            core_context_store=mock_core_context_store,
        )

        result = client.rules.get("rule_001", tenant=tenant_context, user=user_context)

        assert result.rule_id == "rule_001"
        mock_core_context_store.get_viz_design_rule.assert_called_once()
