"""Unit tests for VisualizationDesigner builder with mocked dependencies."""

from unittest.mock import MagicMock, patch

import pytest
from langgraph.graph.state import CompiledStateGraph

from agents.base import AgentBuilder
from agents.models import AgentContext
from agents.viz_designer import VisualizationDesigner
from agents.viz_designer.config import StageSettings, VisualizationDesignerSettings
from agents.viz_designer.prompts import (
    REFINEMENT_SYSTEM_PROMPT,
    SELECTION_SYSTEM_PROMPT,
)
from agents.viz_designer.schemas import (
    DataMapping,
    VizDesignerGraphState,
    VizRefinementResponseSchema,
    VizRefinementState,
    VizSelectionResponseSchema,
    VizSelectionState,
)


class TestStageSettings:
    """Tests for StageSettings model."""

    def test_default_values(self):
        settings = StageSettings(model="gpt-4")
        assert settings.model == "gpt-4"
        assert settings.temperature == 0.0
        assert settings.max_tokens == 4000
        assert settings.prompt is None
        assert settings.state_schema is None
        assert settings.response_format is None


class TestVisualizationDesignerSettings:
    """Tests for VisualizationDesignerSettings (Pydantic Settings)."""

    def test_default_values(self):
        settings = VisualizationDesignerSettings()
        assert settings.default_model == "gpt-4o-mini"
        assert settings.temperature == 0.0
        assert settings.max_tokens == 4000
        assert settings.debug is False
        assert settings.selection_model is None
        assert settings.refinement_model is None

    def test_custom_model(self):
        settings = VisualizationDesignerSettings(
            default_model="anthropic:claude-sonnet-4-20250514"
        )
        assert settings.default_model == "anthropic:claude-sonnet-4-20250514"

    def test_debug_mode(self):
        settings = VisualizationDesignerSettings(debug=True)
        assert settings.debug is True

    def test_get_stage_settings_default(self):
        """Stage settings fall back to pipeline defaults when no override."""
        settings = VisualizationDesignerSettings(default_model="gpt-4")
        stage = settings.get_stage_settings("selection")
        assert stage.model == "gpt-4"
        assert stage.temperature == 0.0

    def test_get_stage_settings_with_override(self):
        """Stage-specific overrides take precedence."""
        settings = VisualizationDesignerSettings(
            default_model="gpt-4",
            selection_model="gpt-4-turbo",
            selection_temperature=0.5,
        )
        selection = settings.get_stage_settings("selection")
        assert selection.model == "gpt-4-turbo"
        assert selection.temperature == 0.5

        # Refinement should still use defaults
        refinement = settings.get_stage_settings("refinement")
        assert refinement.model == "gpt-4"
        assert refinement.temperature == 0.0


class TestVisualizationDesigner:
    """Tests for VisualizationDesigner builder."""

    def test_init_with_settings(self):
        settings = VisualizationDesignerSettings()
        designer = VisualizationDesigner(settings=settings)
        assert designer.settings.default_model == "gpt-4o-mini"
        assert designer._xlake_client is None
        assert designer._tools == []

    def test_init_with_custom_settings(self):
        settings = VisualizationDesignerSettings(
            default_model="anthropic:claude-sonnet-4-20250514",
            debug=True,
        )
        designer = VisualizationDesigner(settings=settings)
        assert designer.settings.default_model == "anthropic:claude-sonnet-4-20250514"
        assert designer.settings.debug is True

    def test_init_with_xlake_client_adds_viz_tool(self):
        """Test that providing xlake_client adds the viz search tool."""
        mock_client = MagicMock()
        mock_viz_tool = MagicMock()
        mock_viz_tool.name = "search_viz_design_rules"

        settings = VisualizationDesignerSettings()

        with (
            patch("agents.tools.search_tools.SearchTools") as mock_search_tools_class,
            patch(
                "agents.tools.search_tools.make_viz_rules_search_tool"
            ) as mock_make_tool,
        ):
            mock_make_tool.return_value = mock_viz_tool
            designer = VisualizationDesigner(
                settings=settings, xlake_client=mock_client
            )

            # Verify tool was created
            mock_search_tools_class.assert_called_once_with(mock_client)
            mock_make_tool.assert_called_once()
            assert len(designer._tools) == 1
            assert designer._tools[0] == mock_viz_tool


class TestAgentBuilderGuard:
    """Tests for AgentBuilder compile() protection."""

    def test_subclass_cannot_override_compile(self):
        """Subclassing AgentBuilder with a compile() method raises TypeError."""
        with pytest.raises(TypeError, match="must not override compile"):

            class BadAgent(AgentBuilder):
                def _build(self) -> CompiledStateGraph: ...

                def compile(self) -> CompiledStateGraph:  # type: ignore[override]
                    ...


