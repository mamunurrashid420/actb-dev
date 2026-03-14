# ADR-004: Standardized Testset Generation

**Status:** Proposed  
**Date:** 2026-03-04  
**Supersedes:** None  
**Depends on:** ADR-002 (Evaluation Framework), ADR-003 (Observability), ADR-005 (Unified Streaming Architecture)

---

## 1. Context

ADR-002 defines how we evaluate agents: assertion-based test cases, tool fixtures, experiment configs, and automatic metric derivation. But it says nothing about how those test cases come into existence. Today, test data is hand-authored — 14 cases for IntentClassifier, 5 each for DataExplorer and VizDesigner. This creates three problems:

1. **Coverage is low.** The ADR-002 example shows 50 IntentClassifier cases; we have 14. Small datasets can't distinguish between a good prompt and a lucky prompt.

2. **Test authoring is unstructured.** Each agent's test data was created ad hoc. There is no shared process for deciding what inputs to generate, what fixture data to pair with them, or how to derive expected outcomes. This makes it hard to onboard new team members or scale to new agents.

3. **Three artifacts must be produced together.** A complete eval test case requires: (a) a user query as input, (b) fixture data that the agent's tools will return, and (c) assertions or reference answers that define correctness. Today these are authored separately with no tooling to keep them consistent. A query about "Q3 revenue by region" is meaningless if the fixture data doesn't contain revenue or region columns.

This ADR proposes a standardized testset generation pipeline that produces all three artifacts from a single data source, with both synthetic and production-capture paths.

---

## 2. Decision

Adopt a **three-track testset generation system**:

- **Track A — Synthetic generation** from XLake metadata and sample data, using an LLM to produce query–fixture–assertion triples.
- **Track B — Production harvest** via a Dagster pipeline that reads completed conversation turns from `conversation_events` (ADR-005), joins with Langfuse and PostHog data, and exports eval-ready YAML with product outcome annotations. Runs nightly or on-demand.
- **Track C — Ad hoc production capture** from individual Langfuse traces, converting specific agent runs into replayable test cases with fixture snapshots. Used for targeted debugging and edge case collection.

All three tracks produce output in the same format: YAML test cases + YAML fixture files compatible with the ADR-002 evaluation framework. A human review step is required before test cases enter the canonical dataset.

---

## 3. The Generation Problem

A complete test case for an ActBI agent is not just a query. It is a **triple**:

```
(user_input, fixture_data, expected_outcome)
```

Each component depends on the others:

- The **user input** must be a realistic question that an executive would ask about the data described in the fixtures.
- The **fixture data** must contain the schemas, tables, KPIs, and sample rows that make the query answerable — otherwise the agent will fail for the wrong reason.
- The **expected outcome** must be derivable from the fixture data — otherwise the assertion is testing luck, not capability.

The fundamental design choice is: **start from the data, not from the query.** The data determines what questions are valid. The questions determine what correct answers look like.

---

## 4. Track A — Synthetic Generation

### 4.1 Data Source: XLake Snapshots

Generation starts with a **data snapshot** — a frozen slice of XLake metadata for a specific tenant or the Northwind demo dataset. A snapshot contains:

```yaml
# evals/snapshots/northwind.yaml
snapshot: northwind
domain: sales
tables:
  - name: orders
    columns:
      - { name: order_id, type: integer, role: primary_key }
      - { name: customer_id, type: integer, role: foreign_key, references: customers.customer_id }
      - { name: order_date, type: date, role: temporal }
      - { name: total_amount, type: decimal, role: measure, unit: USD }
      - { name: region, type: varchar, role: dimension }
    row_count: 12400
    sample_rows:
      - [1001, 42, "2024-01-15", 2340.50, "Northeast"]
      - [1002, 17, "2024-01-16", 890.00, "West"]
      - [1003, 42, "2024-02-01", 1575.25, "Northeast"]

  - name: customers
    columns:
      - { name: customer_id, type: integer, role: primary_key }
      - { name: company_name, type: varchar, role: entity }
      - { name: segment, type: varchar, role: dimension, values: [Enterprise, SMB, Startup] }
    row_count: 850

kpis:
  - name: revenue
    formula: "SUM(orders.total_amount)"
    grain: [region, segment, order_date]
  - name: average_order_value
    formula: "AVG(orders.total_amount)"
    grain: [region, segment]

relationships:
  - { from: orders.customer_id, to: customers.customer_id, type: join, confidence: 0.98 }

external_signals:
  - { name: us_gdp_quarterly, source: fred, domain: economic }
```

