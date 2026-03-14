"""Base builder infrastructure for LangGraph-based agents.

All new agents should extend :class:`AgentBuilder` and implement
:meth:`_build` to construct their agent graph.  Consumers call
:meth:`compile` to obtain a standard ``CompiledStateGraph`` that
supports the full LangChain Runnable API (``invoke``, ``ainvoke``,
``stream``, ``astream``, ``batch``, etc.).

Context is passed per-request via LangGraph's native ``context=``
parameter — no custom Runnable wrapper is needed.

Example::

    from agents.base import AgentBuilder
    from agents.models import AgentContext

    class MyAgent(AgentBuilder):
        def _build(self):
            graph = StateGraph(MyState, context_schema=AgentContext)
            # ... add nodes / edges ...
            return graph.compile()

    agent = MyAgent(settings=settings)
    graph = agent.compile()
    result = await graph.ainvoke(state, context=ctx)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, final

from langgraph.graph.state import CompiledStateGraph


class AgentBuilder(ABC):
    """Base builder for all LangGraph-based agents.

    Subclasses implement :meth:`_build` to construct the agent graph.
    Consumers call :meth:`compile` to get a standard
    ``CompiledStateGraph`` with the full Runnable API.

    The ``_build`` method (single-underscore prefix) is *protected by
    convention* — it should only be called by the framework, never
    directly by application code.

    The ``compile`` method is **non-overridable**: it is decorated with
    ``@typing.final`` (for static type-checkers) and enforced at
    runtime via ``__init_subclass__``.  If a subclass attempts to
    define ``compile``, a ``TypeError`` is raised at class-definition
    time.

    Usage::

        agent = MyAgent(settings=settings)
        graph = agent.compile()
        result = await graph.ainvoke(state, context=ctx)
    """

    def __init__(self) -> None:
        self._compiled: CompiledStateGraph | None = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if "compile" in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} must not override compile(). "
                "Implement _build() instead."
            )

    # ------------------------------------------------------------------
    # Subclass hook (protected)
    # ------------------------------------------------------------------

    @abstractmethod
    def _build(self) -> CompiledStateGraph:
        """Construct and return the compiled agent graph.

        Subclasses must implement this method.  It is called once by
        :meth:`compile` and the result is cached for subsequent calls.

        Returns:
            A ``CompiledStateGraph`` ready for invocation.
        """
        ...

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @final
    def compile(self) -> CompiledStateGraph:
        """Compile and return the agent graph (cached).

        This is the **public entry-point** for obtaining the executable
        agent.  It calls :meth:`_build` on the first invocation and
        caches the result for subsequent calls.

        This method is **non-overridable** — subclasses must implement
        ``_build()`` instead.

        Returns:
            A ``CompiledStateGraph`` supporting the full Runnable API.
        """
        if self._compiled is None:
            self._compiled = self._build()
        return self._compiled

    def reset(self) -> None:
        """Clear the cached compilation.

        Useful in testing or when the builder's configuration has
        changed and you need a fresh graph.
        """
        self._compiled = None
