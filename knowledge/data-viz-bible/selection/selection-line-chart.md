---
type: action-implementation
action: selection
chart-type: line_chart
aliases: [line graph, trend chart, time series chart, trend line]
data-pattern: temporal-measure
family: evolution
priority: P0
tags: [selection, line_chart, evolution, trends, time-series, temporal]
---

# Selection: Line Chart

Shows trends and changes over continuous data, typically time.

## When to Use

- **Showing trends over time**: Revenue by month, users by week, temperature by day
- **Continuous data with meaningful connections**: Values between points can be interpolated
- **Comparing multiple series over the same interval**: Revenue vs. costs, actual vs. forecast
- **Emphasizing rate of change**: Slopes communicate acceleration/deceleration

### Data Pattern

- 0 DIMENSIONS + 1 MEASURE + TEMPORAL (single series)
- 1 DIMENSION + 1 MEASURE + TEMPORAL (multiple series, one line per category)
- Data should be ordered by time
- Values between points are meaningfully connected

### User Intent Signals

Queries that suggest a line chart:
- "Show me the trend over..."
- "How has X changed over time..."
- "Monthly/quarterly/yearly performance..."
- "Compare trends between..."
- "Track progress of..."
- "What's the trajectory of..."

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| Discrete categories without sequence | Lines imply false continuity | Bar Chart |
| Single time point comparison | Line adds no value | Slope Chart, Bar Chart |
| Emphasizing cumulative magnitude | Line shows level, not accumulation | Area Chart (stacked) |
| Too many series (>5) | Becomes "spaghetti chart" | Small multiples, highlight one series |
| Sparse, irregular data | Connecting distant points misleads | Scatter Plot with trend line |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| TEMPORAL | Yes | X-axis time values (dates, months, years) |
| MEASURE | Yes | Y-axis numeric values |
| DIMENSION | No | For multiple series (one line per category) |

### Row Count Considerations

- **Few points (< 10)**: Consider showing data markers
- **Moderate (10-50)**: Standard line, no markers usually needed
- **Dense (> 50)**: Ensure adequate width; consider aggregation
- **Very dense (> 200)**: May need downsampling or time range selection

## Selection Decision

```
IF hasTemporal:
    AND measures == 1:
    AND dimensions == 0:
        → Line Chart (single series)
    
    AND measures == 1:
    AND dimensions == 1:
    AND dimension.cardinality <= 5:
        → Line Chart (multi-series)
    
    AND measures == 1:
    AND dimensions == 1:
    AND dimension.cardinality > 5:
        → Line Chart with highlight strategy
        OR Small multiples
```

## Alternatives Comparison

| Scenario | Line Chart | Alternative | Recommendation |
|----------|------------|-------------|----------------|
| Show trend over time | ✓ Clear trend visibility | Area Chart: Emphasizes magnitude | **Line** for trend focus |
| Compare 2 time points | Shows full context | Slope Chart: Direct comparison | **Slope** for cleaner comparison |
| Show composition over time | Shows individual series | Stacked Area: Shows total + parts | **Stacked Area** for part-to-whole |
| Sparse time points | May mislead with connections | Scatter + trend: Shows actual points | **Scatter** if interpolation invalid |
| Many categories | Spaghetti risk | Bar Chart (grouped): Discrete comparison | **Highlight strategy** or filter |

## Variants

### Single Line
One measure over time. Simplest form.

### Multi-Line
Multiple series (by dimension) on same axes. Limit to 4-5 series for readability.

### With Markers
Data points shown as dots. Use for sparse data or when individual values matter.

### With Area Fill
Line with shaded area below. See [Area Chart](./selection-area-chart.md).

### Stepped Line
Value changes only at data points (no interpolation). Use for discrete states (e.g., pricing tiers).

## Critical Rules

> **Lines must connect meaningful continuous data.**

The line between points implies that intermediate values exist and can be estimated. If this isn't true (e.g., categorical data), don't use a line chart.

> **Limit to 5 series maximum.**

Beyond 5 lines, the chart becomes difficult to read. Use highlighting (one series prominent, others gray) or small multiples instead.

## See Also

- [Selection Interface](./selection.md) — Decision tree and process
- [Area Chart](./selection-area-chart.md) — When magnitude matters more than trend
- [Slope Chart](./selection-slope-chart.md) — For two-point comparisons
- [Timeseries](./selection-timeseries.md) — For complex time handling