Snapshots can be produced manually, exported from a live XLake tenant, or derived from the Northwind seed data.

### 4.2 Generation Pipeline

The generator is an LLM-based pipeline that takes a snapshot and produces test case triples. It runs as a CLI command:

```bash
just eval-generate \
  --snapshot northwind \
  --agent data_explorer \
  --count 30 \
  --difficulty mixed \
  --output evals/datasets/data_explorer/generated_batch_001.yaml
```

The pipeline has three stages:

**Stage 1 — Query Generation.** An LLM receives the snapshot metadata (table schemas, KPIs, relationships, sample rows) and a persona prompt describing the kinds of questions an executive would ask. It generates `count` diverse queries covering different difficulty levels, query patterns, and data domains.

The persona prompt varies by agent type:

| Agent Type | Persona | Example Queries |
|---|---|---|
| IntentClassifier | Executive asking varied question types | "Break down revenue by region", "What happened to sales?", "Import the Q3 report" |
| DataExplorer | Analyst looking for data sources | "Find GDP data for economic analysis", "What datasets cover customer churn?" |
| QueryBuilder | Executive asking analytical questions | "Compare Q3 vs Q2 revenue by segment", "Top 10 customers by order value" |
| VizDesigner | User requesting specific visualizations | "Show me a trend of revenue over time", "Compare regions side by side" |
| DataInterpreter | Executive wanting explanations | "Why did revenue drop in Q3?", "What's driving the margin change?" |

The generator enforces diversity constraints: no more than 20% of queries should target the same table, at least 30% should involve joins, and difficulty should be distributed across easy/medium/hard.

**Stage 2 — Fixture Derivation.** For each generated query, the pipeline constructs the fixture data the agent's tools would need to return. This is deterministic, not LLM-generated:

- **For `search` fixtures:** The snapshot's table names and KPI names are used to construct plausible search results matching the query's domain.
- **For `describe` fixtures:** Schema information is copied directly from the snapshot for the relevant tables.
- **For `get` fixtures:** Sample rows from the snapshot are filtered/aggregated to produce realistic result sets that would answer the query.

The fixture derivation uses a rule-based engine, not an LLM. This avoids the problem of an LLM generating fixtures that are inconsistent with the snapshot schema.

**Stage 3 — Assertion Generation.** This is the hardest part. The pipeline produces assertions at two levels:

*Structural assertions* are generated deterministically from the query + fixture combination:
- If the query mentions a table name → `any-contains` on the output's asset references
- If the query is analytical → `not-null` on key output fields
- Count bounds based on fixture data cardinality
- `latency-budget` from agent-level defaults

*Semantic assertions* are generated by an LLM that receives both the query and the fixture data, then produces:
- `contains` assertions for key terms that should appear in rationale
- `equals` assertions for classification agents (task, mode, job)
- Reference answers for future Ragas faithfulness scoring

Both types are emitted as YAML assertions in the ADR-002 format.

### 4.3 Output Format

The generator produces two files per batch:

**Test cases** — ready to use with the eval framework:
```yaml
# evals/datasets/data_explorer/generated_batch_001.yaml
- name: gen_revenue_by_region_001
  generated: true
  snapshot: northwind
  difficulty: medium
  inputs:
    query: "Find data about revenue broken down by region"
    focus_areas: [sales]
  assert:
    - type: any-contains
      field: assets_found[*].asset_path
      value: orders
    - type: count-range
      field: assets_found
      min: 1
      max: 5
    - type: contains
      field: rationale
      value: region
  metadata:
    reference: "The orders table contains total_amount (revenue) and region columns"
    retrieved_contexts: []  # populated at eval time from fixture responses
```

