"""Tests for evaluation dataset loading and validation."""

import pytest


def _get_dataset_names() -> list[str]:
    """Get dataset names for parameterization (import at collection time)."""
    from evals.datasets import available

    return available()


class TestDatasetLoader:
    """Tests for the universal dataset loader."""

    def test_available_returns_manifest_datasets(self):
        """Should list datasets from manifest.yaml."""
        from evals.datasets import available

        datasets = available()
        assert isinstance(datasets, list)
        assert len(datasets) > 0
        # Known datasets should be present
        assert "intent_classifier" in datasets
        assert "viz_designer" in datasets
        assert "data_explorer" in datasets

    def test_load_returns_cases(self):
        """Should return list of Case objects."""
        from evals.datasets import load

        cases = load("intent_classifier")
        assert isinstance(cases, list)
        assert len(cases) > 0

    def test_load_nonexistent_raises_key_error(self):
        """Should raise KeyError for dataset not in manifest."""
        from evals.datasets import load

        with pytest.raises(KeyError) as exc_info:
            load("nonexistent_dataset")
        assert "nonexistent_dataset" in str(exc_info.value)
        assert "Available:" in str(exc_info.value)

    def test_get_schema_returns_type_paths(self):
        """Should return input/output type paths."""
        from evals.datasets import get_schema

        schema = get_schema("intent_classifier")
        assert "input" in schema
        assert "output" in schema
        assert "IntentClassifierInput" in schema["input"]
        assert "IntentClassifierOutput" in schema["output"]

    def test_get_schema_nonexistent_raises_key_error(self):
        """Should raise KeyError for unknown dataset."""
        from evals.datasets import get_schema

        with pytest.raises(KeyError):
            get_schema("nonexistent")

    def test_load_without_validation_returns_dicts(self):
        """validate=False should return dict inputs/outputs."""
        from evals.datasets import load

        cases = load("intent_classifier", validate=False)
        assert len(cases) > 0
        # Without validation, inputs/outputs are dicts
        assert isinstance(cases[0].inputs, dict)
        assert isinstance(cases[0].expected_output, dict)

    def test_load_with_validation_returns_typed(self):
        """validate=True (default) should return typed Pydantic models."""
        from evals.datasets import load

        cases = load("intent_classifier", validate=True)
        assert len(cases) > 0
        # With validation, inputs are typed
        assert hasattr(cases[0].inputs, "message_text")
        assert hasattr(cases[0].expected_output, "task")


class TestDatasetSchemaValidation:
    """Validates all datasets in manifest against their declared schemas.

    This test automatically runs for every dataset in manifest.yaml.
    Adding a new dataset to the manifest automatically adds a test case.
    """

    @pytest.mark.parametrize("dataset_name", _get_dataset_names())
    def test_dataset_validates_against_schema(self, dataset_name: str):
        """Dataset should load and validate against its declared schema."""
        from evals.datasets import load

        cases = load(dataset_name)
        assert len(cases) > 0, f"Dataset '{dataset_name}' is empty"

        # Verify each case has required structure
        for case in cases:
            assert case.name, f"Case missing name in {dataset_name}"
            assert case.inputs is not None, f"Case '{case.name}' missing inputs"


class TestIntentClassifierDataset:
    """Specific tests for intent_classifier dataset coverage."""

    def test_covers_all_tasks(self):
        """Dataset should cover both task types."""
        from evals.datasets import load

        cases = load("intent_classifier")
        tasks = {c.expected_output.task for c in cases}

        assert "consult" in tasks
        assert "reflect" in tasks

    def test_covers_all_modes(self):
        """Dataset should cover all mode types."""
        from evals.datasets import load

        cases = load("intent_classifier")
        modes = {c.expected_output.mode for c in cases}

        assert "reporter" in modes
        assert "interpreter" in modes
        assert "explorer" in modes

    def test_covers_key_jobs(self):
        """Dataset should cover key job types."""
        from evals.datasets import load

        cases = load("intent_classifier")
        jobs = {c.expected_output.job for c in cases}

        assert "query" in jobs
        assert "clarify" in jobs
        assert "out_of_scope" in jobs
