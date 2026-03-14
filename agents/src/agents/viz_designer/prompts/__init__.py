"""Prompts for VisualizationDesigner pipeline stages.

The pipeline is 2-stage: Selection -> Refinement (final).
Styling and implementation are handled by the UI via style-guide.ts.
"""

from .refinement import (
    REFINEMENT_REQUEST_TEMPLATE,
    REFINEMENT_SYSTEM_PROMPT,
    format_refinement_request,
)
from .selection import (
    SELECTION_REQUEST_TEMPLATE,
    SELECTION_SYSTEM_PROMPT,
    SELECTION_SYSTEM_PROMPT_1,
    SELECTION_SYSTEM_PROMPT_2,
    format_selection_request,
)

__all__ = [
    # Selection stage
    "SELECTION_SYSTEM_PROMPT",
    "SELECTION_SYSTEM_PROMPT_1",
    "SELECTION_SYSTEM_PROMPT_2",
    "SELECTION_REQUEST_TEMPLATE",
    "format_selection_request",
    # Refinement stage (final)
    "REFINEMENT_SYSTEM_PROMPT",
    "REFINEMENT_REQUEST_TEMPLATE",
    "format_refinement_request",
]