**Fixture data** — paired with the test cases:
```yaml
# evals/fixtures/tools/data_explorer_gen_batch_001.yaml
search:
  - input: { query: "revenue region" }
    output: ["northwind/orders", "northwind/customers"]
  - input: { query: "revenue broken down by region" }
    output: ["northwind/orders"]

describe:
  - input: { asset_path: "northwind/orders" }
    output:
      is_partitioned: false
      schema:
        order_id: integer
        customer_id: integer
        order_date: date
        total_amount: decimal
        region: varchar
      row_count: 12400

get:
  - input: { asset_path: "northwind/orders", limit: 5 }
    output:
      columns: [order_id, customer_id, order_date, total_amount, region]
      rows:
        - [1001, 42, "2024-01-15", 2340.50, "Northeast"]
        - [1002, 17, "2024-01-16", 890.00, "West"]
        - [1003, 42, "2024-02-01", 1575.25, "Northeast"]
```

### 4.4 Human Review Gate

Generated test cases are never added to canonical datasets automatically. The workflow is:

1. Generator outputs to `evals/datasets/<agent>/staging/`
2. Developer reviews staged cases, edits or discards as needed
3. Approved cases are moved to `evals/datasets/<agent>/` and committed
4. The `generated: true` flag and `snapshot` reference are preserved for provenance

A review helper command shows each case with its fixture data for quick accept/reject:

```bash
just eval-review data_explorer --batch generated_batch_001
```

---

## 5. Track B — Production Harvest (Dagster Pipeline)

Hand-authored test cases cover known patterns. Production harvest covers the long tail — real user questions that reveal failure modes no one anticipated.

A Dagster pipeline reads completed conversation turns from `conversation_events` (ADR-005), filters for quality, and exports eval-ready YAML that the existing framework consumes without modification. The pipeline runs nightly or on-demand.

### 5.1 Source Contract

The pipeline depends on the `conversation_events` table (ADR-005 §6). Each conversation turn is identified by `(conversation_id, message_id)` and contains a sequence of `ActBIEvent` records ordered by `seq`. A turn is complete when it contains a `done` event.

Key fields consumed:

| Field | Usage |
|---|---|
| `payload` | The complete agent output (canonical JSON of the domain protobuf). Becomes the eval `reference_output`. |
| `event_type` | Determines which assertion derivation rules apply. |
| `variant` | Enables segmenting by experiment arm (from ADR-003 feature flags). |
| `tenant_id` | Enforces tenant isolation in exported datasets. |
| `agent_node` | Identifies which agent produced the output, used for routing to per-agent datasets. |

### 5.2 Pipeline Stages

#### Stage 1: Harvest

Query `conversation_events` for completed turns not yet exported. Join with Langfuse exports on `conversation_id` for token costs and latency. Join with PostHog exports on `conversation_id` for product outcomes.

```python
@asset(deps=[conversation_events])
def eval_candidates(db, langfuse_export, posthog_export):
    """Identify conversation turns suitable for eval datasets."""
    turns = db.sql("""
        SELECT
            ce.conversation_id,
            ce.message_id,
            ce.tenant_id,
            ce.variant,
            first_value(ce.payload->>'query') FILTER (WHERE ce.event_type = 'status')
                OVER w AS user_query,
            jsonb_agg(
                jsonb_build_object(
                    'event_type', ce.event_type,
                    'payload', ce.payload,
                    'agent_node', ce.agent_node
                ) ORDER BY ce.seq
            ) FILTER (WHERE ce.event_type IN (
                'chart_spec','insight','recommendation','error'
            )) OVER w AS outputs
        FROM conversation_events ce
        WHERE ce.event_type != 'reasoning'
        WINDOW w AS (PARTITION BY ce.conversation_id, ce.message_id)
    """)
    return turns
```

#### Stage 2: Filter and Annotate

