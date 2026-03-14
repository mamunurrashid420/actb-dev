"""Experiment types for evaluation runs."""

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from evals.framework.prompt import ResolvedPrompt, resolve_prompt
from evals.framework.provenance import Provenance

if TYPE_CHECKING:
    from evals.framework.assertions.types import Assertion, AssertionResult
    from evals.framework.fixtures import ToolFixtures


@dataclass
class SingleRunResult:
    """Result of a single evaluation run."""

    run_index: int
    """Zero-based index of this run within the multi-run sequence."""

    output: Any
    """The output produced by the agent."""

    assertions: list["AssertionResult"]
    """Results of all assertions evaluated for this run."""

    passed: bool
    """True if all assertions passed."""

    duration_seconds: float
    """Execution time for this run in seconds."""

    tokens: int | None = None
    """Total tokens used (optional)."""


@dataclass
class MultiRunResult:
    """Aggregated result across multiple runs of the same test case.

    Supports non-deterministic agents by running the same test case N times
    and computing pass rate statistics.
    """

    case_name: str
    """Name of the test case that was run."""

    runs: list[SingleRunResult] = field(default_factory=list)
    """Individual run results."""

    @property
    def pass_count(self) -> int:
        """Number of runs that passed all assertions."""
        return sum(1 for r in self.runs if r.passed)

    @property
    def pass_rate(self) -> float:
        """Fraction of runs that passed (0.0 to 1.0)."""
        return self.pass_count / len(self.runs) if self.runs else 0.0

    @property
    def failures(self) -> list[SingleRunResult]:
        """Get all failed runs with their assertion details."""
        return [r for r in self.runs if not r.passed]

    @property
    def first_failure(self) -> SingleRunResult | None:
        """Get first failure for quick summary."""
        return self.failures[0] if self.failures else None

    @property
    def avg_duration(self) -> float:
        """Mean duration across runs."""
        return (
            statistics.mean(r.duration_seconds for r in self.runs) if self.runs else 0.0
        )

    @property
    def stddev_duration(self) -> float | None:
        """Standard deviation of duration (None if < 2 runs)."""
        if len(self.runs) < 2:
            return None
        return statistics.stdev(r.duration_seconds for r in self.runs)


