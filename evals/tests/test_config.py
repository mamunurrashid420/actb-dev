"""Tests for the eval framework config with assertion and fixture support."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from evals.framework.assertions.types import Assertion
from evals.framework.config import (
    ExperimentConfig,
    _build_assertions,
    _build_fixtures,
    load_config,
)
from evals.framework.fixtures.types import ToolFixtures

# ─────────────────────────────────────────────────────────────────────────────
# ExperimentConfig Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestExperimentConfig:
    """Tests for ExperimentConfig dataclass."""

    def test_config_with_assertions(self):
        """Should store experiment-level assertions."""
        assertions = [
            Assertion(type="not-null", field="task"),
            Assertion(type="latency-budget", max_seconds=5),
        ]
        config = ExperimentConfig(
            name="test",
            description="Test config",
            agent=MagicMock,
            prompts=["prompt1"],
            models=["model1"],
            dataset=[],
            dataset_name="test_dataset",
            metrics=[],
            assertions=assertions,
        )

        assert len(config.assertions) == 2
        assert config.assertions[0].type == "not-null"
        assert config.assertions[1].max_seconds == 5

    def test_config_with_fixtures(self):
        """Should store experiment-level fixtures."""
        fixtures = ToolFixtures(tools=Path("fixtures/tools/test.yaml"))
        config = ExperimentConfig(
            name="test",
            description="Test config",
            agent=MagicMock,
            prompts=["prompt1"],
            models=["model1"],
            dataset=[],
            dataset_name="test_dataset",
            metrics=[],
            fixtures=fixtures,
        )

        assert config.fixtures is not None
        assert config.fixtures.tools == Path("fixtures/tools/test.yaml")

    def test_config_defaults(self):
        """Should have default empty assertions and None fixtures."""
        config = ExperimentConfig(
            name="test",
            description="Test config",
            agent=MagicMock,
            prompts=["prompt1"],
            models=["model1"],
            dataset=[],
            dataset_name="test_dataset",
            metrics=[],
        )

        assert config.assertions == []
        assert config.fixtures is None


# ─────────────────────────────────────────────────────────────────────────────
# Assertion Builder Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBuildAssertions:
    """Tests for _build_assertions function."""

    def test_build_empty_assertions(self):
        """Should return empty list for None input."""
        result = _build_assertions(None)
        assert result == []

    def test_build_empty_list(self):
        """Should return empty list for empty list input."""
        result = _build_assertions([])
        assert result == []

    def test_build_simple_assertions(self):
        """Should build Assertion objects from dicts."""
        config = [
            {"type": "not-null", "field": "task"},
            {"type": "equals", "field": "status", "value": "active"},
        ]

        result = _build_assertions(config)

        assert len(result) == 2
        assert result[0].type == "not-null"
        assert result[0].field == "task"
        assert result[1].type == "equals"
        assert result[1].value == "active"

    def test_build_performance_assertions(self):
        """Should build performance assertions."""
        config = [
            {"type": "latency-budget", "max_seconds": 5.0},
            {"type": "token-budget", "max_tokens": 1000},
        ]

        result = _build_assertions(config)

        assert len(result) == 2
        assert result[0].max_seconds == 5.0
        assert result[1].max_tokens == 1000

    def test_build_range_assertions(self):
        """Should build range assertions."""
        config = [
            {"type": "in-range", "field": "score", "min": 0, "max": 100},
        ]

        result = _build_assertions(config)

        assert len(result) == 1
        assert result[0].min == 0
        assert result[0].max == 100

    def test_invalid_assertion_raises(self):
        """Should raise error for invalid assertion."""
        config = [
            {"type": "invalid-type", "field": "x", "unknown_field": "bad"},
        ]

        with pytest.raises(ValueError, match="Invalid assertion at index 0"):
            _build_assertions(config)


# ─────────────────────────────────────────────────────────────────────────────
# Fixture Builder Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBuildFixtures:
    """Tests for _build_fixtures function."""

    def test_build_none_fixtures(self):
        """Should return None for None input."""
        result = _build_fixtures(None)
        assert result is None

    def test_build_tool_fixtures_path(self):
        """Should build ToolFixtures with path."""
        config = {"tools": "fixtures/tools/test.yaml"}

        result = _build_fixtures(config)

        assert result is not None
        assert result.tools == Path("fixtures/tools/test.yaml")

    def test_build_tool_fixtures_live(self):
        """Should build ToolFixtures with 'live' mode."""
        config = {"tools": "live"}

        result = _build_fixtures(config)

        assert result is not None
        assert result.tools == "live"

    def test_invalid_fixtures_raises(self):
        """Should raise error for invalid fixtures."""
        config = {"tools": "path.yaml", "unknown": "field"}

        with pytest.raises(ValueError, match="Invalid fixtures config"):
            _build_fixtures(config)


# ─────────────────────────────────────────────────────────────────────────────
# Load Config Integration Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLoadConfig:
    """Tests for load_config function with assertions and fixtures."""

    @patch("evals.framework.config._resolve_class")
    @patch("evals.framework.config._resolve_dataset")
    def test_load_config_with_assertions(
        self, mock_resolve_dataset, mock_resolve_class, tmp_path: Path
    ):
        """Should load config with experiment-level assertions."""
        mock_resolve_class.return_value = MagicMock
        mock_resolve_dataset.return_value = ([], "test_dataset")

        yaml_content = """
