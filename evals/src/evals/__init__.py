"""Evaluation framework for actBI agents."""

# ruff: noqa: I001
# Import order is intentional: we need 'metrics' to be bound to the framework module,
# not the legacy evals.metrics submodule. The framework import must come last.

# Import framework components (Experiment, RunResult, etc.)
from evals.framework import (
    Experiment,
    ExperimentSet,
    PromptResolver,
    Provenance,
    ResolvedPrompt,
    RunResult,
)

# Import legacy metrics functions (these import evals.metrics implicitly)
from evals.metrics import (
    ClassificationMetrics,
    classification_metrics_from_report,
    success_rate,
)

# Import framework metrics module LAST to bind 'metrics' to the framework module
# This must come after the evals.metrics import to override the implicit binding
from evals.framework import metrics as metrics  # noqa: PLC0414

__all__ = [
    # Legacy metrics (functions)
    "success_rate",
    "classification_metrics_from_report",
    "ClassificationMetrics",
    # Framework
    "Experiment",
    "ExperimentSet",
    "RunResult",
    "PromptResolver",
    "ResolvedPrompt",
    "Provenance",
    # Metrics namespace (module with exact_match, field_f1, etc.)
    "metrics",
]
