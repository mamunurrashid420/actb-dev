"""Dataset loading utilities for evaluation framework.

Supports both JSON arrays (.json) and JSONL (.jsonl) formats.
"""

import importlib
import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_evals import Case

from evals.framework.assertions.types import Assertion
from evals.framework.fixtures.types import ToolFixtures


class EvalCase(BaseModel):
    """A test case with assertion-based expectations.

    This is the modern format for evaluation test cases, replacing the
    expected_output approach with explicit assertions.

    Examples:
        Minimal case:
            EvalCase(name="basic", inputs={"query": "Find GDP"})

        Full case with assertions and fixtures:
            EvalCase(
                name="gdp_search",
                inputs={"query": "Find GDP data"},
                runs=3,
                assert_=[
                    Assertion(type="not-null", field="recommended_asset"),
                    Assertion(type="any-contains", field="assets_found[*].path", value="gdp"),
                ],
                fixtures=ToolFixtures(tools="fixtures/tools/custom.yaml"),
            )
    """

    name: str
    """Unique name for this test case."""

    inputs: dict
    """Input data for the agent."""

    runs: int = 1
    """Number of times to run this test case (for statistical significance)."""

    assert_: list[Assertion] = Field(default_factory=list, alias="assert")
    """Assertions to evaluate against the agent output."""

    fixtures: ToolFixtures | None = None
    """Per-case fixture overrides (e.g., custom tool mocks)."""

    workflow_assert: list[Assertion] | None = None
    """Workflow-level assertions (for multi-agent workflows)."""

    metadata: dict = Field(default_factory=dict)
    """Arbitrary metadata for the test case."""

    model_config = {"populate_by_name": True}


def _resolve_type(type_path: str) -> type[BaseModel]:
    """Resolve a type path like 'module.path:ClassName' to a class."""
    if ":" not in type_path:
        raise ValueError(
            f"Invalid type path '{type_path}'. Expected 'module:ClassName'"
        )

    module_path, class_name = type_path.rsplit(":", 1)
    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        raise ImportError(f"Cannot import module '{module_path}': {e}") from e

    if not hasattr(module, class_name):
        raise AttributeError(f"Module '{module_path}' has no attribute '{class_name}'")

    return getattr(module, class_name)


def load_manifest(manifest_path: Path) -> dict[str, dict[str, str]]:
    """Load the dataset manifest YAML file."""
    with manifest_path.open() as f:
        return yaml.safe_load(f)


def load_json(
    path: str | Path,
) -> list[Case[dict, dict | None, dict]]:
    """Load evaluation cases from a JSON array file as untyped dicts.

    Args:
        path: Path to JSON file containing an array of cases.

    Returns:
        List of Case objects with dict inputs/outputs.
    """
    path = Path(path)

    with path.open() as f:
        try:
            data_list = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}: Invalid JSON: {e}") from e

    if not isinstance(data_list, list):
        raise ValueError(f"{path}: Expected JSON array, got {type(data_list).__name__}")

    cases: list[Case[dict, dict | None, dict]] = []
    for idx, data in enumerate(data_list):
        if "name" not in data:
            raise ValueError(f"{path}[{idx}]: Missing required 'name' field")
        if "inputs" not in data:
            raise ValueError(f"{path}[{idx}]: Missing required 'inputs' field")

        cases.append(
            Case(
                name=data["name"],
                inputs=data["inputs"],
                expected_output=data.get("expected_output"),
                metadata=data.get("metadata", {}),
            )
        )

    return cases


def load_jsonl(
    path: str | Path,
) -> list[Case[dict, dict | None, dict]]:
    """Load evaluation cases from a JSONL file as untyped dicts.

    Type validation happens downstream when the agent parses inputs
    and evaluators compare outputs.

    Args:
        path: Path to JSONL file containing cases.

    Returns:
        List of Case objects with dict inputs/outputs.
    """
    path = Path(path)
    cases: list[Case[dict, dict | None, dict]] = []

    with path.open() as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{line_num}: Invalid JSON: {e}") from e

            if "name" not in data:
                raise ValueError(f"{path}:{line_num}: Missing required 'name' field")
            if "inputs" not in data:
                raise ValueError(f"{path}:{line_num}: Missing required 'inputs' field")

            cases.append(
                Case(
                    name=data["name"],
                    inputs=data["inputs"],
                    expected_output=data.get("expected_output"),
                    metadata=data.get("metadata", {}),
                )
            )

    return cases