Not every production turn is a good eval case. Filter criteria:

- Turn completed without errors (no `error` event type in outputs)
- Produced at least one `chart_spec` or `insight`
- User query longer than 10 characters (skip "hi", "thanks", etc.)

Annotate with product outcomes from PostHog:

- `user_engaged` — did the user act on the output (`visualization_chart_pinned`, `decision_insight_clicked`)?
- `led_to_dashboard` — did the conversation produce a published dashboard (`visualization_dashboard_published`)?

Turns where users engaged are higher-quality positive examples. This annotation enables **weighted regression testing** — failures on engaged cases are more serious than failures on ignored cases.

```python
@asset(deps=[eval_candidates])
def filtered_eval_cases(candidates, posthog_outcomes):
    """Filter for quality and annotate with product outcomes."""
    cases = []
    for turn in candidates:
        if turn.has_error:
            continue
        if not turn.outputs:
            continue
        if len(turn.user_query) < 10:
            continue

        outcome = posthog_outcomes.get(turn.conversation_id)
        turn.user_engaged = outcome and outcome.reached_milestone(
            "visualization_chart_pinned", "decision_insight_clicked"
        )
        turn.led_to_dashboard = outcome and outcome.reached_milestone(
            "visualization_dashboard_published"
        )
        cases.append(turn)
    return cases
```

#### Stage 3: Export as Eval YAML

Transform filtered turns into the standard test case format. Group by primary agent. Append to existing datasets with deduplication by case name.

```python
@asset(deps=[filtered_eval_cases])
def export_eval_datasets(cases, output_dir="evals/datasets/production/"):
    """Export as YAML consumable by the eval framework."""
    by_agent = defaultdict(list)

    for case in cases:
        agent_name = _infer_agent(case.outputs)

        eval_case = {
            "name": f"prod_{case.conversation_id}_{case.message_id[:8]}",
            "inputs": {"query": case.user_query},
            "metadata": {
                "source": "production",
                "conversation_id": case.conversation_id,
                "tenant_id": case.tenant_id,
                "variant": case.variant,
                "user_engaged": case.user_engaged,
                "led_to_dashboard": case.led_to_dashboard,
                "harvested_at": datetime.utcnow().isoformat(),
            },
        }

        assertions = _derive_assertions(case.outputs)
        if assertions:
            eval_case["assert"] = assertions

        eval_case["reference_output"] = _extract_primary_output(case.outputs)
        by_agent[agent_name].append(eval_case)

    for agent_name, agent_cases in by_agent.items():
        path = Path(output_dir) / f"{agent_name}.yaml"
        existing = yaml.safe_load(path.read_text()) if path.exists() else []
        existing_names = {c["name"] for c in existing}
        new_cases = [c for c in agent_cases if c["name"] not in existing_names]
        yaml.dump(existing + new_cases, path.open("w"))
```

### 5.3 Production Assertion Derivation

Production assertions are constraint-based, not exact-match. They capture "the production agent produced output with these properties" so new versions can be verified against the same bar.

```python
def _derive_assertions(outputs: list[dict]) -> list[dict]:
    assertions = []

    for out in outputs:
        match out["event_type"]:
            case "chart_spec":
                assertions.append({"type": "not-null", "field": "chart_type"})
                assertions.append({
                    "type": "equals",
                    "field": "chart_type",
                    "value": out["payload"].get("chart_type"),
                })
                assertions.append({
                    "type": "count-range",
                    "field": "series",
                    "min": 1,
                })

            case "insight":
                assertions.append({"type": "not-null", "field": "summary"})
                conf = out["payload"].get("confidence", 0)
                if conf > 0:
                    assertions.append({
                        "type": "gte",
                        "field": "confidence",
                        "value": round(conf - 0.1, 2),  # 10% tolerance
                    })

            case "recommendation":
                assertions.append({"type": "not-null", "field": "summary"})

    return assertions
```

Key principles:

- `chart_spec` → assert chart type stays the same (bar should stay bar, not become pie), assert at least one series
- `insight` → assert non-null summary, assert confidence within 10% tolerance of production baseline
- `recommendation` → assert non-null summary
- Never assert exact payload match — agents are non-deterministic

### 5.4 Production Metadata Schema

Every production-harvested test case includes a `metadata` block:

| Field | Type | Purpose |
|---|---|---|
| `source` | `"production"` | Distinguishes from hand-authored and synthetic cases |
| `conversation_id` | string | Links back to full event log for debugging |
| `tenant_id` | string | Enforces tenant isolation |
| `variant` | string | Experiment arm that produced this output (from ADR-003 flags) |
| `user_engaged` | boolean | User acted on the output (from PostHog) |
| `led_to_dashboard` | boolean | Conversation produced a published dashboard |
| `harvested_at` | ISO datetime | When the case was exported |

### 5.5 Data Sensitivity and Tenant Isolation

Production queries contain tenant data. Exported datasets must be tenant-scoped and never cross tenant boundaries:

- Each exported YAML file is scoped to a single tenant
- Dataset directory structure: `evals/datasets/production/{tenant_id}/{agent_name}.yaml`
- The `tenant_id` in metadata enforces this at the data level
- CI pipelines running production datasets must respect tenant isolation — never merge datasets across tenants

### 5.6 Deduplication

Cases are deduplicated by `name`, which includes `conversation_id` and `message_id` prefix. If the nightly pipeline encounters a turn that was already exported, it skips it. The production dataset grows monotonically — new cases append, existing cases are never modified.

---

## 6. Track C — Ad Hoc Capture (Individual Traces)

Track C is a lightweight, manual complement to Track B. Instead of harvesting in bulk, a developer captures a specific Langfuse trace — typically a failure, edge case, or interesting interaction discovered during debugging.

### 6.1 Usage

```bash
just eval-capture \
  --agent data_explorer \
  --trace-id lf_trace_abc123 \
  --output evals/datasets/data_explorer/staging/
```

### 6.2 Capture Process

1. **Fetch trace** from Langfuse API using `conversation_id` or trace ID.
2. **Extract tool calls** — each tool invocation becomes a fixture entry (input → output pairs).
3. **Extract inputs** — the original user query and any context passed to the agent.
4. **Generate assertions** — structural assertions are derived from the actual output. An LLM reviews the output and generates semantic assertions about what a correct response should contain.
5. **Output** as staged YAML test case + fixture file.

### 6.3 Selective Capture

The pipeline supports filters for batch capture of interesting traces:

```bash
# Capture failures — cases where the agent errored or produced low-quality output
just eval-capture --agent data_explorer --filter failures --last 7d

# Capture slow runs — latency outliers
just eval-capture --agent data_explorer --filter slow --threshold 15s --last 7d

# Capture by Langfuse score — cases where LLM-judge or human scored low
just eval-capture --agent data_explorer --filter low-score --threshold 5 --last 7d
```

Track C cases go through the same human review gate as synthetic and harvested cases. The key difference from Track B is that Track C captures **full fixture snapshots** (tool call inputs and outputs) for replay, while Track B captures **assertions about the output shape** for regression testing.

---

## 7. Agent-Specific Generation Strategies

Different agent types require different generation approaches because their input/output shapes and tool interactions differ significantly.

### 6.1 IntentClassifier

**Input shape:** A user message (natural language query).  
**Output shape:** Structured classification — `task`, `mode`, `job` fields.  
**Fixtures:** None (no tool calls).  
**Assertion type:** `equals` on each classification field.

**Generation strategy:** The generator needs the full taxonomy of task/mode/job values. It produces diverse phrasings for each category, including edge cases (ambiguous queries, multi-intent, conversational vs. analytical). Expected classifications are deterministic — the LLM that generates the query also produces the correct label, since it's generating from the taxonomy.

```yaml
- name: gen_intent_revenue_breakdown_001
  generated: true
  inputs:
    query: "Can you break down our Q3 numbers by product line?"
  assert:
    - type: equals
      field: task
      value: query
    - type: equals
      field: mode
      value: reporter
    - type: equals
      field: job
      value: breakdown
```

