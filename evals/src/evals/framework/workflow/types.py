"""Workflow trace types for capturing LangGraph execution.

Provides dataclasses for recording tool calls, agent executions,
and full workflow traces for evaluation.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """Record of a single tool invocation."""

    tool_name: str
    args: dict
    result: Any | None = None
    error: str | None = None
    duration_ms: float = 0


@dataclass
class AgentTrace:
    """Trace of a single agent execution within workflow."""

    agent_name: str
    input: dict
    output: dict | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    error: str | None = None
    duration_ms: float = 0


# Alias for backward compatibility and spec alignment
AgentSpan = AgentTrace


@dataclass
class WorkflowTrace:
    """Full trace of workflow execution."""

    agents: list[AgentTrace] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)

    def get_agent(self, name: str) -> AgentTrace | None:
        """Get trace for a specific agent by name."""
        return next((a for a in self.agents if a.agent_name == name), None)

    def has_errors(self) -> bool:
        """Check if any agent or tool raised an error."""
        agent_errors = any(a.error for a in self.agents)
        tool_errors = any(t.error for t in self.tool_calls)
        return agent_errors or tool_errors

    def agents_invoked(self) -> list[str]:
        """Get list of agent names that were invoked."""
        return [a.agent_name for a in self.agents]

    def get_tool_calls(self, tool_name: str) -> list[ToolCall]:
        """Get all tool calls for a specific tool."""
        return [tc for tc in self.tool_calls if tc.tool_name == tool_name]
