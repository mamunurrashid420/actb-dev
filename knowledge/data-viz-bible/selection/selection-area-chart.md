---
type: action-implementation
action: selection
chart-type: area_chart
aliases: [area graph, filled line chart, shaded line]
data-pattern: temporal-measure
family: evolution
priority: P0
tags: [selection, area, trends, time-series, magnitude]
---

# Selection: Area Chart

Shows trends over time with emphasis on magnitude through filled area below the line.

## When to Use

- **Emphasizing cumulative magnitude**: Total volume over time
- **Showing trends with volume context**: Revenue that fills space
- **Stacked composition over time**: Multiple series showing parts of whole
- **Creating visual impact**: Area fills create more visual weight than lines

### Data Pattern

- 0 DIMENSIONS + 1 MEASURE + TEMPORAL (single area)
- 1 DIMENSION + 1 MEASURE + TEMPORAL (stacked areas)

### User Intent Signals

Queries that suggest an area chart:
- "Show volume over time..."
- "Cumulative trend..."
- "Total [metric] by [time period]..."
- "Composition changes over time..."

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| Comparing precise values | Area obscures exact positions | Line Chart |
| Multiple series (non-stacked) | Overlapping areas confuse | Multi-line Chart |
| Non-continuous data | Area implies continuity | Bar Chart |
| Negative values | Area below zero is confusing | Line Chart |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| TEMPORAL | Yes | X-axis time values |
| MEASURE | Yes | Y-axis values (area height) |
| DIMENSION | No | For stacked areas |

## Selection Decision

```
IF hasTemporal AND measures == 1:
    AND intent == "magnitude" OR "volume" OR "cumulative":
        → Area Chart
    
    AND dimensions == 1:
    AND intent == "composition over time":
        → Stacked Area Chart
    
    AND intent == "trend" OR "rate of change":
        → Line Chart (area adds noise)
```

## Alternatives Comparison

| Scenario | Area Chart | Alternative | Recommendation |
|----------|------------|-------------|----------------|
| Single metric trend | ✓ Shows magnitude | Line: Cleaner trend | **Line** for precision, **Area** for impact |
| Composition over time | Stacked area | Stacked bar | **Stacked Area** for continuity |
| Multiple series compare | Overlapping confuses | Multi-line | **Multi-line** |
| Rate of change focus | Fills distract | Line | **Line** |

## Variants

### Basic Area
Single filled area below line.

### Stacked Area
Multiple series stacked, showing parts of total.

### 100% Stacked Area
Stacked areas normalized to 100%.

### Gradient Area
Fill with gradient for visual appeal.

## Critical Rules

> **Use area when magnitude matters more than precision.**

The filled area emphasizes volume but makes exact values harder to read.

> **Avoid overlapping (non-stacked) areas.**

Multiple overlapping areas are confusing. Use stacking or multi-line instead.

> **Values should be positive.**

Area charts work poorly with negative values.

## See Also

- [Selection Interface](./selection.md)
- [Line Chart](./selection-line-chart.md) — For trend precision
- [Bar Chart (Stacked)](./selection-bar-chart-stacked.md) — For discrete time periods
