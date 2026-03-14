"""Tests for Experiment and ExperimentSet configuration."""

from unittest.mock import MagicMock

from evals.framework.experiment import Experiment, ExperimentSet


class TestExperiment:
    """Tests for Experiment configuration."""

    def test_auto_generates_name(self):
        """Experiment should auto-generate name from agent and model."""
        exp = Experiment(
            agent=MagicMock,
            prompt="test prompt",
            model="google:gemini-flash",
            dataset=[],
        )

        assert "MagicMock" in exp.name
        assert "gemini-flash" in exp.name

    def test_custom_name_used(self):
        """Custom name should override auto-generated name."""
        exp = Experiment(
            agent=MagicMock,
            prompt="test prompt",
            model="google:gemini-flash",
            dataset=[],
            name="my_custom_experiment",
        )

        assert exp.name == "my_custom_experiment"

    def test_resolved_prompt_cached(self):
        """Resolved prompt should be cached on first access."""
        exp = Experiment(
            agent=MagicMock,
            prompt="test prompt",
            model="google:gemini-flash",
            dataset=[],
        )

        resolved1 = exp.resolved_prompt
        resolved2 = exp.resolved_prompt

        assert resolved1 is resolved2

    def test_accepts_py_prompt_reference(self):
        """Should accept py:// prompt references."""
        exp = Experiment(
            agent=MagicMock,
            prompt="py://agents.intent_classifier.agent:DEFAULT_PROMPT",
            model="google:gemini-flash",
            dataset=[],
        )

        assert "IntentClassifier" in exp.resolved_prompt.content


class TestExperimentSet:
    """Tests for ExperimentSet configuration."""

    def test_auto_generates_name(self):
        """ExperimentSet should auto-generate name from experiment count."""
        exp1 = Experiment(agent=MagicMock, prompt="p1", model="m1", dataset=[])
        exp2 = Experiment(agent=MagicMock, prompt="p2", model="m2", dataset=[])

        exp_set = ExperimentSet(experiments=[exp1, exp2])

        assert "2" in exp_set.name

    def test_custom_name_used(self):
        """Custom name should override auto-generated name."""
        exp1 = Experiment(agent=MagicMock, prompt="p1", model="m1", dataset=[])
        exp2 = Experiment(agent=MagicMock, prompt="p2", model="m2", dataset=[])

        exp_set = ExperimentSet(
            experiments=[exp1, exp2],
            name="my_experiment_set",
        )

        assert exp_set.name == "my_experiment_set"

    def test_experiments_accessible(self):
        """Experiments should be accessible from set."""
        exp1 = Experiment(
            agent=MagicMock, prompt="p1", model="m1", dataset=[], name="exp1"
        )
        exp2 = Experiment(
            agent=MagicMock, prompt="p2", model="m2", dataset=[], name="exp2"
        )

        exp_set = ExperimentSet(experiments=[exp1, exp2])

        assert len(exp_set.experiments) == 2
        assert exp_set.experiments[0].name == "exp1"
        assert exp_set.experiments[1].name == "exp2"
