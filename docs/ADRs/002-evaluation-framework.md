# ADR-002: Evaluation Framework Design

**Status:** Proposed
**Date:** 2026-01-23

## Context

We need a consistent way to evaluate AI agents across the actBI platform. The framework must support:

1. **Classification agents** (IntentClassifier) - outputs have known expected values
2. **Discovery agents** (DataExplorer) - outputs satisfy constraints but aren't exactly predictable
3. **Generation agents** (BriefCreator, QueryBuilder) - outputs must meet quality criteria
4. **Multi-agent workflows** (Supervisor pipelines) - failures often occur at agent boundaries

Based on [industry research on LLM agent evaluation](https://arxiv.org/abs/2503.16416), we analyzed our 12 planned agents and found that most require **constraint-based evaluation** rather than exact matching. Non-deterministic agents (DataExplorer, DataInterpreter, BriefCreator) benefit from multiple evaluation runs.

## Decision

Adopt a **promptfoo-inspired assertion-based evaluation system** with:

1. **Single `assert` field** in test cases containing an array of assertions
2. **Experiment-level assertions** that apply to all test cases
3. **Automatic metric derivation** from assertion results
4. **Milestones** for multi-agent workflow evaluation
5. **Tool fixtures** for deterministic agent testing
6. **Multiple runs** for non-deterministic agents

---

## Experiment Configs

Experiment configs separate *what to test* from *how to evaluate*:

```yaml
# evals/configs/data_explorer.yaml
name: data_explorer_eval
agent: agents.data_explorer:DataExplorer
dataset: data_explorer

models:
  - google:gemini-3-flash-preview
  - anthropic:claude-sonnet-4-20250514

prompts:
  - py://agents.data_explorer.prompts:DEFAULT_PROMPT
  - xms://data_explorer/concise

# Assertions applied to ALL test cases
assert:
  - type: not-null
    field: recommended_asset
  - type: latency-budget
    max_seconds: 10

fixtures:
  tools: fixtures/tools/data_explorer.yaml
```

With 2 models and 2 prompts, the framework runs all 4 combinations and compares results side-by-side.

---

## Test Cases

Test cases combine inputs with assertions. Each assertion automatically becomes a reported metric.

### Single-Agent Test Case

```yaml
- name: gdp_search
  inputs:
    query: Find GDP data for the United States
    focus_areas: [economic]
  assert:
    - type: any-contains
      field: assets_found[*].asset_path
      value: gdp
    - type: count-range
      field: assets_found
      min: 1
      max: 5
    - type: contains
      field: rationale
      value: gdp
```

### Workflow Test Case

Workflow evaluation focuses on **outcomes over paths**. Asserting exact agent sequences or per-step outputs is brittle—agents often find valid alternative approaches that rigid evaluations would reject.

```yaml
- name: revenue_analysis
  workflow: supervisor_pipeline
  inputs:
    user_message: "Why did revenue drop in Q3?"

  # PRIMARY: Assert on final output
  assert:
    - type: not-null
      field: response
    - type: contains
      field: response
      value: revenue

  # SECONDARY: Workflow execution constraints
  workflow_assert:
    - type: no-errors
    - type: tool-call-valid
      tool: sql_execution
      assert:
        - type: is-valid-sql
          field: query
    - type: llm-judge
      judge: trajectory_quality
      threshold: 7

  # Capture full trajectory for debugging (not graded)
  trace: true
```

**`assert` vs `workflow_assert`:**
- `assert` — Evaluates the final output (what the agent returned)
- `workflow_assert` — Evaluates execution quality (how it got there)

**Workflow assertion types:**
- `no-errors` — No agent or tool raised an exception
- `tool-call-valid` — Validate tool call parameters meet constraints
- `agent-invoked` — Verify a required agent was called (without asserting order)
- `llm-judge` — Use an LLM to evaluate trajectory quality

Full trajectories are captured via OpenTelemetry instrumentation and stored with experiment results for debugging and analysis.

---

## Assertions to Metrics

Metrics are derived automatically from assertions—no separate configuration needed.

Each unique assertion becomes a metric (e.g., `recommended_asset_present: 94%`). Aggregate metrics include `assertion_pass_rate`, `case_pass_rate`, and `workflow_pass_rate`.

**Classification metrics** are auto-detected: when multiple test cases use `type: equals` on the same field, the framework computes accuracy, precision, recall, F1, and confusion matrix.

For the full assertion type reference, see `evals/docs/assertions.md`.

---

## Tool Fixtures

Agents interact with external data through tools (`search_assets`, `describe_asset`, `get_data`). Tool fixtures mock the underlying `shared.data` functions for deterministic testing.

**Fixture modes:**
- **mock**: Return canned responses from YAML (default, fast, deterministic)
- **live**: No mocking, call real services (integration tests)

**Config format:**
```yaml
# Experiment-level (applies to all cases)
fixtures:
  tools: fixtures/tools/data_explorer.yaml

# Per-case override
- name: live_integration_test
  inputs: { query: "GDP data" }
  fixtures: { tools: live }
  assert:
    - type: not-null
      field: recommended_asset
```

**Fixture file format:**
```yaml
# fixtures/tools/data_explorer.yaml
search:
  - input: { query: "gdp" }
    output: ["fred/gdp/usa", "fred/gdp/chn", "worldbank/gdp"]
  - input: { query: "unemployment" }
    output: ["bls/unemployment/national"]

describe:
  - input: { asset_path: "fred/gdp/usa" }
    output:
      is_partitioned: false
      schema: { date: datetime, value: float }
      row_count: 1200

get:
  - input: { asset_path: "fred/gdp/usa", limit: 5 }
    output:
      columns: [date, value]
      rows: [[2024-01-01, 28.3], [2024-04-01, 28.7]]
```

If no matching input is found, the framework raises an error (fail loudly).

Fixtures can be set at experiment level or overridden per test case.

---

## Tracing

Workflow tracing uses [OpenTelemetry](https://opentelemetry.io/) with [GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/). This provides:

- Auto-instrumentation for LangChain/LangGraph
- Standard span format for agent calls, tool invocations, and LLM requests
- Dual export to evaluation framework and observability backends (LangSmith, Datadog, etc.)

Traces are captured in-memory during evaluation and converted to `WorkflowTrace` for assertion processing.

---

## Multiple Runs

For non-deterministic agents, run multiple times and report pass rate:

```yaml
- name: gdp_search_fuzzy
  inputs:
    query: "Find GDP data for economic analysis"
  runs: 3
  assert:
    - type: any-contains
      field: assets_found[*].asset_path
      value: gdp
```

Reports `pass_rate: 66.7%` (2/3 runs passed).

---

## Concurrency

Rate limiting is handled per-provider at the `LLMClient` level using LangChain's `InMemoryRateLimiter`. This allows ExperimentSets to run all experiments in parallel—provider rate limits handle pacing automatically.

```python
# All providers use 5 requests/sec (300 RPM)
_rate_limiters = {
    "google": InMemoryRateLimiter(requests_per_second=5, max_bucket_size=10),
    "anthropic": InMemoryRateLimiter(requests_per_second=5, max_bucket_size=10),
    "openai": InMemoryRateLimiter(requests_per_second=5, max_bucket_size=10),
}
```

This separation of concerns keeps the evaluation runner simple while ensuring we don't exceed API limits.

---

## Extensibility

New assertion types can be added by implementing the base evaluator interface. Planned extensions include:

**LLM-as-Judge** — For subjective quality assessment where deterministic checks aren't sufficient:

```yaml
- type: llm-judge
  judge: interpretation_quality  # References a judge defined in evals/judges/
  field: rationale
  threshold: 7
```

Judges are defined separately and can themselves be evaluated for consistency and alignment.

**Ragas Metrics** — For RAG-based agents like DataExplorer:

```yaml
- type: ragas-faithfulness
  field: rationale
  threshold: 0.7

- type: ragas-context-precision
  threshold: 0.8
```

Ragas assertions require `retrieved_contexts` and optionally `reference` in the test case metadata.

---

## Interfaces

**CLI** — For CI, batch runs, and quick iteration:
```bash
just eval data_explorer              # Run evaluation
just eval data_explorer --sample 10  # Quick iteration
just eval-compare <id1> <id2>        # Compare experiments
```

**Notebooks** — For interactive development and visualization:

```python
from evals import Experiment, ExperimentSet
from evals.datasets import load_from_manifest

cases = load_from_manifest("intent_classifier")

comparison = await ExperimentSet(
    experiments=[
        Experiment(agent=IntentClassifier, model="gemini-flash", dataset=cases, ...),
        Experiment(agent=IntentClassifier, model="claude-sonnet", dataset=cases, ...),
    ]
).run(save=False)

comparison.print_comparison()
comparison.plot_metrics(fields=["task_accuracy", "mode_accuracy"])
```

**Storage** — Results stored locally in `.eval/` (SQLite metadata + Parquet results).

See `evals/README.md` for detailed usage.

### Example Output

```
$ just eval intent_classifier

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

## Consequences

### Benefits

1. **Unified approach**: One assertion syntax for single-agent and workflow evaluation
2. **Self-documenting tests**: Assertions embedded with inputs for easy review
3. **Automatic metrics**: No separate metrics configuration needed
4. **Reproducible**: Fixtures enable deterministic tests
5. **Extensible**: New assertion types can be added without framework changes
6. **Failure attribution**: Milestones show which agent failed and why

### Tradeoffs

1. Verbosity: Classification tests require multiple `type: equals` assertions
2. Learning curve: Team must learn assertion types
3. Workflow runner depends on LangGraph callback structure

---

## References

- [Anthropic: Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [pydantic-evals](https://ai.pydantic.dev/evals/)
- [DeepEval: AI Agent Evaluation](https://deepeval.com/guides/guides-ai-agent-evaluation)
- [promptfoo: Expected Outputs](https://www.promptfoo.dev/docs/configuration/expected-outputs/)
