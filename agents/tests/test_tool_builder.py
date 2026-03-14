"""Tests for ToolBuilder base class.

Tests cover:
- ToolBuilder initialization and caching behavior
- compile() method behavior
- reset() method behavior
- Subclass prevention of compile() override
"""

from __future__ import annotations

import pytest
from langchain_core.tools import BaseTool, tool

from agents.tools.base import ToolBuilder

# =============================================================================
# Test Fixtures
# =============================================================================


class ConcreteToolBuilder(ToolBuilder):
    """Concrete implementation of ToolBuilder for testing."""

    def __init__(self, tool_name: str = "test_tool"):
        super().__init__()
        self.tool_name = tool_name
        self.build_call_count = 0

    def _build(self) -> BaseTool:
        """Build a simple test tool."""
        self.build_call_count += 1

        @tool
        def test_tool(query: str) -> str:
            """A test tool for unit tests."""
            return f"Result for: {query}"

        # Set the name after creation if needed
        test_tool.name = self.tool_name
        return test_tool


@pytest.fixture
def tool_builder() -> ConcreteToolBuilder:
    """Create a test tool builder."""
    return ConcreteToolBuilder()


# =============================================================================
# ToolBuilder Tests
# =============================================================================


class TestToolBuilder:
    """Tests for ToolBuilder base class."""

    def test_init_compiled_is_none(self, tool_builder: ConcreteToolBuilder) -> None:
        """Test that _compiled is None after initialization."""
        assert tool_builder._compiled is None

    def test_compile_returns_base_tool(self, tool_builder: ConcreteToolBuilder) -> None:
        """Test that compile() returns a BaseTool."""
        result = tool_builder.compile()
        assert result is not None
        assert hasattr(result, "invoke")
        assert hasattr(result, "name")

    def test_compile_caches_result(self, tool_builder: ConcreteToolBuilder) -> None:
        """Test that compile() caches the result."""
        tool1 = tool_builder.compile()
        tool2 = tool_builder.compile()
        assert tool1 is tool2

    def test_compile_calls_build_once(self, tool_builder: ConcreteToolBuilder) -> None:
        """Test that _build() is only called once."""
        tool_builder.compile()
        tool_builder.compile()
        tool_builder.compile()
        assert tool_builder.build_call_count == 1

    def test_reset_clears_cache(self, tool_builder: ConcreteToolBuilder) -> None:
        """Test that reset() clears the cached compilation."""
        tool1 = tool_builder.compile()
        tool_builder.reset()
        assert tool_builder._compiled is None
        tool2 = tool_builder.compile()
        assert tool1 is not tool2

    def test_reset_allows_rebuild(self, tool_builder: ConcreteToolBuilder) -> None:
        """Test that reset() allows _build() to be called again."""
        tool_builder.compile()
        assert tool_builder.build_call_count == 1
        tool_builder.reset()
        tool_builder.compile()
        assert tool_builder.build_call_count == 2

    def test_tool_has_correct_name(self, tool_builder: ConcreteToolBuilder) -> None:
        """Test that the compiled tool has the expected name."""
        result = tool_builder.compile()
        assert result.name == "test_tool"

    def test_tool_can_be_invoked(self, tool_builder: ConcreteToolBuilder) -> None:
        """Test that the compiled tool can be invoked."""
        result = tool_builder.compile()
        output = result.invoke({"query": "hello"})
        assert "Result for: hello" in output


# =============================================================================
# Subclass Restriction Tests
# =============================================================================


class TestToolBuilderSubclassRestrictions:
    """Tests for ToolBuilder subclass restrictions."""

    def test_cannot_override_compile(self) -> None:
        """Test that subclasses cannot override compile()."""
        with pytest.raises(TypeError) as excinfo:

            class BadToolBuilder(ToolBuilder):
                def _build(self) -> BaseTool:
                    @tool
                    def dummy(query: str) -> str:
                        """Dummy."""
                        return query

                    return dummy

                def compile(self) -> BaseTool:  # noqa: F811
                    """Attempt to override compile."""
                    return self._build()

        assert "must not override compile()" in str(excinfo.value)
        assert "BadToolBuilder" in str(excinfo.value)

    def test_can_override_build(self) -> None:
        """Test that subclasses can override _build() (required)."""

        class CustomToolBuilder(ToolBuilder):
            def _build(self) -> BaseTool:
                @tool
                def custom_tool(query: str) -> str:
                    """Custom tool."""
                    return f"Custom: {query}"

                return custom_tool

        builder = CustomToolBuilder()
        result = builder.compile()
        assert result.name == "custom_tool"

    def test_can_add_reset_override(self) -> None:
        """Test that subclasses can override reset() with custom logic."""

        class ExtendedToolBuilder(ToolBuilder):
            def __init__(self):
                super().__init__()
                self.reset_count = 0

            def _build(self) -> BaseTool:
                @tool
                def extended_tool(query: str) -> str:
                    """Extended tool."""
                    return query

                return extended_tool

            def reset(self) -> None:
                """Extended reset with custom logic."""
                self.reset_count += 1
                super().reset()

        builder = ExtendedToolBuilder()
        builder.compile()
        builder.reset()
        assert builder.reset_count == 1
        assert builder._compiled is None


# =============================================================================
# Edge Cases
# =============================================================================


class TestToolBuilderEdgeCases:
    """Tests for edge cases and error handling."""

    def test_different_tool_names(self) -> None:
        """Test that different builders can have different tool names."""
        builder1 = ConcreteToolBuilder(tool_name="tool_one")
        builder2 = ConcreteToolBuilder(tool_name="tool_two")

        tool1 = builder1.compile()
        tool2 = builder2.compile()

        assert tool1.name == "tool_one"
        assert tool2.name == "tool_two"

    def test_multiple_builders_independent_caching(self) -> None:
        """Test that multiple builders have independent caches."""
        builder1 = ConcreteToolBuilder()
        builder2 = ConcreteToolBuilder()

        tool1 = builder1.compile()
        builder1.reset()

        # builder2 should still have its cache
        tool2 = builder2.compile()
        tool2_again = builder2.compile()
        assert tool2 is tool2_again

        # builder1 should rebuild
        tool1_new = builder1.compile()
        assert tool1 is not tool1_new
