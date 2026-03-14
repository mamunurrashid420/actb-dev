"""Base builder infrastructure for LangChain tools.

All tool builders should extend :class:`ToolBuilder` and implement
:meth:`_build` to construct their tool.  Consumers call :meth:`compile`
to obtain a standard ``BaseTool`` instance.

This follows the same pattern as :class:`~agents.base.AgentBuilder` for
consistency across the codebase.

Example::

    from agents.tools.base import ToolBuilder
    from langchain_core.tools import BaseTool, tool

    class MySearchTool(ToolBuilder):
        def __init__(self, client: SomeClient):
            super().__init__()
            self._client = client

        def _build(self) -> BaseTool:
            @tool
            def search(query: str) -> str:
                '''Search for documents.'''
                return self._client.search(query)
            return search

    builder = MySearchTool(client=client)
    my_tool = builder.compile()
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, final

from langchain_core.tools import BaseTool


class ToolBuilder(ABC):
    """Base builder for all LangChain tools.

    Subclasses implement :meth:`_build` to construct the tool.
    Consumers call :meth:`compile` to get a standard ``BaseTool``.

    The ``_build`` method (single-underscore prefix) is *protected by
    convention* — it should only be called by the framework, never
    directly by application code.

    The ``compile`` method is **non-overridable**: it is decorated with
    ``@typing.final`` (for static type-checkers) and enforced at
    runtime via ``__init_subclass__``.  If a subclass attempts to
    define ``compile``, a ``TypeError`` is raised at class-definition
    time.

    Usage::

        builder = MySearchTool(client=client)
        tool = builder.compile()
        # Use tool with agents
    """

    def __init__(self) -> None:
        self._compiled: BaseTool | None = None

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
    def _build(self) -> BaseTool:
        """Construct and return the tool.

        Subclasses must implement this method.  It is called once by
        :meth:`compile` and the result is cached for subsequent calls.

        Returns:
            A ``BaseTool`` ready for use with agents.
        """
        ...

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @final
    def compile(self) -> BaseTool:
        """Compile and return the tool (cached).

        This is the **public entry-point** for obtaining the tool.
        It calls :meth:`_build` on the first invocation and caches
        the result for subsequent calls.

        This method is **non-overridable** — subclasses must implement
        ``_build()`` instead.

        Returns:
            A ``BaseTool`` ready for use with agents.
        """
        if self._compiled is None:
            self._compiled = self._build()
        return self._compiled

    def reset(self) -> None:
        """Clear the cached compilation.

        Useful in testing or when the builder's configuration has
        changed and you need a fresh tool.
        """
        self._compiled = None
