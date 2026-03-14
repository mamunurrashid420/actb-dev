# Assertion Reference

Assertions define expected behaviors for agent outputs. They can be used at the experiment level (apply to all test cases) or per test case.

## Field Path Syntax

| Path | Meaning |
|------|---------|
| `field` | Top-level field |
| `nested.field` | Nested object field |
| `array[0]` | First array element |
| `array[*]` | All array elements (for any/all checks) |
| `array[*].field` | Field from all array elements |

---

## Existence Checks

```yaml
# Field is not null/undefined
- type: not-null
  field: recommended_asset

# Field is null/undefined
- type: is-null
  field: error_message
```

---

## Equality Checks

```yaml
# Exact equality
- type: equals
  field: validation.passed
  value: true

# Field is one of allowed values
- type: one-of
  field: chart_type
  values: [bar, line, scatter, table]
```

---

## Numeric Comparisons

```yaml
# Greater than threshold
- type: greater-than
  field: confidence
  value: 0.8

# Less than threshold
- type: less-than
  field: error_count
  value: 5

# Within range (inclusive)
- type: between
  field: quality.completeness
  min: 0.9
  max: 1.0
```

---

## String Checks

```yaml
# Contains substring (case-insensitive by default)
- type: contains
  field: rationale
  value: gdp

# Case-sensitive contains
- type: contains
  field: sql
  value: SELECT
  case_sensitive: true

# Regex match
- type: matches
  field: asset_path
  pattern: ^gold/economic/.*

# Starts with prefix
- type: starts-with
  field: response
  value: "Based on"

# Ends with suffix
- type: ends-with
  field: sql
  value: ";"
```

---

## Array Checks

```yaml
# Array length in range
- type: count-range
  field: assets_found
  min: 1
  max: 10

# Array length exactly
- type: count
  field: insights
  value: 3

# Any element contains value
- type: any-contains
  field: assets_found[*].asset_path
  value: gdp

# All elements contain value
- type: all-contain
  field: updates[*].status
  value: success

# Array includes specific value
- type: includes
  field: tags
  value: economic
```

---

## Domain-Specific Checks

```yaml
# Valid SQL syntax
- type: is-valid-sql
  field: sql

# SQL contains no mutations (SELECT only)
- type: sql-no-mutation
  field: sql

# Valid JSON
- type: is-json
  field: response_body

# Matches JSON schema
- type: json-schema
  field: output
  schema:
    type: object
    required: [id, name]
```

---

## Resource Budgets

```yaml
# Maximum latency
- type: latency-budget
  max_seconds: 10

# Maximum token usage
- type: token-budget
  max_tokens: 50000
```

---

## Negation

Any assertion can be negated with `not: true`:

```yaml
- type: contains
  field: response
  value: "I don't know"
  not: true  # Fails if response contains "I don't know"
```

---

## Workflow Assertions

These apply only to workflow test cases (used in `workflow_assert`):

```yaml
# Validates agent execution order
- type: agent-sequence
  expected: [IntentClassifier, Supervisor, QueryBuilder]

# Fails if any agent raised an exception
- type: no-errors

# Validates specific agent was called
- type: agent-invoked
  agent: QueryBuilder
  times: 1  # optional
```

---

## Planned Extensions

### LLM-as-Judge

```yaml
- type: llm-judge
  judge: interpretation_quality  # Defined in evals/judges/
  field: rationale
  threshold: 7
```

### Ragas Metrics

For RAG-based agents. Requires `retrieved_contexts` in test case metadata.

```yaml
- type: ragas-faithfulness
  field: rationale
  threshold: 0.7

- type: ragas-context-precision
  threshold: 0.8

- type: ragas-context-recall
  threshold: 0.7

- type: ragas-answer-relevancy
  threshold: 0.8
```
