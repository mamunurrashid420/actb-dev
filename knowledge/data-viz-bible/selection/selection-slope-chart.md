---
type: action-implementation
action: selection
chart-type: slope_chart
aliases: [slope graph, before-after chart, slopegraph]
data-pattern: two-point-comparison
family: evolution
priority: P1
tags: [selection, slope, comparison, change, before-after]
---

# Selection: Slope Chart

Shows change between exactly two time points using connected lines.

## When to Use

- **Before/after comparison**: Q1 vs Q4, 2020 vs 2024
- **Exactly two time points**: Not for multiple periods
- **Comparing many items**: Works with 5-20 items
- **Emphasizing direction of change**: Slopes show up/down clearly

### Data Pattern

- 1 DIMENSION (items) + 1 MEASURE + 2 time points
- Each item has exactly 2 values
- Lines connect the two points

### User Intent Signals

Queries that suggest slope chart:
- "Change from X to Y..."
- "Before and after..."
- "Compare two periods..."
- "How did rankings change..."

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| More than 2 time points | Slope only shows 2 | Line Chart |
| Single item | No comparison | KPI with delta |
| Many items (>20) | Too many crossing lines | Grouped Bar |
| Precise values matter more | Hard to read exact | Table |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| DIMENSION | Yes | Item labels |
| MEASURE | Yes | Values |
| TEMPORAL | Yes | Exactly 2 time points |

## Selection Decision

```
IF timePoints == 2:
    AND dimensions == 1:
    AND intent == "change" OR "before/after":
    AND itemCount <= 20:
        → Slope Chart
    
    AND timePoints > 2:
        → Line Chart
```

## Variants

### Basic Slope Chart
Lines connecting left and right points.

### Ranked Slope Chart
Y-axis shows rank instead of value. Emphasizes position changes.

### Highlighted Slope Chart
One or few lines emphasized, others gray.

## Critical Rules

> **Use only for exactly 2 time points.**

More time points need a line chart.

> **Label both endpoints.**

Values or labels at start and end help readability.

> **Watch for crossing lines.**

Many items with similar values create spaghetti. Consider highlighting.

## See Also

- [Selection Interface](./selection.md)
- [Line Chart](./selection-line-chart.md) — For multiple time points
- [Bar Chart (Grouped)](./selection-bar-chart-grouped.md) — Alternative for 2-period comparison