Diversity constraints: at least 5 examples per (task, mode) pair, with adversarial examples for commonly confused categories.

### 6.2 DataExplorer

**Input shape:** A search query + optional focus areas.  
**Output shape:** Found assets, rationale, recommended asset.  
**Fixtures:** `search`, `describe`, `get` tool responses.  
**Assertion type:** Constraint-based (`any-contains`, `count-range`, `contains`).

**Generation strategy:** Start from snapshot tables and KPIs. For each table, generate 3–5 queries that would lead an explorer to find it. Fixtures are derived directly from the snapshot schema. Assertions check that the agent found relevant assets and produced coherent rationale.

### 6.3 QueryBuilder

**Input shape:** An analytical question + schema context.  
**Output shape:** SQL query + explanation.  
**Fixtures:** Schema descriptions, sample data.  
**Assertion type:** `is-valid-sql`, `contains` on referenced tables/columns, `not-null` on explanation.

**Generation strategy:** This agent benefits from a **ground truth SQL** approach. The generator produces a query, writes a reference SQL against the snapshot schema, and derives assertions from the SQL structure (which tables are joined, which columns are selected, which aggregations are used). The reference SQL is stored in `metadata.reference_sql` for debugging but is not used as an exact-match assertion — the agent may produce valid alternative SQL.

### 6.4 VizDesigner

**Input shape:** Data summary + user intent.  
**Output shape:** ChartSpec (chart type, encodings, styling).  
**Fixtures:** Data shape descriptions.  
**Assertion type:** `equals` on chart type, `evaluator` for encoding correctness (pydantic-evals `EncodingFieldsPresent`, `SafetyRules`).

**Generation strategy:** Generate data shapes (time series, categorical breakdown, correlation, distribution) and pair each with appropriate chart types. Assertions use both YAML assertions for chart type and pydantic-evals evaluators for structural correctness.

### 6.5 Workflow (Supervisor Pipeline)

**Input shape:** End-to-end user message.  
**Output shape:** Full response + agent trajectory.  
**Fixtures:** All tool responses across all agents in the pipeline.  
**Assertion type:** `assert` on final output + `workflow_assert` on execution quality.

**Generation strategy:** Compose from single-agent test cases. A workflow test case combines an IntentClassifier input with DataExplorer/QueryBuilder/VizDesigner fixtures. The generator selects compatible single-agent cases and assembles them into an end-to-end scenario.

---

## 8. Assertion Derivation Rules

The hardest part of testset generation is producing meaningful assertions without a human writing each one. The framework uses a tiered approach:

### 8.1 Tier 1 — Deterministic (rule-based, no LLM)

These are derived automatically from the query + fixture combination:

| Rule | Condition | Assertion Produced |
|---|---|---|
| Output exists | Always | `type: not-null, field: <primary_output_field>` |
| Asset found | Query mentions a table in fixtures | `type: any-contains, field: assets_found[*].asset_path, value: <table>` |
| Count bounded | Fixture has N matching results | `type: count-range, field: assets_found, min: 1, max: N+2` |
| Classification | Agent is IntentClassifier | `type: equals, field: task/mode/job, value: <generated_label>` |
| Latency | Always | `type: latency-budget, max_seconds: <agent_default>` |
| SQL validity | Agent is QueryBuilder | `type: is-valid-sql, field: query` |

### 8.2 Tier 2 — LLM-derived (generated, high confidence)

An LLM examines the query, fixture data, and expected output shape, then generates:

- `contains` assertions for key terms that must appear in rationale
- Reference answers for Ragas faithfulness scoring (stored in `metadata.reference`)
- Quality rubrics for future LLM-as-Judge assertions (stored in `metadata.rubric`)

### 8.3 Tier 3 — Human-authored (review step)

During the human review gate, reviewers can add, modify, or remove assertions. This is where domain-specific expectations get encoded — things like "a revenue question should never recommend the weather dataset" that neither rules nor an LLM would reliably produce.

---

