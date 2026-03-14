# Agent Evaluation Guide

This guide covers running evaluations for actBI agents, comparing experiments, and analyzing results.

## Quick Start

```bash
# Run evaluation for a specific agent
cd data/agents
uv run python -m agents.evals.cli run intent_classifier

# List available configs
uv run python -m agents.evals.cli list

# View run history
uv run python -m agents.evals.cli history
```

## Running Evaluations

### From CLI

The eval CLI supports these commands:

| Command | Description |
|---------|-------------|
| `run <config>` | Run experiments defined in a YAML config |
| `list` | List available config files |
| `history` | Show recent run results |
| `show <run_id>` | Show details for a specific run |
| `compare <id1> <id2>` | Compare two runs |
| `export <run_id>` | Export results to Parquet |

```bash
# Run with specific model override
uv run python -m agents.evals.cli run intent_classifier --model anthropic:claude-sonnet-4-20250514

# Run without saving results
uv run python -m agents.evals.cli run intent_classifier --no-save
```

### From Notebooks

For interactive exploration, use notebooks in `data/analysis/notebooks/agents/`:

```python
from agents.evals import datasets
from agents.evals.framework import Experiment, ExperimentSet
from agents.intent_classifier import IntentClassifier

# Load dataset
cases = datasets.load("intent_classifier")

# Create experiment
exp = Experiment(
    agent=IntentClassifier,
    prompt="py://agents.intent_classifier.agent:DEFAULT_PROMPT",
    model="google:gemini-3-flash-preview",
    dataset=cases,
    dataset_name="intent_classifier",
)

# Run and get results
result = await exp.run()
result.print_summary()
```

### From YAML Config

Config files in `src/agents/evals/configs/` define reusable experiments:

```yaml
# configs/intent_classifier.yaml
name: intent_classifier_eval
description: IntentClassifier evaluation suite

agent: agents.intent_classifier:IntentClassifier

prompts:
  - py://agents.intent_classifier.agent:DEFAULT_PROMPT

models:
  - google:gemini-3-flash-preview
  - anthropic:claude-sonnet-4-20250514

dataset: intent_classifier

metrics:
  - exact_match
  - field_f1:
      fields: [task, mode, job]
  - latency

tags:
  - intent
  - classification
```

## Understanding Metrics

### Classification Metrics

For agents with discrete output fields (like IntentClassifier):

| Metric | Description |
|--------|-------------|
| `field_accuracy` | Exact match rate per field |
| `field_f1` | F1 score (harmonic mean of precision/recall) |
| `field_precision` | True positives / predicted positives |
| `field_recall` | True positives / actual positives |

Output example:
```
gemini-3-flash-preview (14 cases, 12.3s)
  Git: abc1234[clean]
  Field    | Accuracy |       F1 | Precision |   Recall
  -------- | -------- | -------- | --------- | --------
  job      |    78.6% |    81.2% |     85.0% |    78.6%
  mode     |    85.7% |    87.3% |     88.9% |    85.7%
  task     |   100.0% |   100.0% |    100.0% |   100.0%
```

### General Metrics

| Metric | Description |
|--------|-------------|
| `exact_match` | Full output matches expected (all fields) |
| `latency` | Response time in seconds |

## Comparing Experiments

### A/B Testing Prompts

```python
from agents.evals.framework import ExperimentSet

# Compare two prompt versions
exp_set = ExperimentSet(
    experiments=[
        Experiment(
            agent=IntentClassifier,
            prompt="py://agents.intent_classifier.agent:DEFAULT_PROMPT",
            model="google:gemini-3-flash-preview",
            dataset=cases,
            dataset_name="intent_classifier",
        ),
        Experiment(
            agent=IntentClassifier,
            prompt="py://agents.intent_classifier.agent:IMPROVED_PROMPT",
            model="google:gemini-3-flash-preview",
            dataset=cases,
            dataset_name="intent_classifier",
        ),
    ],
    name="prompt_comparison",
)

comparison = await exp_set.run()
comparison.print_comparison()
```

### Cross-Model Comparison

```python
# Compare models with same prompt
models = [
    "google:gemini-3-flash-preview",
    "anthropic:claude-sonnet-4-20250514",
    "openai:gpt-4o",
]

experiments = [
    Experiment(
        agent=IntentClassifier,
        prompt="py://agents.intent_classifier.agent:DEFAULT_PROMPT",
        model=model,
        dataset=cases,
        dataset_name="intent_classifier",
    )
    for model in models
]

comparison = await ExperimentSet(experiments=experiments, name="model_comparison").run()

# Visualize results
comparison.plot_metrics()  # Bar chart of field metrics
comparison.plot_speed_accuracy()  # Speed vs accuracy scatter
```

## Storage and Results

### Local Storage

Results are stored in `.eval/` directory:

```
.eval/
├── runs.db           # SQLite index of all runs
└── results/          # Per-run Parquet files
    ├── {uuid1}.parquet
    └── {uuid2}.parquet
```

### Loading Previous Results

```python
from agents.evals.framework.storage import ResultStore

store = ResultStore()

# Get all runs
runs = store.list_runs(limit=10)

# Load specific run
result = store.load_run("abc123...")

# Query by agent type
intent_runs = store.list_runs(agent_type="IntentClassifier")
```

### Exporting Results

```python
# Export to DataFrame
df = result.to_dataframe()

# Export comparison table
comparison_df = comparison.to_dataframe()
```

## Provenance Tracking

Every run captures:

| Field | Description |
|-------|-------------|
| `git_commit` | Current commit hash |
| `git_dirty` | Whether working tree has changes |
| `prompt.hash` | SHA256 of prompt content |
| `prompt.source` | Prompt reference (py://...) |
| `model` | Model identifier (provider:model) |
| `created_at` | Timestamp |

This enables reproducibility and debugging regressions.

## Troubleshooting

### Missing API Key

```
Error: No API key found for provider 'anthropic'
```

Set the appropriate environment variable:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
export GOOGLE_API_KEY=...
export OPENAI_API_KEY=sk-...
```

### Dataset Not Found

```
KeyError: Dataset 'my_dataset' not in manifest
```

Ensure your dataset is:
1. Created as `datasets/my_dataset.jsonl`
2. Added to `datasets/manifest.yaml`

### Validation Errors

```
ValueError: datasets/my_dataset.jsonl:5: Input validation failed
```

Check that your JSONL matches the schema defined in manifest.yaml. See [DATASET_REFERENCE.md](DATASET_REFERENCE.md) for format details.

## Next Steps

- [ADDING_AGENTS.md](ADDING_AGENTS.md) - Add a new agent with evaluation
- [DATASET_REFERENCE.md](DATASET_REFERENCE.md) - Dataset format specification
- [ARCHITECTURE.md](ARCHITECTURE.md) - Framework design decisions
