# Dataset Reference

This document covers the JSONL format and manifest structure for evaluation datasets.

## JSONL Format

Each line in a `.jsonl` file is a JSON object representing one test case:

```jsonl
{"name": "case_name", "inputs": {...}, "expected_output": {...}, "metadata": {...}}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique identifier for the case (snake_case) |
| `inputs` | object | Input data matching the agent's input schema |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `expected_output` | object | Expected output matching the agent's output schema |
| `metadata` | object | Additional info for filtering/analysis |

### Example

```jsonl
{"name": "simple_query", "inputs": {"message_text": "Show revenue"}, "expected_output": {"task": "consult", "mode": "reporter", "job": "query", "confidence": 0.9}, "metadata": {"category": "consult_reporter"}}
```

## Manifest Format

The `manifest.yaml` file maps dataset names to their schemas:

```yaml
# datasets/manifest.yaml
dataset_name:
  input: module.path:InputClassName
  output: module.path:OutputClassName
```

### Example

```yaml
intent_classifier:
  input: agents.intent_classifier.schemas:IntentClassifierInput
  output: agents.intent_classifier.schemas:IntentClassifierOutput

viz_designer:
  input: agents.viz_designer.schemas:VizInput
  output: agents.viz_designer.schemas:VizOutput
```

### Schema Resolution

The `module.path:ClassName` format is resolved at runtime:
1. Import `module.path` using Python's import system
2. Get attribute `ClassName` from the module
3. Validate JSONL data against the Pydantic model

## Loading Datasets

### Programmatic Access

```python
from agents.evals import datasets

# List available datasets
datasets.available()  # ["data_explorer", "intent_classifier", "viz_designer"]

# Load with validation (default)
cases = datasets.load("intent_classifier")

# Load without validation (raw dicts)
cases = datasets.load("intent_classifier", validate=False)

# Get schema info
schema = datasets.get_schema("intent_classifier")
# {"input": "agents.intent_classifier.schemas:...", "output": "..."}
```

### From YAML Config

Configs reference datasets by name (loads from JSONL):

```yaml
dataset: intent_classifier
```

Or by module:variable for custom Python datasets:

```yaml
dataset: my_module.datasets:CUSTOM_CASES
```

## Best Practices

### Case Design

- **Unique names**: Use descriptive snake_case names (`compare_quarters`, `vague_query`)
- **Edge cases**: Include ambiguous inputs, error conditions
- **Categories**: Use `metadata.category` for grouping similar cases
- **Balance**: Cover all expected output values (tasks, modes, jobs)

### Expected Output

- Include `expected_output` for supervised evaluation
- Match the exact schema structure
- Omit optional fields if not testing them

### Metadata

Common metadata fields:

```jsonl
{"metadata": {"category": "consult_reporter", "difficulty": "easy", "source": "manual"}}
```

- `category`: Logical grouping for analysis
- `difficulty`: For stratified evaluation
- `source`: Origin of test case (manual, generated, production)

## Validation

Tests automatically validate all datasets on every run:

```bash
# Run dataset validation
uv run pytest tests/evals/test_datasets.py -v
```

Validation checks:
1. JSONL syntax is valid
2. Required fields (`name`, `inputs`) present
3. Input data validates against schema
4. Expected output (if present) validates against schema

## Adding a Dataset

1. Create JSONL file: `datasets/my_dataset.jsonl`
2. Add to manifest:
   ```yaml
   my_dataset:
     input: agents.my_agent.schemas:MyInput
     output: agents.my_agent.schemas:MyOutput
   ```
3. Run tests to validate: `uv run pytest tests/evals/`

## File Organization

```
evals/datasets/
├── manifest.yaml           # Schema definitions
├── intent_classifier.jsonl # IntentClassifier cases
├── viz_designer.jsonl      # VisualizationDesigner cases
└── data_explorer.jsonl     # DataExplorer cases
```
