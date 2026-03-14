"""Tests for the eval framework loader with assertion-based test case format."""

from pathlib import Path

import pytest

from evals.framework.assertions.types import Assertion
from evals.framework.fixtures.types import ToolFixtures
from evals.framework.loader import (
    EvalCase,
    load_test_cases,
    load_test_cases_json,
    load_test_cases_jsonl,
    load_test_cases_yaml,
)

# ─────────────────────────────────────────────────────────────────────────────
# EvalCase Model Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestEvalCaseModel:
    """Tests for the EvalCase Pydantic model."""

    def test_minimal_test_case(self):
        """Should create test case with just name and inputs."""
        tc = EvalCase(name="basic", inputs={"query": "Find GDP"})

        assert tc.name == "basic"
        assert tc.inputs == {"query": "Find GDP"}
        assert tc.runs == 1  # default
        assert tc.assert_ == []  # default
        assert tc.fixtures is None  # default
        assert tc.workflow_assert is None  # default
        assert tc.metadata == {}  # default

    def test_test_case_with_all_fields(self):
        """Should create test case with all fields."""
        tc = EvalCase(
            name="full_case",
            inputs={"query": "Find GDP data"},
            runs=3,
            assert_=[
                Assertion(type="not-null", field="recommended_asset"),
                Assertion(
                    type="any-contains", field="assets_found[*].path", value="gdp"
                ),
            ],
            fixtures=ToolFixtures(tools=Path("fixtures/tools/custom.yaml")),
            workflow_assert=[
                Assertion(type="agent-invoked", value="IntentClassifier"),
            ],
            metadata={"category": "search"},
        )

        assert tc.name == "full_case"
        assert tc.inputs == {"query": "Find GDP data"}
        assert tc.runs == 3
        assert len(tc.assert_) == 2
        assert tc.assert_[0].type == "not-null"
        assert tc.fixtures is not None
        assert tc.fixtures.tools == Path("fixtures/tools/custom.yaml")
        assert tc.workflow_assert is not None
        assert len(tc.workflow_assert) == 1
        assert tc.metadata == {"category": "search"}

    def test_test_case_from_dict_with_alias(self):
        """Should parse 'assert' key as assert_ field (alias)."""
        data = {
            "name": "aliased",
            "inputs": {"query": "test"},
            "assert": [{"type": "not-null", "field": "result"}],
        }

        tc = EvalCase.model_validate(data)

        assert tc.name == "aliased"
        assert len(tc.assert_) == 1
        assert tc.assert_[0].type == "not-null"

    def test_test_case_serializes_with_alias(self):
        """Should serialize assert_ field as 'assert' (by_alias)."""
        tc = EvalCase(
            name="serialize",
            inputs={"query": "test"},
            assert_=[Assertion(type="not-null", field="result")],
        )

        data = tc.model_dump(by_alias=True, exclude_none=True)

        assert "assert" in data
        assert "assert_" not in data

    def test_test_case_populate_by_name(self):
        """Should accept both 'assert' and 'assert_' in input."""
        # Using alias
        tc1 = EvalCase.model_validate({
            "name": "t1",
            "inputs": {},
            "assert": [{"type": "not-null", "field": "x"}],
        })
        assert len(tc1.assert_) == 1

        # Using field name directly
        tc2 = EvalCase(
            name="t2", inputs={}, assert_=[Assertion(type="not-null", field="x")]
        )
        assert len(tc2.assert_) == 1


# ─────────────────────────────────────────────────────────────────────────────
# YAML Loader Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLoadEvalCasesYaml:
    """Tests for load_test_cases_yaml function."""

    def test_load_minimal_cases(self, tmp_path: Path):
        """Should load minimal test cases (name + inputs only)."""
        yaml_content = """
- name: case1
  inputs:
    query: Find GDP
- name: case2
  inputs:
    query: Show revenue
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        cases = load_test_cases_yaml(yaml_file)

        assert len(cases) == 2
        assert cases[0].name == "case1"
        assert cases[0].inputs == {"query": "Find GDP"}
        assert cases[1].name == "case2"

    def test_load_full_cases(self, tmp_path: Path):
        """Should load test cases with all fields."""
        yaml_content = """
