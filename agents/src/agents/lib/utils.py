"""Utilities for agent invocation and context.

Agents are **stateless and idempotent** — per-request context
(tenant, user) is passed via LangGraph's native ``context=``
parameter rather than being embedded in the agent instance.

Example::

    from agents.lib.utils import create_agent_context

    ctx = create_agent_context(tenant=tenant, user=user)
    result = await graph.ainvoke(state, context=ctx)

The context is automatically available inside graph nodes via
``ToolRuntime[AgentContext]`` and through ``langgraph.config.get_config()``.
"""

from __future__ import annotations

from agents.models import AgentContext
from xlake.core import TenantContext, UserContext


def create_agent_context(
    *,
    tenant: TenantContext,
    user: UserContext,
) -> AgentContext:
    """Create an :class:`AgentContext` for agent invocation.

    This is a thin factory that standardises how application code
    builds the per-request context that is threaded through the
    agent graph.

    Args:
        tenant: Tenant identity and configuration.
        user: Authenticated user information.

    Returns:
        An ``AgentContext`` instance to pass as ``context=`` when
        invoking a compiled agent graph.
    """
    return AgentContext(tenant=tenant, user=user)