## 9. Dataset Management

### 9.1 Dataset Manifest

Each agent's dataset is tracked by a manifest file:

```yaml
# evals/datasets/data_explorer/manifest.yaml
agent: data_explorer
target_size: 50
current_size: 45

sources:
  - file: core_cases.yaml
    count: 5
    origin: manual
    author: nikos
    date: 2026-01-23

  - file: generated_batch_001.yaml
    count: 20
    origin: synthetic
    snapshot: northwind
    date: 2026-03-01
    reviewed_by: nikos

  - file: captured_edge_cases.yaml
    count: 5
    origin: capture
    trace_ids: [lf_abc123, lf_def456, ...]
    date: 2026-03-04
    reviewed_by: nikos

  - file: production/tenant_xyz/data_explorer.yaml
    count: 15
    origin: production
    tenant_id: tenant_xyz
    harvested: 2026-03-04
    reviewed_by: nikos

coverage:
  tables_referenced: [orders, customers, products, suppliers]
  difficulty_distribution: { easy: 12, medium: 20, hard: 13 }
  query_patterns: { single_table: 15, join: 18, aggregation: 25, temporal: 22 }
```

The manifest makes dataset composition visible and auditable.

### 9.2 Dataset Hygiene

- **Deduplication:** Before adding a batch, check for semantic similarity against existing cases (embedding-based).
- **Balance checks:** The manifest tracks difficulty distribution and query pattern coverage. The generator can be asked to fill gaps: `just eval-generate --snapshot northwind --agent data_explorer --fill-gaps`.
- **Staleness:** When the agent's tool interface changes, fixtures must be regenerated. The snapshot version pins the schema, so old test cases remain valid for regression testing even as the live schema evolves.

---

## 10. Integration with ADR-002, ADR-003, and ADR-005

### 10.1 ADR-002 (Eval Framework)

Generated test cases and fixtures use the exact same YAML format that ADR-002's `Experiment` runner consumes. No adapter needed — generated batches are added to the dataset manifest and referenced from experiment configs as usual.

The `metadata.reference` field produced by the generator enables future Ragas assertions. When the `ragas-faithfulness` assertion type is implemented, it reads `reference` from metadata and `retrieved_contexts` from fixture responses captured at eval time.

### 10.2 ADR-003 (Observability)

Track B's Dagster pipeline joins with Langfuse exports (token costs, latency, trace spans) and PostHog exports (product outcomes, funnel milestones) using `conversation_id` as the join key — the same key ADR-003 establishes for cross-system analysis.

Track C uses the Langfuse API directly to fetch individual traces. Authentication uses the same `LangfuseSettings` from the DI container (ADR-003 §4.1).

The `variant` field in production metadata comes from ADR-003's `AgentConfig` — the feature flag variant that was active when the conversation ran. This enables segmenting eval datasets by experiment arm to measure whether a flag variant improved or degraded quality.

### 10.3 ADR-005 (Unified Streaming Architecture)

Track B depends on the `conversation_events` table defined in ADR-005 §6. The pipeline consumes `ActBIEvent` records and uses their `event_type` field to route assertion derivation. The `payload` field contains the canonical JSON serialization of the domain protobuf, which becomes the `reference_output` in exported test cases.

The pipeline only reads completed turns (those containing a `done` event) and never reads `reasoning` events — these are ephemeral streaming tokens not relevant to eval assertions.

---

## 11. Implementation Plan