def _validate_and_build_cases[InputT: BaseModel, OutputT: BaseModel](
    data_list: list[dict],
    path: Path,
    input_type: type[InputT],
    output_type: type[OutputT],
) -> list[Case[InputT, OutputT | None, dict]]:
    """Validate a list of case dicts and build typed Case objects."""
    cases: list[Case[InputT, OutputT | None, dict]] = []

    for idx, data in enumerate(data_list):
        loc = f"{path}[{idx}]"

        if "name" not in data:
            raise ValueError(f"{loc}: Missing required 'name' field")
        if "inputs" not in data:
            raise ValueError(f"{loc}: Missing required 'inputs' field")

        try:
            validated_input = input_type.model_validate(data["inputs"])
        except Exception as e:
            raise ValueError(f"{loc}: Input validation failed: {e}") from e

        validated_output = None
        if data.get("expected_output"):
            try:
                validated_output = output_type.model_validate(data["expected_output"])
            except Exception as e:
                raise ValueError(f"{loc}: Output validation failed: {e}") from e

        cases.append(
            Case(
                name=data["name"],
                inputs=validated_input,
                expected_output=validated_output,
                metadata=data.get("metadata", {}),
            )
        )

    return cases


def load_json_typed[InputT: BaseModel, OutputT: BaseModel](
    path: str | Path,
    input_type: type[InputT],
    output_type: type[OutputT],
) -> list[Case[InputT, OutputT | None, dict]]:
    """Load evaluation cases from a JSON array file with type validation.

    Args:
        path: Path to JSON file containing an array of cases.
        input_type: Pydantic model class for input validation.
        output_type: Pydantic model class for expected_output validation.

    Returns:
        List of Case objects with validated inputs/outputs.
    """
    path = Path(path)

    with path.open() as f:
        try:
            data_list = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}: Invalid JSON: {e}") from e

    if not isinstance(data_list, list):
        raise ValueError(f"{path}: Expected JSON array, got {type(data_list).__name__}")

    return _validate_and_build_cases(data_list, path, input_type, output_type)


def load_jsonl_typed[InputT: BaseModel, OutputT: BaseModel](
    path: str | Path,
    input_type: type[InputT],
    output_type: type[OutputT],
) -> list[Case[InputT, OutputT | None, dict]]:
    """Load evaluation cases from a JSONL file with type validation.

    Use this when you need validated Pydantic models at load time.

    Args:
        path: Path to JSONL file containing cases.
        input_type: Pydantic model class for input validation.
        output_type: Pydantic model class for expected_output validation.

    Returns:
        List of Case objects with validated inputs/outputs.
    """
    path = Path(path)
    data_list: list[dict] = []

    with path.open() as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{line_num}: Invalid JSON: {e}") from e

            data_list.append(data)

    return _validate_and_build_cases(data_list, path, input_type, output_type)


def load_yaml(
    path: str | Path,
) -> list[Case[dict, dict | None, dict]]:
    """Load evaluation cases from a YAML file as untyped dicts.

    Args:
        path: Path to YAML file containing a list of cases.

    Returns:
        List of Case objects with dict inputs/outputs.
    """
    path = Path(path)

    with path.open() as f:
        data_list = yaml.safe_load(f)

    if not isinstance(data_list, list):
        raise ValueError(f"{path}: Expected YAML list, got {type(data_list).__name__}")

    cases: list[Case[dict, dict | None, dict]] = []
    for idx, data in enumerate(data_list):
        if "name" not in data:
            raise ValueError(f"{path}[{idx}]: Missing required 'name' field")
        if "inputs" not in data:
            raise ValueError(f"{path}[{idx}]: Missing required 'inputs' field")

        cases.append(
            Case(
                name=data["name"],
                inputs=data["inputs"],
                expected_output=data.get("expected_output"),
                metadata=data.get("metadata", {}),
            )
        )

    return cases


def load_yaml_typed[InputT: BaseModel, OutputT: BaseModel](
    path: str | Path,
    input_type: type[InputT],
    output_type: type[OutputT],
) -> list[Case[InputT, OutputT | None, dict]]:
    """Load evaluation cases from a YAML file with type validation.

    Args:
        path: Path to YAML file containing a list of cases.
        input_type: Pydantic model class for input validation.
        output_type: Pydantic model class for expected_output validation.

    Returns:
        List of Case objects with validated inputs/outputs.
    """
    path = Path(path)

    with path.open() as f:
        data_list = yaml.safe_load(f)

    if not isinstance(data_list, list):
        raise ValueError(f"{path}: Expected YAML list, got {type(data_list).__name__}")

    return _validate_and_build_cases(data_list, path, input_type, output_type)


