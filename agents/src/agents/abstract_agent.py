"""Legacy base agent infrastructure for actBI.

.. deprecated::
    This module contains the legacy ``BaseAgent`` class which uses a custom
    LLM framework (``LLMClient``).  New agents should extend
    :class:`agents.base.AgentBuilder` instead, which builds LangGraph-based
    agents with the full Runnable API.

The ``BaseAgent`` is still used by:
- ``IntentClassifier``
- ``DataExplorer``

These agents will be migrated to ``AgentBuilder`` in a future release.
"""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod

from pydantic import BaseModel

from agents.llm import LLMClient


class BaseAgent[InputT: BaseModel, OutputT: BaseModel](ABC):
    """Framework-agnostic base agent (DEPRECATED).

    .. deprecated::
        Use :class:`agents.base.AgentBuilder` for new agents.  ``BaseAgent``
        remains available for legacy agents (IntentClassifier, DataExplorer)
        but will be removed in a future version.

    All agents inherit from this class and implement:
    - default_prompt(): Returns the system prompt
    - arun(): Async execution method

    Subclasses can use self.llm_client for LLM interactions.
    """

    def __init__(
        self,
        prompt_override: str | None = None,
        model: str | None = None,
        llm: LLMClient | None = None,
    ):
        warnings.warn(
            "BaseAgent is deprecated. New agents should extend "
            "agents.base.AgentBuilder instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.prompt = prompt_override or self.default_prompt()
        self.llm_client = llm or LLMClient(model=model)

    @abstractmethod
    def default_prompt(self) -> str:
        """Return the default system prompt for this agent."""
        pass

    @abstractmethod
    async def arun(self, input: InputT) -> OutputT:
        """Run the agent asynchronously."""
        pass

    def run(self, input: InputT) -> OutputT:
        """Synchronous wrapper for arun()."""
        import asyncio

        return asyncio.run(self.arun(input))
