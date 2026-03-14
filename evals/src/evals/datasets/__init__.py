"""Test case datasets for agent evaluation.

Usage:
    from evals.datasets import load, available

    # Load any dataset by name (validates against schema from manifest)
    intent_cases = load("intent_classifier")
    viz_cases = load("viz_designer")
    explorer_cases = load("data_explorer")

    # Load without validation (returns dicts)
    cases = load("intent_classifier", validate=False)

    # List available datasets
    print(available())  # ["data_explorer", "intent_classifier", "viz_designer"]

    # Get schema info for a dataset
    from evals.datasets import get_schema
    schema = get_schema("intent_classifier")
    # {"input": "agents.intent_classifier.schemas:IntentClassifierInput", ...}

Adding a new dataset:
    1. Create a JSONL file: datasets/my_new_dataset.jsonl
    2. Add entry to manifest.yaml with input/output schema paths
    3. Run tests - they automatically validate all datasets
"""

from pathlib import Path
from typing import Any

from pydantic_evals import Case

from evals.framework.loader import load_from_manifest, load_manifest

_DATASETS_DIR = Path(__file__).parent
_MANIFEST_PATH = _DATASETS_DIR / "manifest.yaml"
_MANIFEST: dict[str, dict[str, str]] | None = None


def _get_manifest() -> dict[str, dict[str, str]]:
    """Load and cache the manifest."""
    global _MANIFEST
    if _MANIFEST is None:
        _MANIFEST = load_manifest(_MANIFEST_PATH)
    return _MANIFEST


def available() -> list[str]:
    """List available dataset names from the manifest."""
    return sorted(_get_manifest().keys())


def get_schema(name: str) -> dict[str, str]:
    """Get the schema definition for a dataset.

    Args:
        name: Dataset name.

    Returns:
        Dict with 'input' and 'output' type paths.

    Raises:
        KeyError: If dataset not in manifest.
    """
    manifest = _get_manifest()
    if name not in manifest:
        raise KeyError(f"Dataset '{name}' not in manifest. Available: {available()}")
    return manifest[name]


def load(name: str, *, validate: bool = True) -> list[Case[Any, Any, dict]]:
    """Load a dataset by name.

    Args:
        name: Dataset name (must be in manifest.yaml).
        validate: If True (default), validate against declared schemas.
                  If False, return raw dicts without validation.

    Returns:
        List of Case objects.

    Raises:
        KeyError: If dataset not in manifest.
        FileNotFoundError: If JSONL file doesn't exist.
        ValueError: If validation fails (when validate=True).
    """
    return load_from_manifest(name, _get_manifest(), _DATASETS_DIR, validate=validate)


__all__ = ["available", "get_schema", "load"]