def load_from_manifest(
    name: str,
    manifest: dict[str, dict[str, str]],
    datasets_dir: Path,
    validate: bool = True,
) -> list[Case[Any, Any, dict]]:
    """Load a dataset using schema info from the manifest.

    Checks for files in order: .yaml, .json, .jsonl

    Args:
        name: Dataset name (key in manifest).
        manifest: Parsed manifest dict.
        datasets_dir: Directory containing dataset files.
        validate: If True, validate against schemas. If False, return dicts.

    Returns:
        List of Case objects.

    Raises:
        KeyError: If dataset not in manifest.
        FileNotFoundError: If no dataset file exists.
        ValueError: If validation fails.
    """
    if name not in manifest:
        available = list(manifest.keys())
        raise KeyError(f"Dataset '{name}' not in manifest. Available: {available}")

    # Check for files in order of preference
    yaml_path = datasets_dir / f"{name}.yaml"
    json_path = datasets_dir / f"{name}.json"
    jsonl_path = datasets_dir / f"{name}.jsonl"

    if yaml_path.exists():
        path = yaml_path
        load_fn = load_yaml
        load_typed_fn = load_yaml_typed
    elif json_path.exists():
        path = json_path
        load_fn = load_json
        load_typed_fn = load_json_typed
    elif jsonl_path.exists():
        path = jsonl_path
        load_fn = load_jsonl
        load_typed_fn = load_jsonl_typed
    else:
        raise FileNotFoundError(
            f"Dataset file not found. Checked: {yaml_path}, {json_path}, {jsonl_path}"
        )

    if not validate:
        return load_fn(path)

    schema = manifest[name]
    input_type = _resolve_type(schema["input"])
    output_type = _resolve_type(schema["output"])

    return load_typed_fn(path, input_type, output_type)


# ─────────────────────────────────────────────────────────────────────────────
# EvalCase Loaders (assertion-based format)
# ─────────────────────────────────────────────────────────────────────────────


def _parse_test_case(data: dict, loc: str) -> EvalCase:
    """Parse a dict into a EvalCase model.

    Args:
        data: Raw dict from YAML/JSON.
        loc: Location string for error messages (e.g., "path.yaml[0]").

    Returns:
        Validated EvalCase instance.
    """
    if "name" not in data:
        raise ValueError(f"{loc}: Missing required 'name' field")
    if "inputs" not in data:
        raise ValueError(f"{loc}: Missing required 'inputs' field")

    try:
        return EvalCase.model_validate(data)
    except Exception as e:
        raise ValueError(f"{loc}: Failed to parse test case: {e}") from e


def load_test_cases_yaml(path: str | Path) -> list[EvalCase]:
    """Load test cases from a YAML file in the assertion-based format.

    Args:
        path: Path to YAML file containing a list of test cases.

    Returns:
        List of EvalCase objects.

    Example YAML format:
        - name: gdp_search
          inputs:
            query: Find GDP data
          runs: 3
          assert:
            - type: not-null
              field: recommended_asset
            - type: any-contains
              field: assets_found[*].path
              value: gdp
          fixtures:
            tools: fixtures/tools/custom.yaml
    """
    path = Path(path)

    with path.open() as f:
        data_list = yaml.safe_load(f)

    if not isinstance(data_list, list):
        raise ValueError(f"{path}: Expected YAML list, got {type(data_list).__name__}")

    test_cases: list[EvalCase] = []
    for idx, data in enumerate(data_list):
        test_case = _parse_test_case(data, f"{path}[{idx}]")
        test_cases.append(test_case)

    return test_cases


def load_test_cases_json(path: str | Path) -> list[EvalCase]:
    """Load test cases from a JSON array file in the assertion-based format.

    Args:
        path: Path to JSON file containing an array of test cases.

    Returns:
        List of EvalCase objects.
    """
    path = Path(path)

    with path.open() as f:
        try:
            data_list = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}: Invalid JSON: {e}") from e

    if not isinstance(data_list, list):
        raise ValueError(f"{path}: Expected JSON array, got {type(data_list).__name__}")

    test_cases: list[EvalCase] = []
    for idx, data in enumerate(data_list):
        test_case = _parse_test_case(data, f"{path}[{idx}]")
        test_cases.append(test_case)

    return test_cases


def load_test_cases_jsonl(path: str | Path) -> list[EvalCase]:
    """Load test cases from a JSONL file in the assertion-based format.

    Args:
        path: Path to JSONL file containing test cases (one per line).

    Returns:
        List of EvalCase objects.
    """
    path = Path(path)
    test_cases: list[EvalCase] = []

    with path.open() as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{line_num}: Invalid JSON: {e}") from e

            test_case = _parse_test_case(data, f"{path}:{line_num}")
            test_cases.append(test_case)

    return test_cases


def load_test_cases(path: str | Path) -> list[EvalCase]:
    """Load test cases from a file, auto-detecting format by extension.

    Supported formats:
        - .yaml/.yml: YAML list of test cases
        - .json: JSON array of test cases
        - .jsonl: JSON Lines (one test case per line)

    Args:
        path: Path to the test case file.

    Returns:
        List of EvalCase objects.
    """
    path = Path(path)

    if path.suffix in (".yaml", ".yml"):
        return load_test_cases_yaml(path)
    elif path.suffix == ".json":
        return load_test_cases_json(path)
    elif path.suffix == ".jsonl":
        return load_test_cases_jsonl(path)
    else:
        raise ValueError(
            f"{path}: Unsupported file extension '{path.suffix}'. "
            "Expected .yaml, .yml, .json, or .jsonl"
        )
