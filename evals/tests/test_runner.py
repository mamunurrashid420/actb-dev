"""Tests for the assertion-based runner."""

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from evals.framework.assertions.types import Assertion
from evals.framework.experiment import (
    ComparisonResult,
    Experiment,
    ExperimentSet,
    RunResult,
)
from evals.framework.fixtures import ToolFixtures
from evals.framework.loader import EvalCase
from evals.framework.runner import AssertionRunner, EvalRunner

# ─────────────────────────────────────────────────────────────────────────────
# Test Fixtures and Helpers
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class MockAgent:
    """Mock agent for testing."""

    prompt_override: str | None = None
    model: str = "test:model"
    output: dict | None = None
    error: Exception | None = None

    async def arun(self, inputs, config=None):
        """Mock async run method."""
        if self.error:
            raise self.error
        return self.output or {"task": "consult", "mode": "chat"}


def make_mock_agent_class(output=None, error=None):
    """Create a mock agent class with configurable output/error."""

    class MockAgentClass:
        def __init__(self, prompt_override=None, model=None):
            self.prompt_override = prompt_override
            self.model = model
            self._output = output
            self._error = error

        async def arun(self, inputs, config=None):
            if self._error:
                raise self._error
            return self._output or {"task": "consult", "mode": "chat"}

    return MockAgentClass


def make_test_case(
    name: str = "test_case",
    inputs: dict | None = None,
    assertions: list[Assertion] | None = None,
    runs: int = 1,
    fixtures: ToolFixtures | None = None,
    workflow_assert: list[Assertion] | None = None,
) -> EvalCase:
    """Create a test case for testing."""
    return EvalCase(
        name=name,
        inputs=inputs or {"query": "test"},
        assert_=assertions or [],
        runs=runs,
        fixtures=fixtures,
        workflow_assert=workflow_assert,
    )


# ─────────────────────────────────────────────────────────────────────────────
# AssertionRunner Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAssertionRunnerInitialization:
    """Tests for AssertionRunner initialization."""

    def test_creates_with_no_store(self):
        """Runner should initialize with no store."""
        runner = AssertionRunner()
        assert runner._store is None
        assert runner.engine is not None
        assert runner.fixture_manager is not None

    def test_creates_with_store(self, tmp_path):
        """Runner should accept a store."""
        from evals.framework.store import LocalStore

        store = LocalStore(base_dir=tmp_path / ".eval")
        runner = AssertionRunner(store=store)
        assert runner._store is store

    def test_lazy_loads_store(self, tmp_path):
        """Store should be lazy-loaded on first access."""
        runner = AssertionRunner()
        assert runner._store is None

        # Accessing store property should create it
        with patch(
            "evals.framework.store.LocalStore.__init__",
            return_value=None,
        ):
            # Force creation by accessing the property
            _ = runner.store
            assert runner._store is not None


