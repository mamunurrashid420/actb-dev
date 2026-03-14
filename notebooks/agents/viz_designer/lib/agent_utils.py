"""Agent utilities for visualization designer notebooks.

Provides helpers for building and running agent stages in isolation
for testing and exploration.
"""

from __future__ import annotations

from langgraph.graph.state import CompiledStateGraph

from agents.viz_designer.agent import VisualizationDesigner


def build_selection_stage(viz_designer: VisualizationDesigner) -> CompiledStateGraph:
    """Build the selection stage as a standalone runnable (for testing).

    Wraps VisualizationDesigner._create_selection_stage() so notebooks
    can run only the chart selection step without compiling the full
    pipeline.

    Returns a compiled graph that can be invoked directly with
    VizSelectionState.

    Args:
        viz_designer: VisualizationDesigner instance (with settings
            and xlake_client configured).

    Returns:
        CompiledStateGraph for the selection stage.

    Example:
        ```python
        from agents.viz_designer.agent import VisualizationDesigner
        from agents.viz_designer.config import VisualizationDesignerSettings
        from lib.agent_utils import build_selection_stage

        viz_agent = VisualizationDesigner(settings=settings, xlake_client=xlake_client)
        selector_agent = build_selection_stage(viz_agent)
        ```
    """
    return viz_designer._create_selection_stage()
