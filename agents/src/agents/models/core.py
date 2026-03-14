"""Core models for agent context and dependencies."""

from dataclasses import dataclass

from xlake.core import TenantContext, UserContext


@dataclass
class AgentContext:
    """Context passed to agent tools via ToolRuntime.context.

    Contains per-request context (tenant/user), not app-level dependencies.
    The XLakeClient and other app-level dependencies should be injected
    into tool classes at initialization time, not passed through context.

    Example:
        ```python
        from agents.models import AgentContext

        ctx = AgentContext(tenant=tenant, user=user)
        result = agent.invoke({"messages": [...]}, context=ctx)
        ```
    """

    tenant: TenantContext
    user: UserContext
