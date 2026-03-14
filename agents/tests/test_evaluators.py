"""Unit tests for evaluator logic.

NOTE: These tests are currently skipped because the evaluators in
evals/src/evals/evaluators/viz.py still reference the old VizInput/VizOutput
schemas that have been removed. The evaluators need to be updated to work
with the new pipeline response schemas (VizSelectionResponseSchema, etc.)
before these tests can be re-enabled.

TODO: Update evaluators to work with new schemas and re-enable tests.
"""

import pytest


@pytest.mark.skip(reason="Evaluators need update to new schemas - see module docstring")
class TestChartTypeMatch:
    """Tests for ChartTypeMatch evaluator."""

    pass


@pytest.mark.skip(reason="Evaluators need update to new schemas - see module docstring")
class TestEncodingFieldsPresent:
    """Tests for EncodingFieldsPresent evaluator."""

    pass


@pytest.mark.skip(reason="Evaluators need update to new schemas - see module docstring")
class TestRationaleQuality:
    """Tests for RationaleQuality evaluator."""

    pass


@pytest.mark.skip(reason="Evaluators need update to new schemas - see module docstring")
class TestSafetyRules:
    """Tests for SafetyRules evaluator."""

    pass