class TestStageCreation:
    """Tests for individual stage creation methods."""

    @patch("agents.viz_designer.agent.create_agent")
    def test_create_selection_stage(self, mock_create_agent):
        """Test _create_selection_stage passes correct params."""
        mock_graph = MagicMock()
        mock_create_agent.return_value = mock_graph

        settings = VisualizationDesignerSettings()
        designer = VisualizationDesigner(settings=settings)
        result = designer._create_selection_stage()

        mock_create_agent.assert_called_once()
        call_kwargs = mock_create_agent.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o-mini"
        assert call_kwargs["system_prompt"] == SELECTION_SYSTEM_PROMPT
        assert call_kwargs["state_schema"] == VizSelectionState
        assert call_kwargs["response_format"] == VizSelectionResponseSchema
        assert call_kwargs["context_schema"] == AgentContext
        assert call_kwargs["name"] == "viz_selection"
        assert result == mock_graph

    @patch("agents.viz_designer.agent.create_agent")
    def test_create_refinement_stage(self, mock_create_agent):
        """Test _create_refinement_stage passes correct params."""
        mock_graph = MagicMock()
        mock_create_agent.return_value = mock_graph

        settings = VisualizationDesignerSettings()
        designer = VisualizationDesigner(settings=settings)
        result = designer._create_refinement_stage()

        mock_create_agent.assert_called_once()
        call_kwargs = mock_create_agent.call_args.kwargs
        assert call_kwargs["system_prompt"] == REFINEMENT_SYSTEM_PROMPT
        assert call_kwargs["state_schema"] == VizRefinementState
        assert call_kwargs["response_format"] == VizRefinementResponseSchema
        assert call_kwargs["name"] == "viz_refinement"
        assert result == mock_graph

    @patch("agents.viz_designer.agent.create_agent")
    def test_stage_uses_model_override(self, mock_create_agent):
        """Test that stage creation uses model override from settings."""
        mock_graph = MagicMock()
        mock_create_agent.return_value = mock_graph

        settings = VisualizationDesignerSettings(
            default_model="gpt-4",
            selection_model="anthropic:claude-sonnet-4-20250514",
        )
        designer = VisualizationDesigner(settings=settings)
        designer._create_selection_stage()

        call_kwargs = mock_create_agent.call_args.kwargs
        assert call_kwargs["model"] == "anthropic:claude-sonnet-4-20250514"


class TestTransformMethods:
    """Tests for transform node methods."""

    def test_selection_to_refinement(self):
        """Test _selection_to_refinement transforms state correctly."""
        settings = VisualizationDesignerSettings()
        designer = VisualizationDesigner(settings=settings)

        mock_response = VizSelectionResponseSchema(
            chart_type="line_chart",
            reasoning="Line chart for trends",
            confidence="high",
            data_mapping=DataMapping(x_axis="date", y_axis="value"),
        )

        # Simulate VizDesignerGraphState dict
        state: VizDesignerGraphState = {
            "messages": [],
            "selection_result": mock_response,
            "nlp_query": "Show trend",
            "output_schema": {"fields": []},
            "materialized_data": [{"date": "2024-01", "value": 100}],
            "conversation_id": None,
            "agent_response": None,
        }

        result = designer._selection_to_refinement(state)

        # Messages should contain a HumanMessage with the formatted request
        assert len(result["messages"]) == 1
        assert "messages" in result


class TestPipelineCreation:
    """Tests for full pipeline creation via compile()."""

    def test_compile_returns_compiled_state_graph(self):
        """Test that compile() returns a CompiledStateGraph."""
        settings = VisualizationDesignerSettings()
        designer = VisualizationDesigner(settings=settings)
        pipeline = designer.compile()

        # Should be a CompiledStateGraph (standard Runnable API)
        assert isinstance(pipeline, CompiledStateGraph)

    def test_compile_caches_pipeline(self):
        """Test that compile() returns the same cached pipeline."""
        settings = VisualizationDesignerSettings()
        designer = VisualizationDesigner(settings=settings)
        pipeline1 = designer.compile()
        pipeline2 = designer.compile()

        assert pipeline1 is pipeline2

    def test_reset_clears_cache(self):
        """Test that reset() clears the cached compilation."""
        settings = VisualizationDesignerSettings()
        designer = VisualizationDesigner(settings=settings)
        pipeline1 = designer.compile()
        designer.reset()
        pipeline2 = designer.compile()

        # After reset, should get a new instance
        assert pipeline1 is not pipeline2

    def test_compile_graph_has_expected_nodes(self):
        """Test that the compiled graph has the expected node structure."""
        settings = VisualizationDesignerSettings()
        designer = VisualizationDesigner(settings=settings)
        pipeline = designer.compile()

        graph = pipeline.get_graph()
        node_ids = {node.id for node in graph.nodes.values()}

        # Should have our three pipeline nodes plus __start__ and __end__
        assert "selection" in node_ids
        assert "transform" in node_ids
        assert "refinement" in node_ids
