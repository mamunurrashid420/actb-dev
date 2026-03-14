"""I/O schemas for IntentClassifier agent."""

from pydantic import BaseModel, Field

from shared.data.types import Job, Mode, Task


class IntentClassifierInput(BaseModel):
    """Input for intent classification (simplified RequestEnvelope)."""

    message_text: str = Field(description="Raw user message to classify")
    conversation_id: str | None = Field(
        default=None, description="Conversation thread identifier"
    )
    # UI Navigation Context
    dashboard_id: str | None = Field(default=None, description="Active dashboard")
    chart_id: str | None = Field(default=None, description="Active chart")
    panel_context: str | None = Field(
        default=None, description="story_view, interpreter, explorer"
    )
    # Analytical State
    active_filters: list[str] | None = Field(
        default=None, description="Current filter chips"
    )
    # User Context
    user_role: str | None = Field(default=None, description="analyst, executive, etc.")
    # Conversation history
    conversation_summary: str | None = Field(
        default=None, description="Summary of recent conversation turns"
    )


class ExtractedEntities(BaseModel):
    """Entities extracted from user message for downstream agents."""

    metrics: list[str] = Field(
        default_factory=list, description="KPIs, measures mentioned"
    )
    dimensions: list[str] = Field(
        default_factory=list, description="Dimensions, groupings"
    )
    filters: dict[str, str] = Field(
        default_factory=dict, description="Explicit filters (year: '2024')"
    )
    time_range: str | None = Field(default=None, description="Temporal scope")
    chart_type: str | None = Field(
        default=None, description="If user specified chart type"
    )
    comparison_target: str | None = Field(
        default=None, description="vs last quarter, vs budget"
    )


class IntentClassifierOutput(BaseModel):
    """Output from intent classification."""

    task: Task = Field(description="consult (discovery) or reflect (analysis)")
    mode: Mode = Field(description="reporter, interpreter, or explorer")
    job: Job = Field(description="Workflow type to trigger")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Classification confidence (0-1)"
    )
    rationale: str = Field(description="Brief explanation of classification")
    extracted_entities: ExtractedEntities | None = Field(
        default=None, description="Entities extracted for downstream agents"
    )
    clarification_question: str | None = Field(
        default=None, description="Question to ask user if job == 'clarify'"
    )

    def __str__(self) -> str:
        """Format output for display."""
        lines = [
            f"  Task:       {self.task}",
            f"  Mode:       {self.mode}",
            f"  Job:        {self.job}",
            f"  Confidence: {self.confidence:.0%}",
            f"  Rationale:  {self.rationale}",
        ]
        if self.extracted_entities:
            entities = self.extracted_entities
            if entities.metrics:
                lines.append(f"  Metrics:    {', '.join(entities.metrics)}")
            if entities.dimensions:
                lines.append(f"  Dimensions: {', '.join(entities.dimensions)}")
            if entities.filters:
                lines.append(f"  Filters:    {entities.filters}")
            if entities.time_range:
                lines.append(f"  Time range: {entities.time_range}")
        if self.clarification_question:
            lines.append(f"  Clarification: {self.clarification_question}")
        return "\n".join(lines)
