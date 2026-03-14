"""VisualizationClient for the XLake Unified API.

The VisualizationClient manages all visual representations and UI state,
excluding the underlying data itself. It wraps CustomerChartStore and
CoreContextStore (VizDesignRules).

Four sub-clients:
- ChartsVisualizationClient: Create and manage charts
- DashboardsVisualizationClient: Create and manage dashboards
- StacksVisualizationClient: Create and manage chart stacks
- RulesVisualizationClient: Access visualization design rules
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..core import TenantContext, UserContext
from .models import (
    ChartSummary,
    DashboardSummary,
    StackSummary,
)

if TYPE_CHECKING:
    from ..models import (
        Chart,
        ChartStack,
        Dashboard,
        VizDesignRule,
        VizDesignRuleResponse,
    )
    from ..stores import CoreContextStore, CustomerChartStore


# =============================================================================
# ChartsVisualizationClient
# =============================================================================


class ChartsVisualizationClient:
    """Sub-client for chart operations.

    Accessed via `visualization.charts`.

    Backed by CustomerChartStore.
    """

    def __init__(self, chart_store: CustomerChartStore) -> None:
        """Initialize the charts sub-client.

        Args:
            chart_store: CustomerChartStore instance for chart access.
        """
        self._chart_store = chart_store

    def create(
        self,
        chart: Chart,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> Chart:
        """Create a new chart.

        Args:
            chart: Chart protobuf message to create.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Created chart with assigned identifiers.
        """
        return self._chart_store.upsert_chart(chart, tenant=tenant, user=user)

    def update(
        self,
        chart_id: str,
        updates: Chart,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> Chart:
        """Update an existing chart.

        Args:
            chart_id: Identifier of the chart to update.
            updates: Chart protobuf message with updated fields.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Updated chart.

        Raises:
            KeyError: If the chart is not found.
        """
        # Ensure the chart ID matches
        if updates.id != chart_id:
            updates.id = chart_id
        return self._chart_store.upsert_chart(updates, tenant=tenant, user=user)

    def get(
        self,
        chart_id: str,
        version: int | None = None,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> Chart:
        """Get a chart by ID and optional version.

        Args:
            chart_id: Identifier of the chart.
            version: Optional specific version to retrieve.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Chart protobuf message.

        Raises:
            KeyError: If the chart is not found.
        """
        return self._chart_store.get_chart(
            chart_id, version=version, tenant=tenant, user=user
        )

    def list(
        self,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[ChartSummary]:
        """List all charts for the tenant.

        Args:
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            List of chart summaries.
        """
        # TODO: Implement chart listing in CustomerChartStore
        # For now, return empty list as placeholder
        return []

    def delete(
        self,
        chart_id: str,
        version: int,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        """Delete a chart version.

        Args:
            chart_id: Identifier of the chart to delete.
            version: Version of the chart to delete.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Raises:
            KeyError: If the chart is not found.
        """
        self._chart_store.delete_chart(chart_id, version, tenant=tenant, user=user)

    def get_data(
        self,
        chart_id: str,
        *,
        context: str = "dashboard",
        conversation_id: str | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> dict[str, Any]:
        """Get the data slice for a chart with context-aware fetching.

        Args:
            chart_id: Identifier of the chart.
            context: Data context - "dashboard" (live, refreshable) or
                "conversation" (frozen snapshot). Defaults to "dashboard".
            conversation_id: Required when context="conversation" to identify
                which frozen snapshot to retrieve.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Chart data as a dictionary.

        Raises:
            KeyError: If the chart or data slice is not found.
            ValueError: If context="conversation" but conversation_id is not provided.
        """
        if context == "conversation" and not conversation_id:
            raise ValueError("conversation_id is required when context='conversation'")

        # Get the chart to find the associated data slice
        chart = self._chart_store.get_chart(chart_id, tenant=tenant, user=user)

        if context == "conversation" and conversation_id:
            # Fetch frozen data for conversation
            slice_id = f"{chart_id}_conv_{conversation_id}"
        else:
            # Fetch live dashboard data (may trigger refresh)
            slice_id = f"{chart_id}_v{chart.version}"

        return self._chart_store.get_chart_data(slice_id, tenant=tenant, user=user)

    def get_data_slice(
        self,
        slice_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> dict[str, Any]:
        """Get a specific data slice by ID.

        Args:
            slice_id: Identifier of the data slice.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Data slice as a dictionary.

        Raises:
            KeyError: If the data slice is not found.
        """
        return self._chart_store.get_chart_data(slice_id, tenant=tenant, user=user)

    def get_highlights(
        self,
        chart_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[Any]:
        """Get highlights for a chart.

        Highlights are visual instructions for emphasizing data in charts,
        linked to insights via insight_id for UI color coordination.

        Args:
            chart_id: Identifier of the chart.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            List of Highlight protobuf messages.

        Raises:
            KeyError: If the chart is not found.
        """
        # TODO: Implement highlight retrieval in CustomerChartStore
        # For now, return empty list as placeholder
        # Will need: self._chart_store.get_highlights(chart_id, tenant, user)
        _ = self._chart_store.get_chart(chart_id, tenant=tenant, user=user)
        return []


# =============================================================================
# DashboardsVisualizationClient
# =============================================================================


class DashboardsVisualizationClient:
    """Sub-client for dashboard operations.

    Accessed via `visualization.dashboards`.

    Backed by CustomerChartStore.
    """

    def __init__(self, chart_store: CustomerChartStore) -> None:
        """Initialize the dashboards sub-client.

        Args:
            chart_store: CustomerChartStore instance for dashboard access.
        """
        self._chart_store = chart_store

    def create(
        self,
        dashboard: Dashboard,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> Dashboard:
        """Create a new dashboard.

        Args:
            dashboard: Dashboard protobuf message to create.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Created dashboard with assigned identifiers.
        """
        return self._chart_store.upsert_dashboard(dashboard, tenant=tenant, user=user)

    def update(
        self,
        dashboard_id: str,
        updates: Dashboard,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> Dashboard:
        """Update an existing dashboard.

        Args:
            dashboard_id: Identifier of the dashboard to update.
            updates: Dashboard protobuf message with updated fields.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Updated dashboard.

        Raises:
            KeyError: If the dashboard is not found.
        """
        if updates.id != dashboard_id:
            updates.id = dashboard_id
        return self._chart_store.upsert_dashboard(updates, tenant=tenant, user=user)

    def get(
        self,
        dashboard_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> Dashboard:
        """Get a dashboard by ID.

        Args:
            dashboard_id: Identifier of the dashboard.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Dashboard protobuf message.

        Raises:
            KeyError: If the dashboard is not found.
        """
        return self._chart_store.get_dashboard(dashboard_id, tenant=tenant, user=user)

    def list(
        self,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[DashboardSummary]:
        """List all dashboards for the tenant.

        Args:
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            List of dashboard summaries.
        """
        # TODO: Implement dashboard listing in CustomerChartStore
        return []

    def clone(
        self,
        dashboard_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> Dashboard:
        """Clone a dashboard.

        Args:
            dashboard_id: Identifier of the dashboard to clone.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            New cloned dashboard.

        Raises:
            KeyError: If the source dashboard is not found.
        """
        # Get the original dashboard
        original = self._chart_store.get_dashboard(
            dashboard_id, tenant=tenant, user=user
        )
        # Create a copy with a new ID
        import uuid

        from ..models import Dashboard

        cloned = Dashboard()
        cloned.CopyFrom(original)
        cloned.id = str(uuid.uuid4())
        cloned.title = f"{original.title} (Copy)"
        return self._chart_store.upsert_dashboard(cloned, tenant=tenant, user=user)

    def publish(
        self,
        dashboard_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        """Publish a dashboard (mark as published).

        Args:
            dashboard_id: Identifier of the dashboard to publish.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Raises:
            KeyError: If the dashboard is not found.
        """
        # TODO: Implement publish flag/state in dashboard metadata
        # For now, this is a no-op placeholder
        _ = self._chart_store.get_dashboard(dashboard_id, tenant=tenant, user=user)

    def delete(
        self,
        dashboard_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        """Delete a dashboard.

        Args:
            dashboard_id: Identifier of the dashboard to delete.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Raises:
            KeyError: If the dashboard is not found.
        """
        self._chart_store.delete_dashboard(dashboard_id, tenant=tenant, user=user)


# =============================================================================
# StacksVisualizationClient
# =============================================================================


class StacksVisualizationClient:
    """Sub-client for chart stack operations.

    Accessed via `visualization.stacks`.

    Backed by CustomerChartStore.
    """

    def __init__(self, chart_store: CustomerChartStore) -> None:
        """Initialize the stacks sub-client.

        Args:
            chart_store: CustomerChartStore instance for stack access.
        """
        self._chart_store = chart_store

    def create(
        self,
        stack: ChartStack,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> ChartStack:
        """Create a new chart stack.

        Args:
            stack: ChartStack protobuf message to create.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Created chart stack with assigned identifiers.
        """
        return self._chart_store.upsert_chart_stack(stack, tenant=tenant, user=user)

    def update(
        self,
        stack_id: str,
        updates: ChartStack,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> ChartStack:
        """Update an existing chart stack.

        Args:
            stack_id: Identifier of the stack to update.
            updates: ChartStack protobuf message with updated fields.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Updated chart stack.

        Raises:
            KeyError: If the stack is not found.
        """
        if updates.id != stack_id:
            updates.id = stack_id
        return self._chart_store.upsert_chart_stack(updates, tenant=tenant, user=user)

    def get(
        self,
        stack_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> ChartStack:
        """Get a chart stack by ID.

        Args:
            stack_id: Identifier of the stack.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            ChartStack protobuf message.

        Raises:
            KeyError: If the stack is not found.
        """
        return self._chart_store.get_chart_stack(stack_id, tenant=tenant, user=user)

    def list(
        self,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[StackSummary]:
        """List all chart stacks for the tenant.

        Args:
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            List of stack summaries.
        """
        # TODO: Implement stack listing in CustomerChartStore
        return []

    def delete(
        self,
        stack_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        """Delete a chart stack.

        Args:
            stack_id: Identifier of the stack to delete.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Raises:
            KeyError: If the stack is not found.
        """
        # TODO: Implement stack deletion in CustomerChartStore
        raise NotImplementedError("Stack deletion is not yet implemented.")


# =============================================================================
# RulesVisualizationClient
# =============================================================================


class RulesVisualizationClient:
    """Sub-client for visualization design rules.

    Accessed via `visualization.rules`.

    Backed by CoreContextStore (VizDesignRule).

    Retrieval patterns:
    - get(): Returns single VizDesignRule by ID
    - get_blueprint(): Returns single VizDesignRule (interface docs are single chunks)
    - get_for_chart(): Returns list (chart-specific docs are split by section)
    - get_foundation(): Returns list (foundation docs are split by section)
    - search(): Returns list (semantic search across all rules)
    """

    def __init__(self, core_context_store: CoreContextStore) -> None:
        """Initialize the rules sub-client.

        Args:
            core_context_store: CoreContextStore instance for design rules.
        """
        self._core_context = core_context_store

    def get(
        self,
        rule_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> VizDesignRule:
        """Get a design rule by ID.

        Args:
            rule_id: Identifier of the design rule.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            VizDesignRule object.

        Raises:
            KeyError: If the rule is not found.
        """
        return self._core_context.get_viz_design_rule(rule_id, tenant=tenant, user=user)

    def get_blueprint(
        self,
        pipeline_stage: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> VizDesignRule:
        """Get the blueprint (interface document) for a pipeline stage.

        Blueprints describe the overall process for each stage and are
        stored as single chunks. Returns one VizDesignRule.

        Args:
            pipeline_stage: "selection" | "refinement" | "formatting" | "implementation"
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Single VizDesignRule containing the blueprint document.

        Raises:
            KeyError: If no blueprint exists for the given stage.
        """
        return self._core_context.get_blueprint_rule(
            pipeline_stage, tenant=tenant, user=user
        )

    def get_for_chart(
        self,
        pipeline_stage: str,
        chart_type: str,
        *,
        library: str | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[VizDesignRule]:
        """Get rules for a specific chart type at a pipeline stage.

        Chart-specific documents are split by section, so this returns
        multiple VizDesignRule chunks (e.g., "When to Use", "Data Requirements", etc.)

        Args:
            pipeline_stage: "selection" | "refinement" | "formatting" | "implementation"
            chart_type: Chart type slug (e.g., "line_chart", "bar_chart_vertical")
            library: Required for implementation stage (e.g., "recharts", "d3")
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            List of VizDesignRule chunks for the chart type.
        """
        return self._core_context.get_chart_rules(
            pipeline_stage, chart_type, library=library, tenant=tenant, user=user
        )

    def get_foundation(
        self,
        *,
        category: str | None = None,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[VizDesignRule]:
        """Get foundation/reference document rules.

        Args:
            category: "schema" | "classification" | "index" | None (all)
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            List of VizDesignRule chunks from foundation documents.
        """
        return self._core_context.get_foundation_rules(
            category=category, tenant=tenant, user=user
        )

    def search(
        self,
        query: str,
        *,
        pipeline_stage: str | None = None,
        chart_types: list[str] | None = None,
        priorities: list[str] | None = None,
        top_k: int = 10,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[VizDesignRuleResponse]:
        """Search for design rules by semantic query with filtering.

        Args:
            query: Natural language query to search for relevant rules.
            pipeline_stage: Filter by pipeline stage.
            chart_types: Filter by chart types.
            priorities: Filter by priority levels (e.g., ["P0", "P1"]).
            top_k: Maximum number of results.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            List of VizDesignRuleResponse with rules and retrieval stats.
        """
        return self._core_context.search_viz_design_rules(
            query,
            pipeline_stage=pipeline_stage,
            chart_types=chart_types,
            priorities=priorities,
            top_k=top_k,
            tenant=tenant,
            user=user,
        )


# =============================================================================
# VisualizationClient (Facade)
# =============================================================================


class VisualizationClient:
    """High-level visualization client for XLake.

    Manages all visual representations and UI state, excluding the
    underlying data itself.

    Sub-clients:
    - `charts`: Create and manage charts
    - `dashboards`: Create and manage dashboards
    - `stacks`: Create and manage chart stacks
    - `rules`: Access visualization design rules

    Top-level methods:
    - `get_insights_and_recommendations()`: Get insights for a chart stack

    Example:
        ```python
        viz = VisualizationClient(chart_store, core_context_store)
        chart = viz.charts.get("chart_001", tenant=tenant, user=user)
        dashboard = viz.dashboards.create(dashboard, tenant=tenant, user=user)
        rules = viz.rules.search("time series", tenant=tenant, user=user)

        # Get insights for a stack
        insights = viz.get_insights_and_recommendations(
            "stack_001", tenant=tenant, user=user
        )
        ```
    """

    def __init__(
        self,
        chart_store: CustomerChartStore,
        core_context_store: CoreContextStore,
    ) -> None:
        """Initialize the VisualizationClient.

        Args:
            chart_store: CustomerChartStore instance.
            core_context_store: CoreContextStore instance for design rules.
        """
        self._chart_store = chart_store
        self.charts = ChartsVisualizationClient(chart_store)
        self.dashboards = DashboardsVisualizationClient(chart_store)
        self.stacks = StacksVisualizationClient(chart_store)
        self.rules = RulesVisualizationClient(core_context_store)

    def get_insights_and_recommendations(
        self,
        stack_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[Any]:
        """Get insights and recommendations for a chart stack.

        Insights are observations about data with linked visual evidence
        (highlights). Each insight can have embedded recommendations.

        Args:
            stack_id: Identifier of the chart stack.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            List of Insight protobuf messages (with embedded Recommendations).

        Raises:
            KeyError: If the stack is not found.
        """
        # TODO: Implement insight retrieval in CustomerChartStore
        # For now, return empty list as placeholder
        # Will need: self._chart_store.get_insights(stack_id, tenant, user)
        _ = self._chart_store.get_chart_stack(stack_id, tenant=tenant, user=user)
        return []
