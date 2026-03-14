# Evaluation Framework

A framework for evaluating AI agents in actBI. Supports single-agent evaluation, multi-agent workflow evaluation, and model/prompt comparison.

See [ADR-002](../docs/ADRs/002-evaluation-framework.md) for design decisions.

## Quick Start

```bash
# Run an evaluation
just eval intent_classifier

# Compare models
just eval intent_classifier --model google:gemini-3-flash-preview

# Quick iteration with sampling
just eval data_explorer --sample 10
```

---

## CLI Reference

### Running Evaluations

```bash
# Run evaluation from config
just eval <config_name>

# Override model
just eval intent_classifier --model anthropic:claude-sonnet-4-20250514

# Sample subset of test cases
just eval data_explorer --sample 10

# Don't save results (ephemeral run)
just eval intent_classifier --no-save

# Verbose output
just eval intent_classifier -v
```

### Managing Experiments

```bash
# List stored experiments
just eval-list

# Filter by agent
just eval-list --agent IntentClassifier

# Show experiment details
just eval-show <experiment-id>

# Compare two experiments
just eval-compare <baseline-id> <candidate-id>

# Show only disagreeing cases
just eval-compare <id1> <id2> --disagreements
```

### Example Output

```
$ just eval intent_classifier

Loading config: evals/configs/intent_classifier.yaml
Agent: IntentClassifier
Models: [gemini-2.5-flash-lite, gemini-3-flash-preview]

Evaluating 50 cases with gemini-2.5-flash-lite... done (8.2s)
Evaluating 50 cases with gemini-3-flash-preview... done (45.1s)

============================================================
Comparison: IntentClassifier Model Comparison
============================================================

gemini-2.5-flash-lite (50 cases, 8.2s)
  Field    | Accuracy |       F1 | Precision |   Recall
  -------- | -------- | -------- | --------- | --------
  task     |    92.0% |    91.8% |     92.4% |    92.0%
  mode     |    85.7% |    85.4% |     88.9% |    85.7%
  job      |    88.0% |    87.2% |     89.1% |    88.0%

gemini-3-flash-preview (50 cases, 45.1s)
  Field    | Accuracy |       F1 | Precision |   Recall
  -------- | -------- | -------- | --------- | --------
  task     |    96.0% |    95.9% |     96.2% |    96.0%
  mode     |    92.0% |    91.8% |     92.5% |    92.0%
  job      |    94.0% |    93.8% |     94.3% |    94.0%

Best by task_accuracy: gemini-3-flash-preview (96.0%)
```

---

## Notebook Interface

Notebooks provide interactive development with visualization support.

### Model Comparison

```python
from evals import Experiment, ExperimentSet
from evals.datasets import load_from_manifest
from agents.intent_classifier import IntentClassifier

# Load dataset
cases = load_from_manifest("intent_classifier")

# Compare models
comparison = await ExperimentSet(
    experiments=[
        Experiment(
            agent=IntentClassifier,
            prompt="xms://intent_classifier/v1",
            model="google:gemini-2.5-flash-lite",
            dataset=cases,
            dataset_name="intent_classifier",
        ),
        Experiment(
            agent=IntentClassifier,
            prompt="xms://intent_classifier/v1",
            model="google:gemini-3-flash-preview",
            dataset=cases,
            dataset_name="intent_classifier",
        ),
    ]
).run(save=False)

# View results
comparison.print_comparison()
comparison.plot_metrics(fields=["task_accuracy", "mode_accuracy", "job_accuracy"])
comparison.to_dataframe()  # For custom analysis
```

### Single Experiment

```python
exp = Experiment(
    agent=IntentClassifier,
    prompt="xms://intent_classifier/v1",
    model="google:gemini-3-flash-preview",
    dataset=cases,
    dataset_name="intent_classifier",
)

result = await exp.run(save=False)
result.print_summary()
```

### Ad-hoc Testing

Test arbitrary inputs without a dataset:

```python
from agents.intent_classifier import IntentClassifier
from agents.intent_classifier.schemas import IntentClassifierInput

agent = IntentClassifier(model="google:gemini-3-flash-preview")

result = await agent.arun(IntentClassifierInput(
    message_text="What's driving the margin improvement this quarter?"
))
print(result)
```

### Subset Evaluation

Evaluate specific categories:

```python
# Filter to edge cases only
edge_cases = [c for c in cases if c.metadata.get("category") == "edge_case"]

exp = Experiment(
    agent=IntentClassifier,
    dataset=edge_cases,
    dataset_name="edge_cases",
    ...
)
result = await exp.run(save=False)
print(f"Edge Cases: {result.success_rate:.1%}")
```

### Confusion Matrix

```python
from sklearn.metrics import ConfusionMatrixDisplay, confusion_matrix

# After running evaluation
y_true = [case.expected["task"] for case in result.cases]
y_pred = [case.output.task for case in result.cases]

cm = confusion_matrix(y_true, y_pred, labels=["consult", "reflect"])
ConfusionMatrixDisplay(cm, display_labels=["consult", "reflect"]).plot()
```

---

## Tracing

Enable LangSmith for debugging failed evaluations:

```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=xxx
export LANGCHAIN_PROJECT=actbi-evals
```

When evaluations fail, inspect the full trace in the LangSmith UI.

---

## Storage

Results are stored locally:

```
.eval/
├── experiments.db              # SQLite: experiment metadata
├── results/
│   └── {experiment-id}.parquet # Detailed case results
└── langchain_cache.db          # LLM response cache
```

---

## Fixtures

Fixtures provide test isolation for XLake and Qdrant.

### Modes

| Component | Mode | Behavior | Use Case |
|-----------|------|----------|----------|
| XLake | `mock` | Return responses from fixture file | Unit tests, CI |
| XLake | `live` | Real XLake calls | Integration tests |
| Qdrant | `mock` | Return fixed results from fixture | Fast, deterministic |
| Qdrant | `seeded` | Real Qdrant, fixed seed | Reproducible but realistic |
| Qdrant | `live` | Real Qdrant, no controls | Integration tests |

### Configuration

Experiment-level:

```yaml
fixtures:
  xlake:
    mode: mock
    responses: fixtures/xlake/data_explorer.yaml
  qdrant:
    mode: seeded
    seed: 42
```

Per-case override:

```yaml
- name: specific_test
  inputs: { ... }
  fixtures:
    qdrant:
      mode: mock
  assert: [ ... ]
```

---

## Recommended Runs by Agent

For non-deterministic agents, use multiple runs:

| Agent | Deterministic? | Recommended `runs` |
|-------|----------------|-------------------|
| IntentClassifier | Yes | 1 (default) |
| QueryBuilder | Mostly | 1 |
| DataExplorer | No (vector search) | 3 |
| DataInterpreter | No (narrative) | 3 |
| VisualizationDesigner | Mostly | 1 |
| BriefCreator | No (narrative) | 3 |

```yaml
- name: gdp_search
  runs: 3
  inputs: { ... }
  assert: [ ... ]
```

---

## Reference

- [Assertion Types](docs/assertions.md) — Full reference of all assertion types
- [ADR-002](../docs/ADRs/002-evaluation-framework.md) — Design decisions
