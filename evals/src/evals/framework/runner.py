"""Assertion-based experiment runner.

Replaces pydantic-evals Dataset.evaluate() with our own async runner that uses:
- AssertionEngine for evaluating assertions
- FixtureManager for applying test fixtures
- WorkflowTraceCallback for capturing workflow traces

Rate limiting is handled by LLMClient (per-provider InMemoryRateLimiter),
so the runner doesn't manage concurrency - all tasks run in parallel and
rate limiters handle pacing.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from tqdm.auto import tqdm

from evals.framework.assertions import AssertionEngine, AssertionResult, EvalContext
from evals.framework.assertions.types import Assertion
from evals.framework.experiment import (
    ComparisonResult,
    Experiment,
    ExperimentSet,
    MultiRunResult,
    RunResult,
    SingleRunResult,
)
from evals.framework.fixtures import FixtureManager, ToolFixtures
from evals.framework.provenance import Provenance
from evals.framework.workflow import WorkflowTraceCallback

if TYPE_CHECKING:
    from evals.framework.store import LocalStore


class AssertionRunner:
    """Runs experiments using assertion-based evaluation.

    This runner replaces pydantic-evals with our own async evaluation system.
    Key features:
    - Uses AssertionEngine for flexible assertion evaluation
    - Supports fixture-based mocking via FixtureManager
    - Captures workflow traces for workflow-level assertions
    - Runs experiments in parallel (rate limiting handled by LLMClient)
    - Provides tqdm progress bars for real-time feedback
    """

    def __init__(self, store: LocalStore | None = None):
        """Initialize runner.

        Args:
            store: Optional LocalStore for persisting results.
        """
        self.engine = AssertionEngine()
        self.fixture_manager = FixtureManager()
        self._store = store

    @property
    def store(self) -> LocalStore:
        """Lazy-load store to avoid circular imports."""
        if self._store is None:
            from evals.framework.store import LocalStore

            self._store = LocalStore()
        return self._store

    async def run(
        self,
        target: Experiment | ExperimentSet,
        save: bool = True,
    ) -> RunResult | ComparisonResult:
        """Run an experiment or experiment set.

        Args:
            target: Single Experiment or ExperimentSet to run.
            save: If True, persist results to local storage.

        Returns:
            RunResult for single experiment, ComparisonResult for set.
        """
        if isinstance(target, ExperimentSet):
            return await self._run_set(target, save)
        return await self._run_experiment(target, save)

    async def _run_set(self, exp_set: ExperimentSet, save: bool) -> ComparisonResult:
        """Run all experiments in parallel.

        Rate limiting is handled by LLMClient, so we launch all experiments
        at once and let the rate limiters manage pacing.
        """
        tasks = [self._run_experiment(exp, save) for exp in exp_set.experiments]
        results = []

        # Use asyncio.as_completed for real-time progress updates
        for coro in tqdm(
            asyncio.as_completed(tasks),
            total=len(tasks),
            desc="Experiments",
            unit="exp",
        ):
            result = await coro
            results.append(result)

        return ComparisonResult(
            name=exp_set.name or "unnamed_comparison",
            results=results,
        )

    async def _run_experiment(self, experiment: Experiment, save: bool) -> RunResult:
        """Run a single experiment with all its test cases."""
        start_time = time.time()

        # Resolve prompt and capture provenance
        resolved_prompt = experiment.resolved_prompt
        provenance = Provenance.capture(
            prompt=resolved_prompt,
            dataset_name=experiment.dataset_name,
            cases=experiment.dataset,
        )

        # Instantiate agent with prompt override
        agent = experiment.agent(
            prompt_override=resolved_prompt.content,
            model=experiment.model,
        )

        # Get experiment-level assertions and fixtures
        exp_assertions = getattr(experiment, "assertions", None) or []
        exp_fixtures = getattr(experiment, "fixtures", None)

        # Create tasks for all test cases
        tasks = [
            self._run_case(agent, case, exp_assertions, exp_fixtures)
            for case in experiment.dataset
        ]

        # Run all cases in parallel with progress bar
        case_results: list[MultiRunResult] = []
        for coro in tqdm(
            asyncio.as_completed(tasks),
            total=len(tasks),
            desc=experiment.name or "Experiment",
            unit="case",
        ):
            result = await coro
            case_results.append(result)

        duration = time.time() - start_time

        # Aggregate results and create RunResult
        result = self._aggregate(experiment, case_results, provenance, duration)

        # Save if requested
        if save:
            self.store.save_assertion_result(result, case_results)

        return result

    async def _run_case(
        self,
        agent: Any,
        case: Any,
        exp_assertions: list[Assertion],
        exp_fixtures: ToolFixtures | None,
    ) -> MultiRunResult:
        """Run a single test case (potentially multiple times).

        Supports the `runs` field on cases for non-deterministic agent testing.
        """
        # Get case name
        case_name = getattr(case, "name", str(case))

        # Merge fixtures (case overrides experiment)
        case_fixtures = getattr(case, "fixtures", None)
        fixtures = self._merge_fixtures(exp_fixtures, case_fixtures)

        # Merge assertions (case adds to experiment)
        case_assertions = getattr(case, "assert_", None) or []
        if hasattr(case, "assertions"):
            case_assertions = case.assertions or []
        assertions = exp_assertions + case_assertions

        # Get workflow assertions if present
        workflow_assertions = getattr(case, "workflow_assert", None) or []

        # Determine number of runs (default 1)
        num_runs = getattr(case, "runs", 1) or 1

        # Execute all runs
        runs: list[SingleRunResult] = []
        for run_idx in range(num_runs):
            result = await self._execute_run(
                agent, case, assertions, workflow_assertions, fixtures, run_idx
            )
            runs.append(result)

        return MultiRunResult(case_name=case_name, runs=runs)

    async def _execute_run(
        self,
        agent: Any,
        case: Any,
        assertions: list[Assertion],
        workflow_assertions: list[Assertion],
        fixtures: ToolFixtures | None,
        run_idx: int,
    ) -> SingleRunResult:
        """Execute one run with fixtures and optional workflow tracing."""
        start = time.time()
        output = None
        trace = None
        error: Exception | None = None

        # Get inputs from case
        inputs = getattr(case, "inputs", case)
        if hasattr(inputs, "model_dump"):
            inputs = inputs.model_dump()

        try:
            async with self.fixture_manager.apply(fixtures):
                if workflow_assertions:
                    # Use workflow callback for tracing
                    callback = WorkflowTraceCallback()
                    output = await agent.arun(inputs, config={"callbacks": [callback]})
                    trace = callback.trace
                else:
                    output = await agent.arun(inputs)
        except Exception as e:
            error = e

        duration = time.time() - start

        # Build evaluation context
        ctx = EvalContext(duration_seconds=duration, trace=trace)

        # Evaluate assertions
        if error:
            # All assertions fail on error
            assertion_results = [
                AssertionResult(
                    assertion=a,
                    passed=False,
                    actual_value=None,
                    message=f"Agent error: {error}",
                )
                for a in assertions
            ]
        else:
            assertion_results = self.engine.evaluate_all(output, assertions, ctx)

        # Add workflow assertions if present and no error
        if workflow_assertions and not error:
            workflow_results = self.engine.evaluate_all(
                output, workflow_assertions, ctx
            )
            assertion_results.extend(workflow_results)

        return SingleRunResult(
            run_index=run_idx,
            output=output,
            assertions=assertion_results,
            passed=all(r.passed for r in assertion_results),
            duration_seconds=duration,
        )

    def _merge_fixtures(
        self,
        exp_fixtures: ToolFixtures | None,
        case_fixtures: ToolFixtures | None,
    ) -> ToolFixtures | None:
        """Merge fixtures - case overrides experiment."""
        if case_fixtures is not None:
            return case_fixtures
        return exp_fixtures

    def _aggregate(
        self,
        experiment: Experiment,
        case_results: list[MultiRunResult],
        provenance: Provenance,
        duration: float,
    ) -> RunResult:
        """Aggregate case results into a RunResult with metrics."""
        total_cases = len(case_results)

        # Count cases where all runs passed
        passed_cases = sum(1 for mr in case_results if all(r.passed for r in mr.runs))
        failed_cases = total_cases - passed_cases

        # Compute pass rates
        case_pass_rate = passed_cases / total_cases if total_cases > 0 else 0.0

        # Compute assertion-level pass rate
        all_assertions = []
        for mr in case_results:
            for run in mr.runs:
                all_assertions.extend(run.assertions)

        assertion_pass_rate = (
            sum(1 for a in all_assertions if a.passed) / len(all_assertions)
            if all_assertions
            else 0.0
        )

        # Compute classification metrics for 'equals' assertions
        classification_metrics = self._compute_classification_metrics(case_results)

        # Build summary
        summary: dict[str, float] = {
            "success_rate": case_pass_rate,
            "case_pass_rate": case_pass_rate,
            "assertion_pass_rate": assertion_pass_rate,
            **classification_metrics,
        }

        # Build metrics dict (detailed per-field metrics)
        metrics: dict[str, dict] = {}
        for field, field_metrics in classification_metrics.items():
            if isinstance(field_metrics, dict):
                metrics[field] = field_metrics

        result_id = uuid4()
        return RunResult(
            id=result_id,
            name=experiment.name or "unnamed",
            provenance=provenance,
            model=experiment.model,
            agent_type=experiment.agent.__name__,
            metrics=metrics,
            summary=summary,
            total_cases=total_cases,
            failed_cases=failed_cases,
            duration_seconds=duration,
            created_at=datetime.now(),
            tags=experiment.tags,
        )

    def _compute_classification_metrics(
        self, case_results: list[MultiRunResult]
    ) -> dict[str, float]:
        """Compute classification metrics for 'equals' assertions.

        Groups assertions by field and computes accuracy, F1, precision, recall
        for fields that have multiple test cases.
        """
        # Collect expected/actual pairs by field
        field_labels: dict[str, dict[str, list[Any]]] = defaultdict(
            lambda: {"expected": [], "actual": []}
        )

        for mr in case_results:
            for run in mr.runs:
                for assertion_result in run.assertions:
                    assertion = assertion_result.assertion
                    if assertion.type == "equals" and assertion.field:
                        field = assertion.field
                        expected = assertion.value
                        actual = assertion_result.actual_value
                        field_labels[field]["expected"].append(str(expected))
                        field_labels[field]["actual"].append(str(actual))

        # Compute metrics per field
        metrics: dict[str, float] = {}
        for field, labels in field_labels.items():
            expected = labels["expected"]
            actual = labels["actual"]

            if len(expected) < 2:
                # Not enough data for classification metrics
                continue

            # Compute accuracy
            accuracy = accuracy_score(expected, actual)
            metrics[f"{field}_accuracy"] = float(accuracy)

            # Get unique labels
            unique_labels = list(set(expected) | set(actual))

            if len(unique_labels) > 1:
                # Compute F1, precision, recall for multi-class
                try:
                    f1 = f1_score(
                        expected,
                        actual,
                        labels=unique_labels,
                        average="weighted",
                        zero_division=0.0,
                    )
                    precision = precision_score(
                        expected,
                        actual,
                        labels=unique_labels,
                        average="weighted",
                        zero_division=0.0,
                    )
                    recall = recall_score(
                        expected,
                        actual,
                        labels=unique_labels,
                        average="weighted",
                        zero_division=0.0,
                    )
                    metrics[f"{field}_f1"] = float(f1)
                    metrics[f"{field}_precision"] = float(precision)
                    metrics[f"{field}_recall"] = float(recall)
                except ValueError:
                    pass

        return metrics


# Backward compatibility alias
EvalRunner = AssertionRunner


async def run_experiment(
    experiment: Experiment,
    save: bool = True,
) -> RunResult:
    """Convenience function to run a single experiment."""
    runner = AssertionRunner()
    return await runner.run(experiment, save=save)
