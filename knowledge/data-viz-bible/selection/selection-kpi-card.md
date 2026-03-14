---
type: action-implementation
action: selection
chart-type: kpi_card
aliases: [KPI, metric card, big number, scorecard, single value, headline number]
data-pattern: single-value
family: summary
priority: P0
tags: [selection, kpi, metric, summary, single-value]
---

# Selection: KPI Card

Displays a single key metric prominently, often with comparison or trend indicator.

## When to Use

- **Single headline number**: Total revenue, count, percentage
- **Executive summary**: The one number that matters most
- **Dashboard headers**: Key metrics at a glance
- **Performance indicators**: With delta/change from comparison period

### Data Pattern

- 0 DIMENSIONS + 1 MEASURE + 1 row (basic)
- 0 DIMENSIONS + 2 MEASURES + 1 row (with comparison/delta)
- Aggregated/summarized data

### User Intent Signals

Queries that suggest a KPI card:
- "What is the total..."
- "Show me the current..."
- "How much/many..."
- "What's our [metric]..."
- Single number questions

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| Multiple values to compare | Can't show comparison | Bar Chart |
| Trend over time | Loses temporal context | Line Chart, Sparkline |
| Distribution of values | Single number hides spread | Histogram |
| Breakdown by category | Aggregation hides detail | Bar Chart, Table |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| MEASURE | Yes | The primary value to display |
| MEASURE (2nd) | No | Comparison value for delta calculation |

### Calculated Fields

- **Delta**: Current - Previous (or % change)
- **Trend direction**: Up/Down/Flat

## Selection Decision

```
IF rowCount == 1:
    AND dimensions == 0:
    AND measures == 1:
        → KPI Card (basic)
    
    AND dimensions == 0:
    AND measures == 2:
        → KPI Card (with comparison)

IF intent == "what is the total" OR "current value":
    → Aggregate data → KPI Card
```

## Variants

### Basic KPI
Value only with label.

### KPI with Delta
Value + change from previous period.

### KPI with Sparkline
Value + mini trend line.

### KPI with Target
Value + progress toward goal.

## Critical Rules

> **One metric per card.**

KPI cards show a single number. Multiple metrics need multiple cards or a different visualization.

> **Context matters.**

A number without context is meaningless. Include label, unit, and ideally comparison/delta.

> **Sentiment should be clear.**

If the number is good or bad, make it visually obvious (color, icon).

## See Also

- [Selection Interface](./selection.md) — Decision tree
- [Data Table](./selection-data-table.md) — For multiple metrics