| Phase | Task | Depends On | Done When |
|---|---|---|---|
| 1 | Define snapshot format and create Northwind snapshot | XLake schema | `evals/snapshots/northwind.yaml` validated |
| 2 | Build query generator (Stage 1) with persona prompts per agent | Phase 1 | `just eval-generate --agent intent_classifier --count 30` produces queries |
| 3 | Build fixture derivation engine (Stage 2) | Phase 1 | Fixtures auto-generated from snapshot, consistent with schema |
| 4 | Build deterministic assertion generator (Tier 1) | Phase 2, Phase 3 | Structural assertions produced for every generated case |
| 5 | Build LLM assertion generator (Tier 2) | Phase 4 | `contains` and `reference` assertions produced |
| 6 | Build review CLI (`just eval-review`) | Phase 4 | Developer can accept/reject/edit staged cases |
| 7 | Build manifest tracking | Phase 6 | `manifest.yaml` updated automatically on add/remove |
| 8 | Build production harvest Dagster pipeline (Track B) | ADR-005 `conversation_events` live, ADR-003 Langfuse + PostHog exports | `just eval-harvest` produces tenant-scoped YAML |
| 9 | Build ad hoc capture CLI (Track C) | ADR-003 Langfuse live | `just eval-capture --trace-id <id>` produces test case + fixtures |
| 10 | Generate initial datasets (30+ cases per agent) | Phase 6 | IntentClassifier, DataExplorer, QueryBuilder, VizDesigner datasets expanded |
| 11 | Integrate Ragas `metadata.reference` with planned `ragas-faithfulness` assertion | ADR-002 Ragas implementation | Faithfulness scoring uses generated references |
| 12 | CI integration for nightly production regression | Phase 8 | `just eval <agent> --dataset production/tenant_xyz` runs in GitHub Actions |

Phases 1–7 can proceed immediately. Phase 8 requires the `conversation_events` table (ADR-005) and Langfuse/PostHog exports to be running. Phase 9 requires Langfuse to be in production (ADR-003). Phase 11 depends on the Ragas assertion type being implemented in the eval framework.

---

## 12. Consequences

### Benefits

1. **Consistent triple generation.** Query, fixture, and assertion are always produced together from the same data source — no orphaned test cases or mismatched fixtures.
2. **Scalable.** Going from 5 to 50 to 500 cases per agent is a `--count` flag, not weeks of manual work.
3. **Three complementary tracks.** Synthetic covers breadth and edge cases; production harvest covers real-world patterns at scale with product outcome annotations; ad hoc capture targets specific failures and debugging scenarios.
4. **Auditable.** Every test case carries provenance: which snapshot, trace, or conversation it came from, who reviewed it, when.
5. **Framework-compatible.** Output format is identical to ADR-002's existing YAML format — no migration needed.
6. **Ragas-ready.** Generated `metadata.reference` and fixture-derived `retrieved_contexts` provide exactly what Ragas faithfulness and context precision metrics need.
7. **Production regression.** Eval datasets grow automatically from real usage, catching failure modes hand-authored cases miss. Product outcome annotations enable weighted regression — failures on cases where users engaged are treated as more serious.

### Tradeoffs

1. **LLM cost for generation.** Each synthetic generation batch requires LLM calls for query generation and Tier 2 assertions. Mitigated by batching and using cheaper models (Gemini Flash) for generation.
2. **Human review bottleneck.** Every generated case must be reviewed before entering the canonical dataset. This is intentional — auto-generated assertions can be wrong, and bad test cases are worse than no test cases.
3. **Snapshot maintenance.** As the XLake schema evolves, snapshots may drift. Versioning the snapshot and pinning test cases to snapshot versions mitigates this.
4. **Fixture completeness.** The rule-based fixture derivation (Track A) may not anticipate every tool call sequence an agent might make. Fail-loudly behavior (from ADR-002) catches this at eval time.
5. **Production pipeline dependencies.** Track B depends on ADR-005's `conversation_events` schema and ADR-003's PostHog/Langfuse export availability. These must be operational before the harvest pipeline can run.

---

## References

- [ADR-002: Evaluation Framework Design](./002-evaluation-framework.md)
- [ADR-003: Observability & Feature Flag Strategy](./ADR-003-Observability-FeatureFlags.md)
- ADR-005: Unified Streaming Architecture (`conversation_events` schema, `ActBIEvent` contract)
- [Ragas: Testset Generation](https://docs.ragas.io/en/latest/concepts/testset_generation.html)
- [Anthropic: Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [ARES: An Automated Evaluation Framework for RAG Systems](https://arxiv.org/abs/2311.09476)
