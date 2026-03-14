"""VisualizationDesigner agent implementation.

A 2-stage pipeline for visualization design:
1. Selection - Choose optimal chart type and initial data mapping
2. Refinement - Classify data series, generate highlights (FINAL OUTPUT)

The agent is stateless — it outputs a semantic chart specification and
AgentChartResponse, but does NOT persist anything. State management
(persistence to CustomerChartStore, data freezing) is handled by the
upstream application API layer.

The UI handles all visual styling (colors, fonts, structural config)
via style-guide.ts.

Architecture
------------
``VisualizationDesigner`` extends :class:`~agents.base.AgentBuilder`
and builds a ``StateGraph`` using the LangGraph **"invoke from a node"**
subgraph pattern with ``input=`` / ``output=`` schema separation
(following the ``open_deep_research`` production pattern)::

    StateGraph(
        VizDesignerGraphState,      # internal (includes bridge fields)
        input=VizDesignerInput,     # what the caller provides
        output=VizDesignerOutput,   # what the caller receives
    )

    START -> selection -> transform -> refinement -> END

Each stage node invokes its own sub-agent (created via
``create_agent``) with a completely different state schema
(``VizSelectionState``, ``VizRefinementState``).  The parent graph's
``RunnableConfig`` (including ``AgentContext``) propagates
automatically, so no custom Runnable wrapper is needed.  The compiled
graph supports the full Runnable API (``invoke``, ``ainvoke``,
``stream``, ``astream``, etc.).

Example::

    from xlake.api import create_xlake_client
    from agents.viz_designer import VisualizationDesigner
    from agents.viz_designer.config import VisualizationDesignerSettings
    from agents.lib.utils import create_agent_context

    # Create client and designer (default model is gpt-4o-mini)
    client = create_xlake_client()
    settings = VisualizationDesignerSettings()
    designer = VisualizationDesigner(
        settings=settings,
        xlake_client=client,
    )

    # Compile the pipeline (cached)
    pipeline = designer.compile()

    # Invoke with context
    ctx = create_agent_context(tenant=tenant, user=user)
    result = await pipeline.ainvoke(
        {
            "messages": [],
            "nlp_query": "Show revenue trends over time",
            "output_schema": {...},
            "materialized_data": [...],
        },
        context=ctx,
    )

    # Access final AgentChartResponse
    response: AgentChartResponse = result.get("agent_response")
    # response.chart_spec - inline spec for immediate rendering
    # response.data - inline data for immediate rendering
    # Persistence is handled by the upstream application API layer.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.base import AgentBuilder
from agents.models import AgentContext
from agents.viz_designer.config import VisualizationDesignerSettings
from agents.viz_designer.prompts import (
    REFINEMENT_SYSTEM_PROMPT,
    SELECTION_SYSTEM_PROMPT,
    format_refinement_request,
)
from agents.viz_designer.schemas import (
    AgentChartResponse,
    DimensionSpec,
    FullAgentChartSpec,
    VizDesignerGraphState,
    VizDesignerInput,
    VizDesignerOutput,
    VizRefinementResponseSchema,
    VizRefinementState,
    VizSelectionResponseSchema,
    VizSelectionState,
)

if TYPE_CHECKING:
    from xlake.api import XLakeClient


class VisualizationDesigner(AgentBuilder):
    """Visualization designer agent pipeline builder.

    Extends :class:`~agents.base.AgentBuilder` to build a 2-stage
    LangGraph pipeline for chart design:
    Selection -> Refinement (final)

    Uses the LangGraph **"invoke from a node"** subgraph pattern so
    that each sub-agent operates on its own focused state
    (``VizSelectionState``, ``VizRefinementState``) while the parent
    graph uses a thin orchestration state (``VizDesignerGraphState``)
    with ``input=`` / ``output=`` schema separation to hide internal
    bridge fields from the caller.

    The agent is stateless — it outputs a semantic chart specification
    but does NOT persist anything.  State management (CustomerChartStore,
    data freezing) is handled by the upstream application API layer.

    The agent outputs a semantic chart specification with:

    - chart_type, title, data_mapping
    - data_series with semantic classifications (prominence, purpose,
      sentiment)
    - highlights linked to insights via insight_id

    The UI handles visual styling via style-guide.ts (colors, fonts,
    structural config).
    """

    def __init__(
        self,
        settings: VisualizationDesignerSettings,
        xlake_client: XLakeClient | None = None,
    ):
        """Initialize the VisualizationDesigner builder.

        Args:
            settings: Complete configuration for the pipeline.
            xlake_client: XLakeClient instance for accessing viz design
                rules.  If provided, automatically adds the
                ``search_viz_design_rules`` tool.
        """
        super().__init__()
        self.settings = settings
        self._xlake_client = xlake_client
        self._tools = self._build_tools()

    # ------------------------------------------------------------------
    # Tool setup
    # ------------------------------------------------------------------

    def _build_tools(self) -> list:
        """Build tools from xlake_client."""
        tools: list = []
        if self._xlake_client:
            from agents.tools.search_tools import (
                SearchTools,
                make_viz_rules_search_tool,
            )

            search_tools = SearchTools(self._xlake_client)
            viz_tool = make_viz_rules_search_tool(search_tools)
            tools.insert(0, viz_tool)
        return tools

    # ------------------------------------------------------------------
    # AgentBuilder implementation (protected)
    # ------------------------------------------------------------------

    def _build(self) -> CompiledStateGraph:
        """Build the 2-stage visualization pipeline.

        Uses the ``StateGraph(State, input=Input, output=Output)``
        pattern from ``open_deep_research``:

        - ``VizDesignerInput``      — what the caller provides
        - ``VizDesignerOutput``     — what the caller receives
        - ``VizDesignerGraphState`` — internal state (includes bridge
          fields like ``selection_result`` that are hidden from the
          caller)

        Each stage node invokes its sub-agent using the LangGraph
        "invoke from a node" pattern — sub-agents have completely
        different state schemas from the parent graph.

        Pipeline::

            START -> selection -> transform -> refinement -> END

        Returns:
            ``CompiledStateGraph`` ready for invocation.
        """
        graph = StateGraph(
            VizDesignerGraphState,
            input=VizDesignerInput,
            output=VizDesignerOutput,
            context_schema=AgentContext,
        )

        # Pipeline nodes
        graph.add_node("selection", self._run_selection)
        graph.add_node("transform", self._selection_to_refinement)
        graph.add_node("refinement", self._run_refinement)

        # Wire linear pipeline
        graph.add_edge(START, "selection")
        graph.add_edge("selection", "transform")
        graph.add_edge("transform", "refinement")
        graph.add_edge("refinement", END)

        return graph.compile(debug=self.settings.debug)

    # ------------------------------------------------------------------
    # Stage creation helpers
    # ------------------------------------------------------------------

    def _create_selection_stage(self) -> CompiledStateGraph:
        """Create the chart selection sub-agent.

        Returns:
            CompiledStateGraph for the selection stage.
        """
        stage = self.settings.get_stage_settings("selection")
        return create_agent(
            model=stage.model,
            tools=self._tools,
            system_prompt=stage.prompt or SELECTION_SYSTEM_PROMPT,
            state_schema=stage.state_schema or VizSelectionState,
            response_format=stage.response_format or VizSelectionResponseSchema,
            context_schema=AgentContext,
            debug=self.settings.debug,
            name="viz_selection",
        )

    def _create_refinement_stage(self) -> CompiledStateGraph:
        """Create the refinement sub-agent.

        Returns:
            CompiledStateGraph for the refinement stage.
        """
        stage = self.settings.get_stage_settings("refinement")
        return create_agent(
            model=stage.model,
            tools=self._tools,
            system_prompt=stage.prompt or REFINEMENT_SYSTEM_PROMPT,
            state_schema=stage.state_schema or VizRefinementState,
            response_format=stage.response_format or VizRefinementResponseSchema,
            context_schema=AgentContext,
            debug=self.settings.debug,
            name="viz_refinement",
        )

    # ------------------------------------------------------------------
    # Graph node functions  ("invoke from a node" pattern)
    # ------------------------------------------------------------------

    async def _run_selection(
        self,
        state: VizDesignerGraphState,
        config: RunnableConfig,
    ) -> dict[str, Any]:
        """Node: invoke the selection sub-agent.

        Follows the LangGraph "invoke from a node" pattern — the
        sub-agent (``VizSelectionState``) has a completely different
        schema from the parent graph.  The node transforms the parent
        state into the subgraph state, invokes the subgraph, and
        transforms the output back into a parent state update.

        The parent graph's ``config`` is forwarded so that the
        ``Runtime`` (including ``AgentContext``) propagates
        automatically.
        """
        agent = self._create_selection_stage()

        # Transform parent state -> selection subgraph state
        result = await agent.ainvoke(
            {
                "messages": state["messages"],
                "nlp_query": state["nlp_query"],
                "output_schema": state["output_schema"],
                "materialized_data": state["materialized_data"],
            },
            config=config,
        )

        # Transform selection output -> parent state update
        return {"selection_result": result["structured_response"]}

    def _selection_to_refinement(
        self,
        state: VizDesignerGraphState,
    ) -> dict[str, Any]:
        """Node: transform selection output into refinement input.

        Reads ``selection_result`` from the bridge field and formats a
        ``HumanMessage`` with full context for the refinement LLM.
        This is a pure transform — no sub-agent invocation.
        """
        selection_result = state["selection_result"]
        selection_dict = (
            selection_result.model_dump()
            if hasattr(selection_result, "model_dump")
            else selection_result or {}
        )
        formatted_request = format_refinement_request(
            selection_result=selection_dict,
            data_schema=state["output_schema"],
            materialized_data=state["materialized_data"],
            nlp_query=state["nlp_query"],
        )

        # Replace messages so the refinement agent sees only the
        # formatted request, not the selection conversation history.
        return {"messages": [HumanMessage(content=formatted_request)]}

    async def _run_refinement(
        self,
        state: VizDesignerGraphState,
        config: RunnableConfig,
    ) -> dict[str, Any]:
        """Node: invoke the refinement sub-agent and build final response.

        Follows the LangGraph "invoke from a node" pattern.  Combines
        the refinement invocation and response building into a single
        node so that ``refinement_result`` remains a local variable
        and never touches the parent state.
        """
        agent = self._create_refinement_stage()

        # Transform parent state -> refinement subgraph state
        result = await agent.ainvoke(
            {
                "messages": state["messages"],
                "selection_result": state["selection_result"],
                "nlp_query": state["nlp_query"],
                "output_schema": state["output_schema"],
                "materialized_data": state["materialized_data"],
                "conversation_id": state.get("conversation_id"),
            },
            config=config,
        )

        # Build AgentChartResponse from refinement output (local variable)
        refinement_result: VizRefinementResponseSchema = result["structured_response"]
        agent_response = self._assemble_chart_response(
            refinement_result=refinement_result,
            materialized_data=state.get("materialized_data", []),
            output_schema=state.get("output_schema", {}),
            conversation_id=state.get("conversation_id"),
        )

        return {"agent_response": agent_response}

    # ------------------------------------------------------------------
    # Response assembly (not a graph node — called from _run_refinement)
    # ------------------------------------------------------------------

    def _assemble_chart_response(
        self,
        *,
        refinement_result: VizRefinementResponseSchema,
        materialized_data: list[dict[str, Any]],
        output_schema: dict[str, Any],
        conversation_id: str | None,
    ) -> AgentChartResponse:
        """Build the final ``AgentChartResponse``.

        Extracts the refinement result, generates IDs for the upstream
        API layer, and constructs the full chart specification.

        The agent is stateless — persistence to CustomerChartStore is
        handled by the upstream application API layer using the
        returned IDs.
        """
        conversation_id = conversation_id or str(uuid.uuid4())

        # Generate IDs for the upstream API layer to use for persistence
        chart_id = f"chart_{uuid.uuid4().hex[:12]}"
        data_slice_id = f"slice_{uuid.uuid4().hex[:12]}"

        # Build dimensions from output_schema
        dimensions = self._extract_dimensions(output_schema)

        # Build sub-chart specs for combo charts
        sub_chart_specs = []
        if refinement_result.chart_type == "combo" and refinement_result.sub_charts:
            for sub in refinement_result.sub_charts:
                sub_chart_specs.append(
                    FullAgentChartSpec(
                        id=sub.id,
                        title=sub.title,
                        chart_type=sub.chart_type,
                        dimensions=dimensions,  # inherit parent dimensions
                        filters=[],
                        chart_data_slice_ids=[],  # inherit parent's slices
                        version=1,
                        schema_version=1,
                        data_mapping=sub.data_mapping,
                        data_series=sub.data_series,
                    )
                )

        # Build FullAgentChartSpec
        chart_spec = FullAgentChartSpec(
            id=chart_id,
            title=refinement_result.title,
            chart_type=refinement_result.chart_type,
            dimensions=dimensions,
            filters=[],
            chart_data_slice_ids=[data_slice_id],
            version=1,
            schema_version=1,
            data_mapping=refinement_result.data_mapping,
            data_series=refinement_result.data_series,
            sub_charts=sub_chart_specs,
        )

        # Build AgentChartResponse
        return AgentChartResponse(
            chart_id=chart_id,
            data_slice_id=data_slice_id,
            conversation_id=conversation_id,
            chart_spec=chart_spec,
            data={"rows": materialized_data},
            highlights=refinement_result.highlights,
            insights=refinement_result.insights,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_dimensions(output_schema: dict[str, Any]) -> list[DimensionSpec]:
        """Extract dimension specs from output schema.

        Args:
            output_schema: Schema describing the data fields.

        Returns:
            List of DimensionSpec objects.
        """
        dimensions = []
        fields = output_schema.get("fields", [])

        for field in fields:
            field_name = field.get("name", "")
            field_type = field.get("type", "").lower()
            field_role = field.get("role", "").lower()

            if field_role == "temporal" or "date" in field_type or "time" in field_type:
                dim_type = "time"
            elif field_role == "measure" or field_type in (
                "int",
                "float",
                "number",
                "decimal",
            ):
                dim_type = "numeric"
            else:
                dim_type = "category"

            dimensions.append(DimensionSpec(field=field_name, type=dim_type))

        return dimensions