@dataclass
class RunResult:
    """Result of a single experiment run."""

    id: UUID
    name: str
    provenance: Provenance
    model: str
    agent_type: str
    metrics: dict[str, dict]  # {"field_f1": {"task_f1": 0.85, ...}}
    summary: dict[str, float]  # {"success_rate": 0.85, "task_match": 0.82}
    total_cases: int
    failed_cases: int
    duration_seconds: float
    created_at: datetime
    results_path: str | None = None  # ".eval/results/{id}.parquet"
    tags: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.summary.get("success_rate", 0.0)

    def __str__(self) -> str:
        status = "dirty" if self.provenance.git_dirty else "clean"
        return (
            f"RunResult(name={self.name}, model={self.model}, "
            f"success_rate={self.success_rate:.1%}, "
            f"cases={self.total_cases}, failed={self.failed_cases}, "
            f"git={self.provenance.git_commit[:8]}[{status}])"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": str(self.id),
            "name": self.name,
            "agent_type": self.agent_type,
            "model": self.model,
            "metrics": self.metrics,
            "summary": self.summary,
            "total_cases": self.total_cases,
            "failed_cases": self.failed_cases,
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at.isoformat(),
            "results_path": self.results_path,
            "tags": self.tags,
            **self.provenance.to_dict(),
        }

    def print_summary(self) -> None:
        """Print formatted summary to stdout."""
        status = "dirty" if self.provenance.git_dirty else "clean"
        model_short = self.model.split(":")[-1] if ":" in self.model else self.model
        failed_str = f", {self.failed_cases} failed" if self.failed_cases > 0 else ""
        print(
            f"{model_short} ({self.total_cases} cases{failed_str}, {self.duration_seconds:.1f}s)"
        )
        print(f"  Git: {self.provenance.git_commit[:8]}[{status}]")

        # Extract classification fields from summary (exclude 'field' composite metric)
        fields = set()
        for key in self.summary:
            for suffix in ("_accuracy", "_f1", "_precision", "_recall"):
                if key.endswith(suffix):
                    field_name = key[: -len(suffix)]
                    if field_name != "field":  # Skip composite metric
                        fields.add(field_name)
                    break

        if fields:
            print(
                f"  {'Field':<8} | {'Accuracy':>8} | {'F1':>8} | {'Precision':>9} | {'Recall':>8}"
            )
            print(f"  {'-' * 8} | {'-' * 8} | {'-' * 8} | {'-' * 9} | {'-' * 8}")
            for field in sorted(fields):
                acc = self.summary.get(f"{field}_accuracy", 0)
                f1 = self.summary.get(f"{field}_f1", 0)
                prec = self.summary.get(f"{field}_precision", 0)
                rec = self.summary.get(f"{field}_recall", 0)
                print(
                    f"  {field:<8} | {acc:>8.1%} | {f1:>8.1%} | {prec:>9.1%} | {rec:>8.1%}"
                )

    def to_dataframe(self) -> "Any":
        """Convert to single-row DataFrame for analysis.

        Returns:
            pd.DataFrame with one row containing run metadata and metrics.

        Raises:
            ImportError: If pandas is not installed.
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas required: pip install pandas") from None
        return pd.DataFrame([self.to_dict()])


@dataclass
class Experiment:
    """Single experiment configuration."""

    agent: type  # Agent class (must have arun method)
    prompt: str  # Reference (py://...) or inline content
    model: str  # e.g., "google:gemini-3-flash-preview"
    dataset: list  # Test cases (pydantic_evals Case objects or wrappers)
    dataset_name: str = "unnamed"  # Name for provenance tracking
    metrics: list | None = None  # Evaluators (defaults to [exact_match()])
    name: str | None = None
    tags: list[str] = field(default_factory=list)

    # Assertion-based evaluation fields
    assertions: list["Assertion"] | None = None  # Experiment-level assertions
    fixtures: "ToolFixtures | None" = None  # Experiment-level fixtures

    # Cached resolved prompt
    _resolved_prompt: ResolvedPrompt | None = field(default=None, repr=False)

    def __post_init__(self):
        # Auto-generate name if not provided
        if self.name is None:
            agent_name = self.agent.__name__
            model_short = self.model.split(":")[-1] if ":" in self.model else self.model
            self.name = f"{agent_name}_{model_short}"

    @property
    def resolved_prompt(self) -> ResolvedPrompt:
        """Lazily resolve the prompt."""
        if self._resolved_prompt is None:
            self._resolved_prompt = resolve_prompt(self.prompt)
        return self._resolved_prompt

    def __str__(self) -> str:
        """Format experiment for display."""
        model_short = self.model.split(":")[-1] if ":" in self.model else self.model
        return f"{self.agent.__name__} | {model_short} | {self.dataset_name} ({len(self.dataset)} cases)"

    async def run(self, save: bool = True) -> RunResult:
        """Run this experiment.

        Args:
            save: If True, save results to local storage

        Returns:
            RunResult with metrics and provenance
        """
        from evals.framework.runner import EvalRunner

        runner = EvalRunner()
        return await runner.run(self, save=save)


@dataclass
class ExperimentSet:
    """Multiple experiments for comparison (e.g., A/B testing prompts)."""

    experiments: list[Experiment]
    name: str | None = None

    def __post_init__(self):
        if self.name is None and self.experiments:
            self.name = f"comparison_{len(self.experiments)}_experiments"

    def __str__(self) -> str:
        """Format experiment set for display."""
        lines = [f"{self.name} ({len(self.experiments)} experiments):"]
        for exp in self.experiments:
            model_short = exp.model.split(":")[-1] if ":" in exp.model else exp.model
            lines.append(f"  - {model_short}")
        return "\n".join(lines)

    async def run(self, save: bool = True) -> "ComparisonResult":
        """Run all experiments and return comparison."""
        from evals.framework.runner import EvalRunner

        runner = EvalRunner()
        results = []
        for exp in self.experiments:
            result = await runner.run(exp, save=save)
            results.append(result)

        return ComparisonResult(
            name=self.name or "unnamed_comparison",
            results=results,
        )


@dataclass
class ComparisonResult:
    """Result of running multiple experiments for comparison."""

    name: str
    results: list[RunResult]

    def best_by(self, metric: str = "success_rate") -> RunResult | None:
        """Get the best result by a given metric."""
        if not self.results:
            return None
        return max(self.results, key=lambda r: r.summary.get(metric, 0.0))

    def summary_table(self) -> list[dict[str, Any]]:
        """Generate summary table for all results."""
        rows = []
        for r in self.results:
            row = {
                "name": r.name,
                "model": r.model,
                "prompt_hash": r.provenance.prompt.hash,
                **r.summary,
                "duration_s": r.duration_seconds,
            }
            rows.append(row)
        return rows

    def print_comparison(self) -> None:
        """Print formatted comparison with per-model metrics."""
        if not self.results:
            print("No results to compare")
            return

        # Header
        print(f"\n{'=' * 60}")
        print(f"Comparison: {self.name}")
        print(f"{'=' * 60}")

        # Extract classification fields (exclude 'field' composite metric)
        fields = set()
        for r in self.results:
            for key in r.summary:
                for suffix in ("_accuracy", "_f1", "_precision", "_recall"):
                    if key.endswith(suffix):
                        field_name = key[: -len(suffix)]
                        if field_name != "field":  # Skip composite metric
                            fields.add(field_name)
                        break

        # Print each model's results
        for r in self.results:
            model_short = r.model.split(":")[-1] if ":" in r.model else r.model
            failed_str = f", {r.failed_cases} failed" if r.failed_cases > 0 else ""
            print(
                f"\n{model_short} ({r.total_cases} cases{failed_str}, {r.duration_seconds:.1f}s)"
            )

            if fields:
                print(
                    f"  {'Field':<8} | {'Accuracy':>8} | {'F1':>8} | {'Precision':>9} | {'Recall':>8}"
                )
                print(f"  {'-' * 8} | {'-' * 8} | {'-' * 8} | {'-' * 9} | {'-' * 8}")
                for field in sorted(fields):
                    acc = r.summary.get(f"{field}_accuracy", 0)
                    f1 = r.summary.get(f"{field}_f1", 0)
                    prec = r.summary.get(f"{field}_precision", 0)
                    rec = r.summary.get(f"{field}_recall", 0)
                    print(
                        f"  {field:<8} | {acc:>8.1%} | {f1:>8.1%} | {prec:>9.1%} | {rec:>8.1%}"
                    )

    def to_dataframe(self) -> "Any":
        """Convert results to DataFrame.

        Returns:
            pd.DataFrame with one row per result.

        Raises:
            ImportError: If pandas is not installed.
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas required: pip install pandas") from None
        return pd.DataFrame(self.summary_table())

    def plot_metrics(
        self, fields: list[str] | None = None, title: str | None = None
    ) -> "Any":
        """Bar chart comparing per-field match rates across models.

        Args:
            fields: Metrics to plot (defaults to all *_match fields).
            title: Chart title (defaults to comparison name).

        Returns:
            matplotlib Figure, or None if no results.

        Raises:
            ImportError: If matplotlib is not installed.
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            raise ImportError("matplotlib required: pip install matplotlib") from None

        if not self.results:
            print("No results to plot")
            return None

        # Auto-detect fields ending in _match if not specified
        if fields is None:
            fields = sorted(k for k in self.results[0].summary if k.endswith("_match"))

        models = [r.model.split(":")[-1] for r in self.results]
        x = np.arange(len(models))
        width = 0.8 / len(fields)

        fig, ax = plt.subplots(figsize=(10, 6))
        for i, field_name in enumerate(fields):
            scores = [r.summary.get(field_name, 0) for r in self.results]
            offset = (i - len(fields) / 2 + 0.5) * width
            ax.bar(
                x + offset, scores, width, label=field_name.replace("_", " ").title()
            )

        ax.set_ylabel("Score")
        ax.set_title(title or f"Model Comparison: {self.name}")
        ax.set_xticks(x)
        ax.set_xticklabels(models, rotation=45, ha="right")
        ax.legend()
        ax.set_ylim(0, 1.0)
        plt.tight_layout()
        return fig

    def plot_speed_accuracy(
        self, metric: str = "success_rate", title: str | None = None
    ) -> "Any":
        """Scatter plot of speed vs accuracy tradeoff.

        Args:
            metric: Metric to use for y-axis (defaults to success_rate).
            title: Chart title (defaults to comparison name).

        Returns:
            matplotlib Figure, or None if no results.

        Raises:
            ImportError: If matplotlib is not installed.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("matplotlib required: pip install matplotlib") from None

        if not self.results:
            print("No results to plot")
            return None

        models = [r.model.split(":")[-1] for r in self.results]
        scores = [r.summary.get(metric, 0) for r in self.results]
        durations = [r.duration_seconds for r in self.results]

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(durations, scores, s=100)

        for i, model in enumerate(models):
            ax.annotate(
                model,
                (durations[i], scores[i]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=9,
            )

        ax.set_xlabel("Duration (seconds)")
        ax.set_ylabel(metric.replace("_", " ").title())
        ax.set_title(title or f"Speed vs Accuracy: {self.name}")
        plt.tight_layout()
        return fig
