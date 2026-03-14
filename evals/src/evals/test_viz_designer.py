"""Integration tests for VisualizationDesigner agent.

These tests make real LLM calls and require an API key.
Run with: pytest evals/ -v -m integration
"""

import pytest
from pydantic_evals import Dataset

from evals.datasets.viz_designer import ALL_CASES
from evals.evaluators.viz import SafetyRules
from evals.metrics import success_rate


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_chart_selection(agent, basic_dataset):
    """All basic cases should pass with high success rate."""
    report = await basic_dataset.evaluate(agent.arun)
    report.print(include_input=True, include_output=True)
    rate = success_rate(report)
    assert rate >= 0.9, f"Success rate: {rate}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_safety_rules(agent):
    """All outputs must pass safety validation."""
    dataset = Dataset(cases=ALL_CASES, evaluators=[SafetyRules()])
    report = await dataset.evaluate(agent.arun)
    rate = success_rate(report)
    assert rate == 1.0, f"Safety violations detected. Success rate: {rate}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_single_case_temporal(agent):
    """Test a single temporal trend case."""
    from evals.datasets.viz_designer import TEMPORAL_TREND

    result = await agent.arun(TEMPORAL_TREND.inputs)
    assert result.chart_type == "line_chart", (
        f"Expected line_chart, got {result.chart_type}"
    )
    assert "date" in [result.encoding.x, result.encoding.y]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_single_case_categorical(agent):
    """Test a single categorical comparison case."""
    from evals.datasets.viz_designer import CATEGORICAL_COMPARISON

    result = await agent.arun(CATEGORICAL_COMPARISON.inputs)
    assert result.chart_type == "bar_chart_vertical", (
        f"Expected bar_chart_vertical, got {result.chart_type}"
    )
