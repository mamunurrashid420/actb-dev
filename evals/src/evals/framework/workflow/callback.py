"""LangGraph callback for capturing workflow execution traces.

Provides a callback handler that records agent and tool executions
during LangGraph workflow execution for evaluation.
"""

import json
import time
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

from evals.framework.workflow.types import AgentTrace, ToolCall, WorkflowTrace


class WorkflowTraceCallback(BaseCallbackHandler):
    """LangGraph callback that captures workflow execution trace."""

    def __init__(self):
        self.trace = WorkflowTrace()
        self._current_agent: AgentTrace | None = None
        self._current_tool: ToolCall | None = None
        self._agent_start_time: float | None = None

    def on_chain_start(
        self, serialized: dict[str, Any], inputs: dict[str, Any], **kwargs: Any
    ) -> None:
        """Called when an agent/chain starts."""
        name = serialized.get("name", serialized.get("id", ["unknown"])[-1])
        self._current_agent = AgentTrace(agent_name=name, input=inputs)
        self._agent_start_time = time.perf_counter()

    def on_chain_end(self, outputs: dict[str, Any], **kwargs: Any) -> None:
        """Called when an agent/chain completes."""
        if self._current_agent:
            self._current_agent.output = outputs
            if self._agent_start_time:
                self._current_agent.duration_ms = (
                    time.perf_counter() - self._agent_start_time
                ) * 1000
            self.trace.agents.append(self._current_agent)
            self._current_agent = None
            self._agent_start_time = None

    def on_chain_error(self, error: BaseException, **kwargs: Any) -> None:
        """Called when an agent/chain raises an error."""
        if self._current_agent:
            self._current_agent.error = str(error)
            self.trace.agents.append(self._current_agent)
            self._current_agent = None

    def on_tool_start(
        self, serialized: dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Called when a tool starts."""
        name = serialized.get("name", "unknown")
        # input_str may be JSON string, try to parse
        try:
            args = json.loads(input_str) if isinstance(input_str, str) else input_str
        except (json.JSONDecodeError, TypeError):
            args = {"raw": input_str}
        self._current_tool = ToolCall(tool_name=name, args=args)

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Called when a tool completes."""
        if self._current_tool:
            self._current_tool.result = output
            self.trace.tool_calls.append(self._current_tool)
            if self._current_agent:
                self._current_agent.tool_calls.append(self._current_tool)
            self._current_tool = None

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        """Called when a tool raises an error."""
        if self._current_tool:
            self._current_tool.error = str(error)
            self.trace.tool_calls.append(self._current_tool)
            if self._current_agent:
                self._current_agent.tool_calls.append(self._current_tool)
            self._current_tool = None
