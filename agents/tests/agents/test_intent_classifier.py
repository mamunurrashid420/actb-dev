"""Unit tests for IntentClassifier schemas."""

import pytest

from agents.intent_classifier.schemas import (
    ExtractedEntities,
    IntentClassifierInput,
    IntentClassifierOutput,
)


class TestIntentClassifierInput:
    """Tests for IntentClassifierInput schema."""

    def test_minimal_input(self):
        """Should accept just message_text."""
        inp = IntentClassifierInput(message_text="Show me revenue")
        assert inp.message_text == "Show me revenue"
        assert inp.conversation_id is None
        assert inp.dashboard_id is None

    def test_full_input(self):
        """Should accept all optional fields."""
        inp = IntentClassifierInput(
            message_text="Show me revenue",
            conversation_id="conv-123",
            dashboard_id="dash-456",
            chart_id="chart-789",
            panel_context="interpreter",
            active_filters=["region=EMEA", "year=2024"],
            user_role="executive",
            conversation_summary="User previously asked about Q3 revenue.",
        )
        assert inp.conversation_id == "conv-123"
        assert inp.panel_context == "interpreter"
        assert len(inp.active_filters) == 2


class TestIntentClassifierOutput:
    """Tests for IntentClassifierOutput schema."""

    def test_minimal_output(self):
        """Should accept required fields only."""
        output = IntentClassifierOutput(
            task="consult",
            mode="reporter",
            job="query",
            confidence=0.9,
            rationale="Direct data request",
        )
        assert output.task == "consult"
        assert output.mode == "reporter"
        assert output.job == "query"
        assert output.extracted_entities is None

    def test_output_with_entities(self):
        """Should accept extracted entities."""
        output = IntentClassifierOutput(
            task="consult",
            mode="reporter",
            job="query",
            confidence=0.85,
            rationale="Revenue query",
            extracted_entities=ExtractedEntities(
                metrics=["revenue"],
                dimensions=["region"],
                filters={"year": "2024"},
                time_range="Q4",
            ),
        )
        assert output.extracted_entities is not None
        assert "revenue" in output.extracted_entities.metrics
        assert output.extracted_entities.filters["year"] == "2024"

    def test_output_with_clarification(self):
        """Should accept clarification question for clarify job."""
        output = IntentClassifierOutput(
            task="consult",
            mode="reporter",
            job="clarify",
            confidence=0.4,
            rationale="Query too vague",
            clarification_question="What specific data are you looking for?",
        )
        assert output.job == "clarify"
        assert output.clarification_question is not None

    @pytest.mark.parametrize(
        "invalid_confidence",
        [1.5, -0.1, 2.0, -1.0],
    )
    def test_confidence_bounds_enforced(self, invalid_confidence: float):
        """Confidence must be between 0 and 1."""
        with pytest.raises(ValueError):
            IntentClassifierOutput(
                task="consult",
                mode="reporter",
                job="query",
                confidence=invalid_confidence,
                rationale="Test",
            )

    @pytest.mark.parametrize("valid_confidence", [0.0, 0.5, 1.0])
    def test_valid_confidence_values(self, valid_confidence: float):
        """Valid confidence values should be accepted."""
        output = IntentClassifierOutput(
            task="consult",
            mode="reporter",
            job="query",
            confidence=valid_confidence,
            rationale="Test",
        )
        assert output.confidence == valid_confidence


class TestExtractedEntities:
    """Tests for ExtractedEntities schema."""

    def test_empty_entities(self):
        """Should allow all empty/default values."""
        entities = ExtractedEntities()
        assert entities.metrics == []
        assert entities.dimensions == []
        assert entities.filters == {}
        assert entities.time_range is None

    def test_full_entities(self):
        """Should accept all fields."""
        entities = ExtractedEntities(
            metrics=["revenue", "margin"],
            dimensions=["region", "product"],
            filters={"year": "2024", "company": "Apple"},
            time_range="Q4 2024",
            chart_type="bar_chart_vertical",
            comparison_target="vs Q3",
        )
        assert len(entities.metrics) == 2
        assert len(entities.filters) == 2
        assert entities.comparison_target == "vs Q3"
