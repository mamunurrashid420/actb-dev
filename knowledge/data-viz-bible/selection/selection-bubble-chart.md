---
type: action-implementation
action: selection
chart-type: bubble_chart
aliases: [bubble plot, sized scatter, three-variable scatter]
data-pattern: three-measures
family: correlation
priority: P2
tags: [selection, bubble, scatter, three-variables, correlation]
---

# Selection: Bubble Chart

Extends scatter plot with a third variable encoded as bubble size.

## When to Use

- **Three continuous variables**: X position, Y position, and size
- **Showing relative magnitude**: Size emphasizes importance
- **Comparing entities across dimensions**: Countries, products, etc.
- **Portfolio analysis**: Risk vs. return vs. investment size

### Data Pattern

- 0 DIMENSIONS + 3 MEASURES (basic)
- 1 DIMENSION + 3 MEASURES (with labels/colors)

### User Intent Signals

Queries that suggest bubble chart:
- "Compare X, Y, and Z..."
- "Show three variables..."
- "Plot with size representing..."
- "Portfolio view..."

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| Only two variables | Size adds no information | Scatter Plot |
| Precise size comparison needed | Hard to compare circle areas | Table, Bar Chart |
| Many overlapping points | Bubbles obscure each other | Scatter with grouping |
| Negative values for size | Can't have negative area | Different encoding |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| MEASURE (1st) | Yes | X-axis position |
| MEASURE (2nd) | Yes | Y-axis position |
| MEASURE (3rd) | Yes | Bubble size |
| DIMENSION | No | Label/color grouping |

## Selection Decision

```
IF measures == 3:
    AND all continuous:
    AND intent == "three-way comparison":
    AND size values positive:
        → Bubble Chart
```

## Variants

### Basic Bubble
X, Y, size only.

### Labeled Bubble
Bubbles with entity labels.

### Colored Bubble
Fourth dimension as color.

## Critical Rules

> **Size must encode positive values.**

Can't have negative bubble sizes.

> **Area, not radius, should be proportional.**

Humans perceive area. If value doubles, area should double (not radius).

> **Watch for overlap.**

Large bubbles can obscure smaller ones. Consider transparency.

## See Also

- [Selection Interface](./selection.md)
- [Scatter Plot](./selection-scatter-plot.md) — Two-variable version