- name: gdp_search
  inputs:
    query: Find GDP data
  runs: 3
  assert:
    - type: not-null
      field: recommended_asset
    - type: any-contains
      field: assets_found[*].asset_path
      value: gdp
  fixtures:
    tools: fixtures/tools/custom.yaml
  workflow_assert:
    - type: no-errors
    - type: agent-invoked
      value: IntentClassifier
  metadata:
    category: search
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        cases = load_test_cases_yaml(yaml_file)

        assert len(cases) == 1
        tc = cases[0]
        assert tc.name == "gdp_search"
        assert tc.runs == 3
        assert len(tc.assert_) == 2
        assert tc.assert_[0].type == "not-null"
        assert tc.assert_[1].type == "any-contains"
        assert tc.fixtures is not None
        assert tc.workflow_assert is not None
        assert len(tc.workflow_assert) == 2
        assert tc.metadata == {"category": "search"}

    def test_load_mixed_cases(self, tmp_path: Path):
        """Should load mix of minimal and full test cases."""
        yaml_content = """
- name: minimal
  inputs:
    query: test
- name: with_asserts
  inputs:
    query: test2
  assert:
    - type: not-null
      field: result
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        cases = load_test_cases_yaml(yaml_file)

        assert len(cases) == 2
        assert cases[0].assert_ == []
        assert len(cases[1].assert_) == 1

    def test_error_missing_name(self, tmp_path: Path):
        """Should error when test case is missing name."""
        yaml_content = """
- inputs:
    query: test
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValueError, match="Missing required 'name' field"):
            load_test_cases_yaml(yaml_file)

    def test_error_missing_inputs(self, tmp_path: Path):
        """Should error when test case is missing inputs."""
        yaml_content = """
- name: no_inputs
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValueError, match="Missing required 'inputs' field"):
            load_test_cases_yaml(yaml_file)

    def test_error_invalid_yaml(self, tmp_path: Path):
        """Should error on invalid YAML (not a list)."""
        yaml_content = """
name: not_a_list
inputs:
  query: test
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValueError, match="Expected YAML list"):
            load_test_cases_yaml(yaml_file)


# ─────────────────────────────────────────────────────────────────────────────
# JSON Loader Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLoadEvalCasesJson:
    """Tests for load_test_cases_json function."""

    def test_load_json_array(self, tmp_path: Path):
        """Should load test cases from JSON array."""
        json_content = """[
  {"name": "case1", "inputs": {"query": "test1"}},
  {"name": "case2", "inputs": {"query": "test2"}, "runs": 5}
]"""
        json_file = tmp_path / "test.json"
        json_file.write_text(json_content)

        cases = load_test_cases_json(json_file)

        assert len(cases) == 2
        assert cases[0].name == "case1"
        assert cases[1].runs == 5

    def test_error_not_array(self, tmp_path: Path):
        """Should error when JSON is not an array."""
        json_content = """{"name": "single", "inputs": {}}"""
        json_file = tmp_path / "test.json"
        json_file.write_text(json_content)

        with pytest.raises(ValueError, match="Expected JSON array"):
            load_test_cases_json(json_file)

    def test_error_invalid_json(self, tmp_path: Path):
        """Should error on invalid JSON."""
        json_file = tmp_path / "test.json"
        json_file.write_text("not valid json {")

        with pytest.raises(ValueError, match="Invalid JSON"):
            load_test_cases_json(json_file)


# ─────────────────────────────────────────────────────────────────────────────
# JSONL Loader Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLoadEvalCasesJsonl:
    """Tests for load_test_cases_jsonl function."""

    def test_load_jsonl(self, tmp_path: Path):
        """Should load test cases from JSONL (one per line)."""
        jsonl_content = """{"name": "case1", "inputs": {"query": "test1"}}
{"name": "case2", "inputs": {"query": "test2"}, "runs": 3}
"""
        jsonl_file = tmp_path / "test.jsonl"
        jsonl_file.write_text(jsonl_content)

        cases = load_test_cases_jsonl(jsonl_file)

        assert len(cases) == 2
        assert cases[0].name == "case1"
        assert cases[1].runs == 3

    def test_skip_empty_lines(self, tmp_path: Path):
        """Should skip empty lines in JSONL."""
        jsonl_content = """{"name": "case1", "inputs": {}}

{"name": "case2", "inputs": {}}
"""
        jsonl_file = tmp_path / "test.jsonl"
        jsonl_file.write_text(jsonl_content)

        cases = load_test_cases_jsonl(jsonl_file)

        assert len(cases) == 2

    def test_error_invalid_line(self, tmp_path: Path):
        """Should error with line number on invalid JSON line."""
        jsonl_content = """{"name": "case1", "inputs": {}}
not valid json
{"name": "case3", "inputs": {}}
"""
        jsonl_file = tmp_path / "test.jsonl"
        jsonl_file.write_text(jsonl_content)

        with pytest.raises(ValueError, match=":2:.*Invalid JSON"):
            load_test_cases_jsonl(jsonl_file)


