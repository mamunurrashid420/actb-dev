"""Configuration for VisualizationDesigner agent pipeline.

Uses Pydantic Settings for type-safe configuration loaded from
AGENT_VIZ_DESIGNER_* environment variables with sensible defaults.

Default model is ``gpt-4o-mini``.  Override via environment:

Example .env:
    AGENT_VIZ_DESIGNER_DEFAULT_MODEL=anthropic:claude-sonnet-4-20250514
    AGENT_VIZ_DESIGNER_DEBUG=true
    AGENT_VIZ_DESIGNER_SELECTION_MODEL=google:gemini-3-flash-preview
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StageSettings(BaseModel):
    """Resolved configuration for a single pipeline stage.

    Produced by ``VisualizationDesignerSettings.get_stage_settings()``.
    Combines stage-specific overrides with pipeline-wide defaults.

    Attributes:
        model: Model identifier for this stage (e.g., "anthropic:claude-sonnet-4-20250514").
        temperature: Sampling temperature.
        max_tokens: Maximum tokens for LLM response.
        prompt: Custom prompt template (None = use default from prompts.py).
        state_schema: TypedDict state schema (None = use default from schemas.py).
        response_format: Pydantic model for structured output (None = use default).
    """

    model: str
    temperature: float = 0.0
    max_tokens: int = 4000
    prompt: Any | None = None
    state_schema: type | None = None
    response_format: type[BaseModel] | None = None

    model_config = {"arbitrary_types_allowed": True}


class VisualizationDesignerSettings(BaseSettings):
    """Complete configuration for the VisualizationDesigner agent.

    Encapsulates ALL configuration for the agent pipeline:
    - Pipeline-wide model and behavior defaults
    - Per-stage overrides for model and temperature
    - Debug settings

    Loaded from AGENT_VIZ_DESIGNER_* environment variables.
    Default model is ``gpt-4o-mini``.  Override via env vars or constructor.

    Example .env (overrides)::

        AGENT_VIZ_DESIGNER_DEFAULT_MODEL=anthropic:claude-sonnet-4-20250514
        AGENT_VIZ_DESIGNER_DEBUG=true
        AGENT_VIZ_DESIGNER_SELECTION_MODEL=google:gemini-3-flash-preview
        AGENT_VIZ_DESIGNER_REFINEMENT_TEMPERATURE=0.2

    Example usage::

        # From environment (production) — default model is gpt-4o-mini
        settings = get_viz_designer_settings()

        # Direct instantiation with overrides (tests, notebooks)
        settings = VisualizationDesignerSettings(
            default_model="anthropic:claude-sonnet-4-20250514",
            debug=True,
            selection_model="google:gemini-3-flash-preview",
        )
    """

    model_config = SettingsConfigDict(
        env_prefix="AGENT_VIZ_DESIGNER_",
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Pipeline-wide defaults
    default_model: str = Field(
        default="gpt-4o-mini",
        description="Default model for all stages (provider:model format).",
    )
    temperature: float = Field(
        default=0.0,
        description="Default sampling temperature for all stages.",
    )
    max_tokens: int = Field(
        default=4000,
        description="Default max tokens for all stages.",
    )
    debug: bool = Field(
        default=False,
        description="Enable verbose logging for graph execution.",
    )

    # Selection stage overrides (None = use pipeline default)
    selection_model: str | None = Field(
        default=None,
        description="Model override for selection stage.",
    )
    selection_temperature: float | None = Field(
        default=None,
        description="Temperature override for selection stage.",
    )

    # Refinement stage overrides (None = use pipeline default)
    refinement_model: str | None = Field(
        default=None,
        description="Model override for refinement stage.",
    )
    refinement_temperature: float | None = Field(
        default=None,
        description="Temperature override for refinement stage.",
    )

    def get_stage_settings(self, stage: str) -> StageSettings:
        """Get resolved settings for a specific stage.

        Falls back to pipeline defaults for any unset stage-specific value.

        Args:
            stage: Stage name ("selection" or "refinement").

        Returns:
            StageSettings with all values resolved.
        """
        model = getattr(self, f"{stage}_model", None) or self.default_model
        temperature = getattr(self, f"{stage}_temperature", None)
        if temperature is None:
            temperature = self.temperature

        return StageSettings(
            model=model,
            temperature=temperature,
            max_tokens=self.max_tokens,
        )


@lru_cache
def get_viz_designer_settings() -> VisualizationDesignerSettings:
    """Get cached visualization designer settings.

    Called once per process. All configuration loaded from environment.
    """
    return VisualizationDesignerSettings()
