---
type: action-implementation
action: selection
chart-type: funnel_chart
aliases: [funnel, conversion funnel, sales funnel, pipeline]
data-pattern: sequential-decreasing
family: evolution
priority: P2
tags: [selection, funnel, conversion, pipeline, stages]
---

# Selection: Funnel Chart

Shows sequential stages where values typically decrease at each step.

## When to Use

- **Conversion pipelines**: Website visitors → leads → customers
- **Sales funnels**: Prospects → opportunities → closed deals
- **Process drop-off**: Where are people leaving?
- **Sequential stages**: Natural progression with attrition

### Data Pattern

- ORDERED CATEGORIES (stages)
- 1 MEASURE (count/value at each stage)
- Values typically decrease from first to last

### User Intent Signals

Queries that suggest funnel chart:
- "Conversion funnel..."
- "Where are people dropping off..."
- "Pipeline stages..."
- "Step-by-step breakdown..."

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| Values don't decrease | Not a funnel pattern | Bar Chart |
| No sequential stages | Funnel implies order | Bar Chart |
| Comparing across categories | Funnel is single flow | Grouped Bar |
| Precise comparison | Widths hard to compare | Bar Chart |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| CATEGORY | Yes | Stage names (ordered) |
| MEASURE | Yes | Value at each stage |

## Selection Decision

```
IF hasOrderedStages:
    AND valuesTendToDecrease:
    AND intent == "conversion" OR "funnel" OR "drop-off":
        → Funnel Chart
```

## Variants

### Tapered Funnel
Classic funnel shape, width proportional to value.

### Stacked Bar Funnel
Horizontal bars decreasing in width.

### Funnel with Conversion Rates
Shows percentage change between stages.

## Critical Rules

> **Stages must be sequential.**

Funnel implies a flow from first to last stage.

> **Width should encode value.**

The visual narrowing shows attrition.

> **Show conversion rates.**

The story is often in the drop-off percentages, not just the absolute values.

## See Also

- [Selection Interface](./selection.md)
- [Bar Chart (Horizontal)](./selection-bar-chart-horizontal.md) — For non-sequential comparison
