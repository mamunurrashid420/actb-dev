"""Evaluation framework for actBI agents.

An assertion-based evaluation system with config-driven experiments,
prompt resolution, provenance tracking, and local storage.
"""

from evals.framework import metrics
from evals.framework.experiment import (
    ComparisonResult,
    Experiment,
    ExperimentSet,
    MultiRunResult,
    RunResult,
    SingleRunResult,
)
from evals.framework.fixtures import FixtureManager, ToolFixtures
from evals.framework.loader import (
    EvalCase,
    load_from_manifest,
    load_jsonl,
    load_jsonl_typed,
    load_manifest,
    load_test_cases,
    load_test_cases_json,
    load_test_cases_jsonl,
    load_test_cases_yaml,
)
from evals.framework.prompt import PromptResolver, ResolvedPrompt
from evals.framework.provenance import Provenance
from evals.framework.runner import AssertionRunner, EvalRunner, run_experiment
from evals.framework.workflow import (
    AgentSpan,
    AgentTrace,
    ToolCall,
    WorkflowTrace,
    WorkflowTraceCallback,
    capture_trace,
    clear_spans,
    get_exporter,
    get_finished_spans,
    setup_otel_tracing,
    spans_to_workflow_trace,
)

__all__ = [
    # Experiment types
    "ComparisonResult",
    "Experiment",
    "ExperimentSet",
    "MultiRunResult",
    "RunResult",
    "SingleRunResult",
    # Runner
    "AssertionRunner",
    "EvalRunner",
    "run_experiment",
    # Dataset loading
    "EvalCase",
    "load_jsonl",
    "load_jsonl_typed",
    "load_manifest",
    "load_from_manifest",
    "load_test_cases",
    "load_test_cases_yaml",
    "load_test_cases_json",
    "load_test_cases_jsonl",
    # Prompt resolution
    "PromptResolver",
    "ResolvedPrompt",
    # Provenance
    "Provenance",
    # Fixtures
    "FixtureManager",
    "ToolFixtures",
    # Workflow (core types)
    "WorkflowTrace",
    "WorkflowTraceCallback",
    "ToolCall",
    "AgentTrace",
    "AgentSpan",
    # Workflow (OTel tracing)
    "setup_otel_tracing",
    "get_exporter",
    "clear_spans",
    "get_finished_spans",
    "capture_trace",
    "spans_to_workflow_trace",
    # Metrics namespace
    "metrics",
]