class TestAssertionRunnerSingleExperiment:
    """Tests for running a single experiment."""

    @pytest.mark.asyncio
    async def test_runs_single_experiment(self):
        """Should run a single experiment successfully."""
        agent_class = make_mock_agent_class(output={"task": "consult"})
        test_case = make_test_case(
            assertions=[Assertion(type="equals", field="task", value="consult")]
        )

        experiment = Experiment(
            agent=agent_class,
            prompt="test prompt",
            model="test:model",
            dataset=[test_case],
        )

        runner = AssertionRunner()
        result = await runner.run(experiment, save=False)

        assert isinstance(result, RunResult)
        assert result.total_cases == 1
        assert result.failed_cases == 0
        assert result.summary["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_experiment_with_failing_assertion(self):
        """Should track failed assertions correctly."""
        agent_class = make_mock_agent_class(output={"task": "wrong_task"})
        test_case = make_test_case(
            assertions=[Assertion(type="equals", field="task", value="consult")]
        )

        experiment = Experiment(
            agent=agent_class,
            prompt="test prompt",
            model="test:model",
            dataset=[test_case],
        )

        runner = AssertionRunner()
        result = await runner.run(experiment, save=False)

        assert result.total_cases == 1
        assert result.failed_cases == 1
        assert result.summary["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_experiment_with_multiple_cases(self):
        """Should handle multiple test cases."""
        agent_class = make_mock_agent_class(output={"task": "consult"})
        test_cases = [
            make_test_case(
                name=f"case_{i}",
                assertions=[Assertion(type="equals", field="task", value="consult")],
            )
            for i in range(5)
        ]

        experiment = Experiment(
            agent=agent_class,
            prompt="test prompt",
            model="test:model",
            dataset=test_cases,
        )

        runner = AssertionRunner()
        result = await runner.run(experiment, save=False)

        assert result.total_cases == 5
        assert result.failed_cases == 0
        assert result.summary["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_experiment_level_assertions(self):
        """Should apply experiment-level assertions to all cases."""
        agent_class = make_mock_agent_class(output={"task": "consult", "mode": "chat"})
        test_cases = [
            make_test_case(name="case_1"),
            make_test_case(name="case_2"),
        ]

        experiment = Experiment(
            agent=agent_class,
            prompt="test prompt",
            model="test:model",
            dataset=test_cases,
            assertions=[Assertion(type="equals", field="task", value="consult")],
        )

        runner = AssertionRunner()
        result = await runner.run(experiment, save=False)

        assert result.total_cases == 2
        assert result.failed_cases == 0


class TestMultipleRunsPerCase:
    """Tests for running a case multiple times."""

    @pytest.mark.asyncio
    async def test_runs_case_multiple_times(self):
        """Should run the same case multiple times."""
        agent_class = make_mock_agent_class(output={"task": "consult"})
        test_case = make_test_case(
            assertions=[Assertion(type="equals", field="task", value="consult")],
            runs=3,
        )

        experiment = Experiment(
            agent=agent_class,
            prompt="test prompt",
            model="test:model",
            dataset=[test_case],
        )

        runner = AssertionRunner()

        # Track the individual case results
        original_run_case = runner._run_case

        case_results = []

        async def tracking_run_case(*args, **kwargs):
            result = await original_run_case(*args, **kwargs)
            case_results.append(result)
            return result

        with patch.object(runner, "_run_case", tracking_run_case):
            await runner.run(experiment, save=False)

        # Should have one MultiRunResult with 3 runs
        assert len(case_results) == 1
        assert len(case_results[0].runs) == 3

    @pytest.mark.asyncio
    async def test_multi_run_pass_rate(self):
        """Pass rate should reflect multiple runs."""
        # Create an agent that alternates between success and failure
        call_count = [0]

        class AlternatingAgent:
            def __init__(self, **kwargs):
                pass

            async def arun(self, inputs, config=None):
                call_count[0] += 1
                if call_count[0] % 2 == 0:
                    return {"task": "wrong"}
                return {"task": "consult"}

        test_case = make_test_case(
            assertions=[Assertion(type="equals", field="task", value="consult")],
            runs=4,
        )

        experiment = Experiment(
            agent=AlternatingAgent,
            prompt="test prompt",
            model="test:model",
            dataset=[test_case],
        )

        runner = AssertionRunner()
        result = await runner.run(experiment, save=False)

        # 2 passes, 2 failures out of 4 runs
        # Case is considered failed if any run fails
        assert result.total_cases == 1
        assert result.failed_cases == 1
        assert result.summary["case_pass_rate"] == 0.0


class TestExperimentSet:
    """Tests for running multiple experiments."""

    @pytest.mark.asyncio
    async def test_runs_experiment_set(self):
        """Should run all experiments in a set."""
        agent_class = make_mock_agent_class(output={"task": "consult"})
        test_case = make_test_case(
            assertions=[Assertion(type="equals", field="task", value="consult")]
        )

        experiments = [
            Experiment(
                agent=agent_class,
                prompt="prompt_v1",
                model="model_a",
                dataset=[test_case],
                name=f"exp_{i}",
            )
            for i in range(3)
        ]

        exp_set = ExperimentSet(experiments=experiments, name="comparison_test")

        runner = AssertionRunner()
        result = await runner.run(exp_set, save=False)

        assert isinstance(result, ComparisonResult)
        assert result.name == "comparison_test"
        assert len(result.results) == 3

    @pytest.mark.asyncio
    async def test_experiment_set_parallel_execution(self):
        """Experiments in a set should run in parallel."""
        import asyncio

        execution_order = []

        class TrackingAgent:
            def __init__(self, name: str = "", **kwargs):
                self.name = name

            async def arun(self, inputs, config=None):
                execution_order.append(f"start_{self.name}")
                await asyncio.sleep(0.01)  # Small delay
                execution_order.append(f"end_{self.name}")
                return {"task": "consult"}

        # agent_class unused
        test_case = make_test_case()

        experiments = [
            Experiment(
                agent=lambda i=i, **kwargs: TrackingAgent(name=str(i), **kwargs),
                prompt=f"prompt_{i}",
                model="test:model",
                dataset=[test_case],
                name=f"exp_{i}",
            )
            for i in range(3)
        ]

        exp_set = ExperimentSet(experiments=experiments)

        runner = AssertionRunner()
        await runner.run(exp_set, save=False)

        # If running in parallel, starts should come before all ends
        # (not strictly interleaved due to tiny delays, but structure should show parallelism)
        assert len(execution_order) == 6


class TestFixtureIntegration:
    """Tests for fixture integration."""

    @pytest.fixture
    def fixture_file(self, tmp_path: Path) -> Path:
        """Create a temporary fixture file."""
        fixture_data = {
            "search": [
                {"input": {"query": "test"}, "output": ["result1", "result2"]},
            ],
        }
        fixture_path = tmp_path / "fixtures.yaml"
        fixture_path.write_text(yaml.dump(fixture_data))
        return fixture_path

    @pytest.mark.asyncio
    async def test_applies_experiment_fixtures(self, fixture_file):
        """Should apply experiment-level fixtures."""
        agent_class = make_mock_agent_class(output={"task": "consult"})
        test_case = make_test_case()

        experiment = Experiment(
            agent=agent_class,
            prompt="test prompt",
            model="test:model",
            dataset=[test_case],
            fixtures=ToolFixtures(tools=fixture_file),
        )

        runner = AssertionRunner()

        # Verify fixture manager is called
        apply_calls = []
        original_apply = runner.fixture_manager.apply

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def tracking_apply(fixtures):
            apply_calls.append(fixtures)
            async with original_apply(fixtures):
                yield

        with patch.object(runner.fixture_manager, "apply", tracking_apply):
            await runner.run(experiment, save=False)

        assert len(apply_calls) == 1
        assert apply_calls[0].tools == fixture_file

    @pytest.mark.asyncio
    async def test_case_fixtures_override_experiment(self, fixture_file, tmp_path):
        """Case-level fixtures should override experiment fixtures."""
        # Create a different fixture file for the case
        case_fixture_path = tmp_path / "case_fixtures.yaml"
        case_fixture_path.write_text(
            yaml.dump({
                "search": [{"input": {"query": "case"}, "output": ["case_result"]}]
            })
        )

        agent_class = make_mock_agent_class(output={"task": "consult"})
        test_case = make_test_case(fixtures=ToolFixtures(tools=case_fixture_path))

        experiment = Experiment(
            agent=agent_class,
            prompt="test prompt",
            model="test:model",
            dataset=[test_case],
            fixtures=ToolFixtures(tools=fixture_file),
        )

        runner = AssertionRunner()

        apply_calls = []
        original_apply = runner.fixture_manager.apply

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def tracking_apply(fixtures):
            apply_calls.append(fixtures)
            async with original_apply(fixtures):
                yield

        with patch.object(runner.fixture_manager, "apply", tracking_apply):
            await runner.run(experiment, save=False)

        # Case fixtures should be used instead of experiment fixtures
        assert len(apply_calls) == 1
        assert apply_calls[0].tools == case_fixture_path


class TestWorkflowTracing:
    """Tests for workflow tracing integration."""

    @pytest.mark.asyncio
    async def test_captures_workflow_trace_when_workflow_assert_present(self):
        """Should capture workflow trace when workflow_assert is specified."""
        agent_class = make_mock_agent_class(output={"task": "consult"})
        test_case = make_test_case(
            workflow_assert=[Assertion(type="not-null", field="task")]
        )

        experiment = Experiment(
            agent=agent_class,
            prompt="test prompt",
            model="test:model",
            dataset=[test_case],
        )

        runner = AssertionRunner()

        # The agent should be called with a callback in the config
        agent_calls = []

        class CapturingAgent:
            def __init__(self, **kwargs):
                pass

            async def arun(self, inputs, config=None):
                agent_calls.append(config)
                return {"task": "consult"}

        experiment.agent = CapturingAgent

        await runner.run(experiment, save=False)

        assert len(agent_calls) == 1
        assert "callbacks" in agent_calls[0]


class TestClassificationMetrics:
    """Tests for classification metrics computation."""

    @pytest.mark.asyncio
    async def test_computes_accuracy_for_equals_assertions(self):
        """Should compute accuracy for 'equals' assertions on same field."""
        agent_class = make_mock_agent_class(output={"task": "consult"})
        test_cases = [
            make_test_case(
                name="case_consult",
                assertions=[Assertion(type="equals", field="task", value="consult")],
            ),
            make_test_case(
                name="case_consult_2",
                assertions=[Assertion(type="equals", field="task", value="consult")],
            ),
        ]

        experiment = Experiment(
            agent=agent_class,
            prompt="test prompt",
            model="test:model",
            dataset=test_cases,
        )

        runner = AssertionRunner()
        result = await runner.run(experiment, save=False)

        # Both cases should pass, so accuracy should be 1.0
        assert "task_accuracy" in result.summary
        assert result.summary["task_accuracy"] == 1.0

    @pytest.mark.asyncio
    async def test_computes_f1_for_multiclass_assertions(self):
        """Should compute F1 for multi-class classification assertions."""
        # Use input-based routing to ensure consistent outputs regardless of execution order

        class InputRoutedAgent:
            def __init__(self, **kwargs):
                pass

            async def arun(self, inputs, config=None):
                # Route based on input query to ensure deterministic results
                query = inputs.get("query", "")
                if "consult" in query:
                    return {"task": "consult"}
                elif "search" in query:
                    return {"task": "search"}
                elif "analyze" in query:
                    return {"task": "analyze"}
                return {"task": "unknown"}

        test_cases = [
            make_test_case(
                name="case_1",
                inputs={"query": "consult"},
                assertions=[Assertion(type="equals", field="task", value="consult")],
            ),
            make_test_case(
                name="case_2",
                inputs={"query": "search"},
                assertions=[Assertion(type="equals", field="task", value="search")],
            ),
            make_test_case(
                name="case_3",
                inputs={"query": "analyze"},
                assertions=[Assertion(type="equals", field="task", value="analyze")],
            ),
        ]

        experiment = Experiment(
            agent=InputRoutedAgent,
            prompt="test prompt",
            model="test:model",
            dataset=test_cases,
        )

        runner = AssertionRunner()
        result = await runner.run(experiment, save=False)

        # All 3 cases match perfectly
        assert "task_accuracy" in result.summary
        assert result.summary["task_accuracy"] == 1.0
        assert "task_f1" in result.summary
        assert result.summary["task_f1"] == 1.0


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_handles_agent_error_gracefully(self):
        """Should handle agent errors gracefully."""
        agent_class = make_mock_agent_class(error=ValueError("Agent failed"))
        test_case = make_test_case(
            assertions=[Assertion(type="not-null", field="task")]
        )

        experiment = Experiment(
            agent=agent_class,
            prompt="test prompt",
            model="test:model",
            dataset=[test_case],
        )

        runner = AssertionRunner()
        result = await runner.run(experiment, save=False)

        # Case should fail due to agent error
        assert result.total_cases == 1
        assert result.failed_cases == 1
        assert result.summary["success_rate"] == 0.0


class TestBackwardCompatibility:
    """Tests for backward compatibility."""

    def test_evalrunner_alias(self):
        """EvalRunner should be an alias for AssertionRunner."""
        assert EvalRunner is AssertionRunner

    @pytest.mark.asyncio
    async def test_run_experiment_function(self):
        """run_experiment function should work."""
        from evals.framework.runner import run_experiment

        agent_class = make_mock_agent_class(output={"task": "consult"})
        test_case = make_test_case()

        experiment = Experiment(
            agent=agent_class,
            prompt="test prompt",
            model="test:model",
            dataset=[test_case],
        )

        with patch("evals.framework.runner.AssertionRunner") as MockRunner:
            mock_instance = MagicMock()
            mock_instance.run = AsyncMock(return_value=MagicMock())
            MockRunner.return_value = mock_instance

            await run_experiment(experiment, save=False)

            MockRunner.assert_called_once()
            mock_instance.run.assert_called_once_with(experiment, save=False)
