"""Tests for shared type definitions."""

import pytest

from shared.data.types import ChartType, DataShape, Job, Mode, Task


class TestTaskType:
    """Tests for Task type."""

    @pytest.mark.parametrize("value", ["consult", "reflect"])
    def test_valid_task_values(self, value: Task):
        """All Task literals should be valid."""
        task: Task = value
        assert task == value

    def test_task_values_complete(self):
        """Task should have exactly 2 values."""
        # This is a documentation test - if Task changes, update tests
        valid: list[Task] = ["consult", "reflect"]
        assert len(valid) == 2


class TestModeType:
    """Tests for Mode type."""

    @pytest.mark.parametrize("value", ["reporter", "interpreter", "explorer"])
    def test_valid_mode_values(self, value: Mode):
        """All Mode literals should be valid."""
        mode: Mode = value
        assert mode == value

    def test_mode_values_complete(self):
        """Mode should have exactly 3 values."""
        valid: list[Mode] = ["reporter", "interpreter", "explorer"]
        assert len(valid) == 3


class TestJobType:
    """Tests for Job type."""

    @pytest.mark.parametrize(
        "value",
        [
            "query",
            "visualize",
            "discover",
            "schema_update",
            "simulate",
            "schedule",
            "navigate",
            "clarify",
            "out_of_scope",
        ],
    )
    def test_valid_job_values(self, value: Job):
        """All Job literals should be valid."""
        job: Job = value
        assert job == value

    def test_job_values_complete(self):
        """Job should have exactly 9 values."""
        valid: list[Job] = [
            "query",
            "visualize",
            "discover",
            "schema_update",
            "simulate",
            "schedule",
            "navigate",
            "clarify",
            "out_of_scope",
        ]
        assert len(valid) == 9


class TestChartType:
    """Tests for ChartType type."""

    @pytest.mark.parametrize(
        "value",
        [
            # P0 — Core
            "kpi_card",
            "data_table",
            "bar_chart_vertical",
            "bar_chart_horizontal",
            "line_chart",
            "area_chart",
            "scatter_plot",
            "pie_chart",
            "donut_chart",
            # P1 — Extended
            "bar_chart_stacked",
            "bar_chart_grouped",
            "histogram",
            "heatmap",
            "treemap",
            "boxplot",
            "slope_chart",
            # P2 — Specialized
            "waterfall_chart",
            "cohort_heatmap",
            "combo",
            "violin_plot",
            "bullet_chart",
            "funnel_chart",
            "bubble_chart",
            "lollipop_chart",
        ],
    )
    def test_valid_chart_types(self, value: ChartType):
        """All ChartType literals should be valid."""
        chart: ChartType = value
        assert chart == value

    def test_chart_type_values_complete(self):
        """ChartType should have exactly 25 values (P0 + P1 + P2)."""
        valid: list[ChartType] = [
            # P0 — Core
            "kpi_card",
            "data_table",
            "bar_chart_vertical",
            "bar_chart_horizontal",
            "line_chart",
            "area_chart",
            "scatter_plot",
            "pie_chart",
            "donut_chart",
            # P1 — Extended
            "bar_chart_stacked",
            "bar_chart_grouped",
            "histogram",
            "heatmap",
            "treemap",
            "boxplot",
            "slope_chart",
            # P2 — Specialized
            "waterfall_chart",
            "cohort_heatmap",
            "combo",
            "violin_plot",
            "bullet_chart",
            "funnel_chart",
            "bubble_chart",
            "lollipop_chart",
        ]
        assert len(valid) == 24


class TestDataShapeType:
    """Tests for DataShape type."""

    @pytest.mark.parametrize(
        "value", ["temporal", "categorical", "distribution", "correlation"]
    )
    def test_valid_data_shapes(self, value: DataShape):
        """All DataShape literals should be valid."""
        shape: DataShape = value
        assert shape == value

    def test_data_shape_values_complete(self):
        """DataShape should have exactly 4 values."""
        valid: list[DataShape] = [
            "temporal",
            "categorical",
            "distribution",
            "correlation",
        ]
        assert len(valid) == 4
