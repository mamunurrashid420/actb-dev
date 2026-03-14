"""YAML configuration loader for experiments."""

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from evals.framework import metrics
from evals.framework.assertions.types import Assertion
from evals.framework.experiment import Experiment, ExperimentSet
from evals.framework.fixtures.types import ToolFixtures


@dataclass
class ExperimentConfig:
    """Parsed experiment configuration."""

    name: str
    description: str
    agent: type
    prompts: list[str]
    models: list[str]
    dataset: list
    dataset_name: str
    metrics: list
    tags: list[str] = field(default_factory=list)
    assertions: list[Assertion] = field(default_factory=list)
    fixtures: ToolFixtures | None = None


def _resolve_class(path: str) -> type:
    """Resolve a class from module:ClassName format."""
    if ":" not in path:
        raise ValueError(
            f"Invalid class path: {path}. Expected format: module.path:ClassName"
        )

    module_path, class_name = path.rsplit(":", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _resolve_dataset(ref: str) -> tuple[list, str]:
    """Resolve dataset from name or module:variable reference.

    Args:
        ref: Either a simple name (e.g., "intent_classifier") that loads from JSONL,
             or a module:variable path (e.g., "my_module:MY_CASES") that imports.

    Returns:
        Tuple of (cases list, dataset_name)
    """
    if ":" in ref:
        # Module:variable format - import from Python module
        module_path, var_name = ref.rsplit(":", 1)
        module = importlib.import_module(module_path)
        return getattr(module, var_name), var_name
    else:
        # Simple name - load from JSONL
        from agents.evals import datasets

        return datasets.load(ref), ref


def _build_metrics(metrics_config: list[dict[str, Any]]) -> list:
    """Build metric evaluators from config."""
    evaluators = []

    for metric_spec in metrics_config:
        if isinstance(metric_spec, str):
            # Simple metric name
            if metric_spec == "exact_match":
                evaluators.append(metrics.exact_match())
            elif metric_spec == "latency":
                evaluators.append(metrics.latency())
            else:
                raise ValueError(f"Unknown metric: {metric_spec}")
        elif isinstance(metric_spec, dict):
            # Metric with parameters
            for name, params in metric_spec.items():
                if name == "exact_match":
                    evaluators.append(metrics.exact_match())
                elif name == "field_match":
                    evaluators.append(
                        metrics.field_match(fields=params.get("fields", []))
                    )
                elif name == "field_f1":
                    evaluators.append(metrics.field_f1(fields=params.get("fields", [])))
                elif name == "latency":
                    evaluators.append(metrics.latency())
                else:
                    raise ValueError(f"Unknown metric: {name}")

    return evaluators if evaluators else [metrics.exact_match()]


def _build_assertions(
    assertions_config: list[dict[str, Any]] | None,
) -> list[Assertion]:
    """Build Assertion objects from config.

    Args:
        assertions_config: List of assertion dicts from YAML, or None.

    Returns:
        List of validated Assertion objects.
    """
    if not assertions_config:
        return []

    assertions: list[Assertion] = []
    for idx, assertion_data in enumerate(assertions_config):
        try:
            assertion = Assertion.model_validate(assertion_data)
            assertions.append(assertion)
        except Exception as e:
            raise ValueError(f"Invalid assertion at index {idx}: {e}") from e

    return assertions


def _build_fixtures(fixtures_config: dict[str, Any] | None) -> ToolFixtures | None:
    """Build ToolFixtures from config.

    Args:
        fixtures_config: Fixtures dict from YAML, or None.

    Returns:
        ToolFixtures instance or None.
    """
    if not fixtures_config:
        return None

    try:
        return ToolFixtures.model_validate(fixtures_config)
    except Exception as e:
        raise ValueError(f"Invalid fixtures config: {e}") from e


def load_config(path: str | Path) -> ExperimentConfig:
    """Load experiment configuration from YAML file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    # Resolve agent class
    agent = _resolve_class(raw["agent"])

    # Resolve dataset
    dataset_name = raw["dataset"]
    dataset, dataset_name = _resolve_dataset(dataset_name)

    # Build metrics
    evaluators = _build_metrics(raw.get("metrics", []))

    # Build experiment-level assertions
    assertions = _build_assertions(raw.get("assert"))

    # Build experiment-level fixtures
    fixtures = _build_fixtures(raw.get("fixtures"))

    return ExperimentConfig(
        name=raw.get("name", path.stem),
        description=raw.get("description", ""),
        agent=agent,
        prompts=raw.get("prompts", []),
        models=raw.get("models", []),
        dataset=dataset,
        dataset_name=dataset_name,
        metrics=evaluators,
        tags=raw.get("tags", []),
        assertions=assertions,
        fixtures=fixtures,
    )


def config_to_experiment_set(config: ExperimentConfig) -> ExperimentSet:
    """Convert configuration to ExperimentSet (all prompt × model combinations)."""
    experiments = []

    for prompt in config.prompts:
        for model in config.models:
            exp = Experiment(
                agent=config.agent,
                prompt=prompt,
                model=model,
                dataset=config.dataset,
                dataset_name=config.dataset_name,
                metrics=config.metrics,
                name=f"{config.name}_{model.split(':')[-1]}",
                tags=config.tags,
            )
            experiments.append(exp)

    return ExperimentSet(experiments=experiments, name=config.name)


def load_and_create_experiments(path: str | Path) -> ExperimentSet:
    """Load config and create experiment set in one step."""
    config = load_config(path)
    return config_to_experiment_set(config)


# Directory for config files
CONFIGS_DIR = Path(__file__).parent.parent / "configs"


def list_configs() -> list[Path]:
    """List all available config files."""
    if not CONFIGS_DIR.exists():
        return []
    return sorted(CONFIGS_DIR.glob("*.yaml"))


def get_config_path(name: str) -> Path:
    """Get config path by name (without .yaml extension)."""
    path = CONFIGS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"Config not found: {name}. Available: {[p.stem for p in list_configs()]}"
        )
    return path
