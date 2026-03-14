"""Service layer for viz designer playground endpoint.

Handles chart spec persistence to CustomerChartStore via xlake_client
after the agent produces its output. The agent itself is stateless.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from xlake.core import TenantContext, TenantIdentity, UserContext

if TYPE_CHECKING:
    from agents.viz_designer.schemas import AgentChartResponse
    from xlake.api.client import XLakeClient
    from xlake.models import Chart

logger = logging.getLogger(__name__)


class VizDesignerPlaygroundService:
    """Persistence service for the viz designer playground.

    Constructs lightweight TenantContext / UserContext from the
    request-provided IDs (defaulting to "playground") and persists the
    chart spec via xlake_client.visualization.charts.create().
    """

    def __init__(self, xlake_client: XLakeClient) -> None:
        self._xlake_client = xlake_client

    def persist_chart(
        self,
        agent_response: AgentChartResponse,
        *,
        tenant_id: str,
        user_id: str,
    ) -> None:
        """Persist chart spec to CustomerChartStore.

        Converts the FullAgentChartSpec (Pydantic ProtoModel) to a
        protobuf Chart message via ``to_proto()``, then calls
        ``xlake_client.visualization.charts.create()``.

        Args:
            agent_response: The AgentChartResponse from the agent pipeline.
            tenant_id: Tenant identifier for xlake isolation.
            user_id: User identifier for xlake permissions.
        """
        tenant = TenantContext(
            identity=TenantIdentity(
                tenant_id=tenant_id,
                tenant_name=tenant_id,
                industry="playground",
                region="playground",
                timezone="UTC",
                locale="en_US",
            ),
        )
        user = UserContext(
            user_id=user_id,
            tenant_id=tenant_id,
            role="admin",
        )

        proto_chart = cast("Chart", agent_response.chart_spec.to_proto())

        logger.info(
            "Persisting chart %s for tenant=%s user=%s",
            agent_response.chart_id,
            tenant_id,
            user_id,
        )
        self._xlake_client.visualization.charts.create(
            proto_chart,
            tenant=tenant,
            user=user,
        )
