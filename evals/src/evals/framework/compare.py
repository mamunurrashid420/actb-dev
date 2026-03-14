"""Comparison utilities for A/B testing experiments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from evals.framework.experiment import RunResult
    from evals.framework.store import LocalStore


@dataclass
class Comparison:
    """Comparison between two experiment runs."""

    baseline: RunResult
    candidate: RunResult

    @property
    def success_rate_delta(self) -> float:
        """Difference in success rate (candidate - baseline)."""
        return self.candidate.success_rate - self.baseline.success_rate

    @property
    def duration_delta(self) -> float:
        """Difference in duration (candidate - baseline)."""
        return self.candidate.duration_seconds - self.baseline.duration_seconds

    def metric_delta(self, metric: str) -> float | None:
        """Get difference for a specific metric."""
        baseline_val = self.baseline.summary.get(metric)
        candidate_val = self.candidate.summary.get(metric)
        if baseline_val is None or candidate_val is None:
            return None
        return candidate_val - baseline_val

    def all_metric_deltas(self) -> dict[str, float]:
        """Get all metric differences."""
        all_metrics = set(self.baseline.summary.keys()) | set(
            self.candidate.summary.keys()
        )
        deltas = {}
        for metric in all_metrics:
            delta = self.metric_delta(metric)
            if delta is not None:
                deltas[metric] = delta
        return deltas

    def print_comparison(self) -> None:
        """Print formatted comparison."""
        print(f"\n{'=' * 70}")
        print("Comparison")
        print(f"{'=' * 70}")
        print(
            f"Baseline:  {self.baseline.name} ({self.baseline.provenance.prompt.hash[:8]})"
        )
        print(
            f"Candidate: {self.candidate.name} ({self.candidate.provenance.prompt.hash[:8]})"
        )
        print(f"{'-' * 70}")

        # Success rate
        sr_delta = self.success_rate_delta
        sr_indicator = "+" if sr_delta >= 0 else ""
        print(
            f"Success Rate: {self.baseline.success_rate:.1%} -> {self.candidate.success_rate:.1%} "
            f"({sr_indicator}{sr_delta:.1%})"
        )

        # Duration
        dur_delta = self.duration_delta
        dur_indicator = "+" if dur_delta >= 0 else ""
        faster_slower = "slower" if dur_delta > 0 else "faster"
        print(
            f"Duration:     {self.baseline.duration_seconds:.1f}s -> {self.candidate.duration_seconds:.1f}s "
            f"({dur_indicator}{dur_delta:.1f}s {faster_slower})"
        )

        # Other metrics
        deltas = self.all_metric_deltas()
        for metric, delta in sorted(deltas.items()):
            if metric in ("success_rate", "duration_seconds"):
                continue
            baseline_val = self.baseline.summary.get(metric, 0)
            candidate_val = self.candidate.summary.get(metric, 0)
            indicator = "+" if delta >= 0 else ""
            print(
                f"{metric:14}: {baseline_val:.1%} -> {candidate_val:.1%} ({indicator}{delta:.1%})"
            )

        print(f"{'=' * 70}")


def compare_experiments(
    baseline: RunResult,
    candidate: RunResult,
) -> Comparison:
    """Create a comparison between two experiment results."""
    return Comparison(baseline=baseline, candidate=candidate)


def find_disagreements(
    result1: RunResult,
    result2: RunResult,
    store: LocalStore | None = None,
) -> list[dict]:
    """Find cases where two experiments disagree.

    Requires both experiments to have saved Parquet results.
    Returns list of case details where outputs differ.
    """
    try:
        import polars as pl
    except ImportError as e:
        raise ImportError("polars is required for disagreement analysis") from e

    if store is None:
        from evals.framework.store import LocalStore

        store = LocalStore()

    if not result1.results_path or not result2.results_path:
        raise ValueError("Both results must have saved Parquet files")

    df1 = pl.read_parquet(result1.results_path)
    df2 = pl.read_parquet(result2.results_path)

    # Join on case_name
    joined = df1.join(df2, on="case_name", suffix="_2")

    # Find cases where outputs differ
    disagreements = []
    for row in joined.iter_rows(named=True):
        output1 = row.get("output")
        output2 = row.get("output_2")
        if output1 != output2:
            disagreements.append({
                "case_name": row["case_name"],
                "input": row.get("input"),
                "output_1": output1,
                "output_2": output2,
                "success_1": row.get("success"),
                "success_2": row.get("success_2"),
            })

    return disagreements


def print_disagreements(disagreements: list[dict], max_items: int = 10) -> None:
    """Print disagreement summary."""
    print(f"\nFound {len(disagreements)} disagreements")
    if not disagreements:
        return

    print(f"\nShowing first {min(len(disagreements), max_items)} disagreements:")
    print("-" * 60)

    for i, d in enumerate(disagreements[:max_items]):
        print(f"\n[{i + 1}] {d['case_name']}")
        print(
            f"  Input: {d['input'][:100]}..."
            if len(d.get("input", "")) > 100
            else f"  Input: {d.get('input')}"
        )
        print(
            f"  Output 1: {d['output_1'][:80]}..."
            if len(str(d.get("output_1", ""))) > 80
            else f"  Output 1: {d.get('output_1')}"
        )
        print(
            f"  Output 2: {d['output_2'][:80]}..."
            if len(str(d.get("output_2", ""))) > 80
            else f"  Output 2: {d.get('output_2')}"
        )
        print(f"  Success: {d.get('success_1')} vs {d.get('success_2')}")