name: test_eval
agent: agents.test:TestAgent
dataset: test_dataset
models:
  - test-model
prompts:
  - test-prompt
assert:
  - type: not-null
    field: task
  - type: latency-budget
    max_seconds: 5
tags:
  - test
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(yaml_content)

        config = load_config(config_file)

        assert config.name == "test_eval"
        assert len(config.assertions) == 2
        assert config.assertions[0].type == "not-null"
        assert config.assertions[0].field == "task"
        assert config.assertions[1].type == "latency-budget"
        assert config.assertions[1].max_seconds == 5

    @patch("evals.framework.config._resolve_class")
    @patch("evals.framework.config._resolve_dataset")
    def test_load_config_with_fixtures(
        self, mock_resolve_dataset, mock_resolve_class, tmp_path: Path
    ):
        """Should load config with experiment-level fixtures."""
        mock_resolve_class.return_value = MagicMock
        mock_resolve_dataset.return_value = ([], "test_dataset")

        yaml_content = """
name: test_eval
agent: agents.test:TestAgent
dataset: test_dataset
models:
  - test-model
prompts:
  - test-prompt
fixtures:
  tools: fixtures/tools/data_explorer.yaml
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(yaml_content)

        config = load_config(config_file)

        assert config.fixtures is not None
        assert config.fixtures.tools == Path("fixtures/tools/data_explorer.yaml")

    @patch("evals.framework.config._resolve_class")
    @patch("evals.framework.config._resolve_dataset")
    def test_load_config_without_assertions(
        self, mock_resolve_dataset, mock_resolve_class, tmp_path: Path
    ):
        """Should have empty assertions when 'assert' is missing (backward compatible)."""
        mock_resolve_class.return_value = MagicMock
        mock_resolve_dataset.return_value = ([], "test_dataset")

        yaml_content = """
name: test_eval
agent: agents.test:TestAgent
dataset: test_dataset
models:
  - test-model
prompts:
  - test-prompt
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(yaml_content)

        config = load_config(config_file)

        assert config.assertions == []
        assert config.fixtures is None

    @patch("evals.framework.config._resolve_class")
    @patch("evals.framework.config._resolve_dataset")
    def test_load_config_full_example(
        self, mock_resolve_dataset, mock_resolve_class, tmp_path: Path
    ):
        """Should load config with all fields."""
        mock_resolve_class.return_value = MagicMock
        mock_resolve_dataset.return_value = ([], "intent_classifier")

        yaml_content = """
name: intent_classifier_eval
agent: agents.intent_classifier:IntentClassifier
dataset: intent_classifier
models:
  - google:gemini-3-flash-preview
prompts:
  - py://agents.intent_classifier.agent:DEFAULT_PROMPT
assert:
  - type: not-null
    field: task
  - type: not-null
    field: mode
  - type: not-null
    field: job
  - type: latency-budget
    max_seconds: 5
fixtures:
  tools: fixtures/tools/data_explorer.yaml
tags:
  - intent
  - classification
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(yaml_content)

        config = load_config(config_file)

        assert config.name == "intent_classifier_eval"
        assert len(config.assertions) == 4
        assert config.fixtures is not None
        assert config.tags == ["intent", "classification"]


# ─────────────────────────────────────────────────────────────────────────────
# Real Config File Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLoadRealConfig:
    """Tests loading actual config files from the codebase."""

    def test_intent_classifier_config_has_assertions(self):
        """The intent_classifier config should have assertions defined."""
        config_path = (
            Path(__file__).parent.parent / "configs" / "intent_classifier.yaml"
        )

        if not config_path.exists():
            pytest.skip("intent_classifier.yaml config not found")

        with open(config_path) as f:
            raw = yaml.safe_load(f)

        # Verify the YAML structure has assertions
        assert "assert" in raw, "Config should have 'assert' key"
        assert isinstance(raw["assert"], list), "'assert' should be a list"
        assert len(raw["assert"]) > 0, "'assert' should not be empty"

        # Verify first assertion structure
        first_assertion = raw["assert"][0]
        assert "type" in first_assertion, "Assertion should have 'type'"
