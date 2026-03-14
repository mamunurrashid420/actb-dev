"""Viz designer playground routes.

Dev-only endpoint (gated by PLAYGROUND=on). No authentication required.
Uses dependency-injector to receive a fresh VisualizationDesigner per
request, and persists the chart spec via xlake_client after the agent runs.
"""

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.messages import HumanMessage

from agents.models import AgentContext
from agents.viz_designer.agent import VisualizationDesigner
from agents.viz_designer.prompts import format_selection_request
from app.containers import AgentsContainer
from xlake.api.client import XLakeClient
from xlake.core import TenantContext, TenantIdentity, UserContext

from .schema import VisualizationCreateRequest, VisualizationCreateResponse
from .service import VizDesignerPlaygroundService

router = APIRouter()


@router.post("/create", response_model=VisualizationCreateResponse)
@inject
async def create_visualization(
    request: VisualizationCreateRequest,
    designer: VisualizationDesigner = Depends(Provide[AgentsContainer.viz_designer]),
    xlake_client: XLakeClient = Depends(Provide[AgentsContainer.xlake_client]),
):
    """Create a visualization from a natural language query.

    Playground endpoint (no auth). The flow:
    1. Receives the NLP query, output_schema, and materialized data
    2. Builds and invokes the 2-stage agent pipeline (Selection -> Refinement)
    3. Persists the chart spec to CustomerChartStore via xlake_client
    4. Returns the AgentChartResponse with inline chart spec and data
    """
    try:
        # Compile the agent pipeline (cached)
        pipeline = designer.compile()

        # Build agent context from request fields (playground defaults)
        tenant = TenantContext(
            identity=TenantIdentity(
                tenant_id=request.tenant_id,
                tenant_name=request.tenant_id,
                industry="playground",
                region="playground",
                timezone="UTC",
                locale="en_US",
            ),
        )
        user = UserContext(
            user_id=request.user_id,
            tenant_id=request.tenant_id,
            role="admin",
        )
        ctx = AgentContext(tenant=tenant, user=user)

        # Format the selection request into a HumanMessage so the LLM
        # actually sees the query, schema, and sample data.
        formatted_request = format_selection_request(
            nlp_query=request.nlp_query,
            output_schema=request.output_schema,
            materialized_data=request.materialized_data,
        )

        # Prepare initial state
        initial_state = {
            "messages": [HumanMessage(content=formatted_request)],
            "nlp_query": request.nlp_query,
            "output_schema": request.output_schema,
            "materialized_data": request.materialized_data,
            "conversation_id": request.conversation_id,
        }

        # Invoke the pipeline
        # Note: context_schema=AgentContext is set in StateGraph construction,
        # enabling the context parameter, but the static type doesn't reflect this.
        result = await pipeline.ainvoke(initial_state, context=ctx)  # type: ignore[arg-type]

        # Extract AgentChartResponse
        agent_response = result.get("agent_response")
        if not agent_response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Agent failed to generate chart response.",
            )

        # Persist chart spec to CustomerChartStore
        persistence = VizDesignerPlaygroundService(xlake_client)
        persistence.persist_chart(
            agent_response,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
        )

        return VisualizationCreateResponse(
            chart_id=agent_response.chart_id,
            data_slice_id=agent_response.data_slice_id,
            conversation_id=agent_response.conversation_id,
            chart_spec=agent_response.chart_spec.model_dump(),
            data=agent_response.data,
            highlights=[h.model_dump() for h in agent_response.highlights],
            insights=[i.model_dump() for i in agent_response.insights],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Visualization creation failed: {e!s}",
        ) from e
