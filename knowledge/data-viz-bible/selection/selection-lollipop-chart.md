---
type: action-implementation
action: selection
chart-type: lollipop_chart
aliases: [lollipop, dot plot with stem, cleveland dot plot]
data-pattern: categorical-single-measure
family: ranking
priority: P2
tags: [selection, lollipop, ranking, comparison, minimal]
---

# Selection: Lollipop Chart

A minimalist alternative to bar charts using dots connected to baseline by thin lines.

## When to Use

- **Ranking with less visual weight**: Cleaner than bars
- **Many categories**: Less ink than bars
- **Emphasizing the endpoint**: Focus on the value, not the bar
- **Modern aesthetic**: Contemporary data visualization style

### Data Pattern

- 1 DIMENSION + 1 MEASURE
- Same as bar chart

### User Intent Signals

Queries that suggest lollipop:
- "Clean comparison..."
- "Minimalist ranking..."
- "Show values with less clutter..."
- (Often a design choice over bar chart)

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| Audience expects bars | May confuse | Bar Chart |
| Stacked data | Can't stack lollipops | Stacked Bar |
| Very small differences | Dots close together | Bar Chart (width helps) |
| Print/low resolution | Thin lines may not render | Bar Chart |

## Data Requirements

Same as bar chart:

| Field Role | Required | Description |
|------------|----------|-------------|
| DIMENSION | Yes | Category labels |
| MEASURE | Yes | Values |

## Selection Decision

```
IF dimensions == 1 AND measures == 1:
    AND intent == "ranking" OR "comparison":
    AND designPreference == "minimal":
        → Lollipop Chart
    ELSE:
        → Bar Chart
```

## Variants

### Horizontal Lollipop
Dots on right, stems extend left (most common).

### Vertical Lollipop
Dots on top, stems extend down.

### Dumbbell/Connected Dot
Two dots per category connected by line (shows change).

## Critical Rules

> **Dots must be clearly visible.**

Use adequate dot size (6-10px) and contrasting color.

> **Stem should be subtle.**

Thin line (1-2px) that doesn't compete with the dot.

> **Sort by value for rankings.**

Same sorting rules as bar charts.

## See Also

- [Selection Interface](./selection.md)
- [Bar Chart (Horizontal)](./selection-bar-chart-horizontal.md) — Traditional alternative