# ─────────────────────────────────────────────────────────────────────────────
# Auto-detect Loader Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLoadEvalCases:
    """Tests for load_test_cases function (auto-detect format)."""

    def test_auto_detect_yaml(self, tmp_path: Path):
        """Should auto-detect YAML format."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("- name: test\n  inputs: {}\n")

        cases = load_test_cases(yaml_file)
        assert len(cases) == 1

    def test_auto_detect_yml(self, tmp_path: Path):
        """Should auto-detect .yml extension."""
        yml_file = tmp_path / "test.yml"
        yml_file.write_text("- name: test\n  inputs: {}\n")

        cases = load_test_cases(yml_file)
        assert len(cases) == 1

    def test_auto_detect_json(self, tmp_path: Path):
        """Should auto-detect JSON format."""
        json_file = tmp_path / "test.json"
        json_file.write_text('[{"name": "test", "inputs": {}}]')

        cases = load_test_cases(json_file)
        assert len(cases) == 1

    def test_auto_detect_jsonl(self, tmp_path: Path):
        """Should auto-detect JSONL format."""
        jsonl_file = tmp_path / "test.jsonl"
        jsonl_file.write_text('{"name": "test", "inputs": {}}\n')

        cases = load_test_cases(jsonl_file)
        assert len(cases) == 1

    def test_error_unsupported_extension(self, tmp_path: Path):
        """Should error on unsupported file extension."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not supported")

        with pytest.raises(ValueError, match="Unsupported file extension"):
            load_test_cases(txt_file)


# ─────────────────────────────────────────────────────────────────────────────
# Backward Compatibility Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBackwardCompatibility:
    """Tests for backward compatibility with old format."""

    def test_old_format_still_works(self, tmp_path: Path):
        """Old format with expected_output should still parse (as metadata)."""
        # Note: EvalCase doesn't have expected_output, but extra fields
        # would be ignored or could be put in metadata by design.
        # The test verifies that minimal cases still work.
        yaml_content = """
- name: old_format
  inputs:
    message_text: Show revenue
  metadata:
    expected_task: consult
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        cases = load_test_cases_yaml(yaml_file)

        assert len(cases) == 1
        assert cases[0].name == "old_format"
        assert cases[0].metadata == {"expected_task": "consult"}

    def test_empty_assert_list_is_default(self, tmp_path: Path):
        """Cases without 'assert' should have empty assertions list."""
        yaml_content = """
- name: no_assertions
  inputs:
    query: test
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        cases = load_test_cases_yaml(yaml_file)

        assert cases[0].assert_ == []


# ─────────────────────────────────────────────────────────────────────────────
# Integration: Load Real Dataset
# ─────────────────────────────────────────────────────────────────────────────


class TestLoadRealDataset:
    """Tests loading the actual intent_classifier dataset."""

    def test_load_intent_classifier_dataset(self):
        """Should load the intent_classifier.yaml dataset with assertions."""
        dataset_path = (
            Path(__file__).parent.parent
            / "src"
            / "evals"
            / "datasets"
            / "intent_classifier.yaml"
        )

        if not dataset_path.exists():
            pytest.skip("intent_classifier.yaml not found")

        cases = load_test_cases_yaml(dataset_path)

        assert len(cases) > 0
        # All cases should have name and inputs
        for case in cases:
            assert case.name
            assert case.inputs
        # First case should have assertions
        assert len(cases[0].assert_) > 0
        # Check first assertion type
        assert cases[0].assert_[0].type == "equals"
