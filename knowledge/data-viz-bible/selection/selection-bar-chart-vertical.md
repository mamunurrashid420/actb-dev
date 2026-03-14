---
type: action-implementation
action: selection
chart-type: bar_chart_vertical
aliases: [bar chart, column chart, bar graph, vertical bars]
data-pattern: categorical-measure
family: ranking
priority: P0
tags: [selection, bar-chart, ranking, comparison, categorical]
---

# Selection: Bar Chart (Vertical)

Compares values across discrete categories using vertical bars.

## When to Use

- **Comparing values across categories**: Sales by product, revenue by region
- **Discrete, unordered categories**: Products, departments, countries
- **Few to moderate categories (3-12)**: Bars become too narrow with many categories
- **Emphasizing magnitude differences**: Bar length directly encodes value

### Data Pattern

- 1 DIMENSION + 1 MEASURE (basic)
- 1 DIMENSION + 1 MEASURE + secondary DIMENSION (grouped/stacked)
- No temporal requirement (use Line Chart for time series)

### User Intent Signals

Queries that suggest a vertical bar chart:
- "Compare X across categories..."
- "Show values by category..."
- "Which category has the highest/lowest..."
- "Break down by..."
- "Sales/revenue/count by..."

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| Many categories (>12) | Bars too narrow, labels crowded | Horizontal Bar, Table |
| Long category names | Labels won't fit below bars | Horizontal Bar |
| Time-based data | Implies false discreteness | Line Chart |
| Showing rankings | Harder to scan top-to-bottom | Horizontal Bar (sorted) |
| Part-to-whole | Bars don't show total context | Pie, Stacked Bar |
| Comparing two time points | Overkill for simple comparison | Slope Chart |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| DIMENSION | Yes | Category labels (x-axis) |
| MEASURE | Yes | Bar heights (y-axis values) |
| DIMENSION (2nd) | No | For grouped or stacked variants |

### Row Count Considerations

- **3-7 categories**: Ideal range
- **8-12 categories**: Acceptable, may need wider chart
- **>12 categories**: Consider Horizontal Bar or filtering to top N

## Selection Decision

```
IF dimensions == 1:
    AND measures == 1:
    AND NOT hasTemporal:
    AND rowCount <= 12:
    AND categoryNameLength <= 10 chars avg:
        → Bar Chart (Vertical)

IF dimensions == 1:
    AND measures == 1:
    AND rowCount > 12:
        → Horizontal Bar or Table

IF dimensions == 1:
    AND measures == 1:
    AND categoryNameLength > 10 chars:
        → Horizontal Bar
```

## Alternatives Comparison

| Scenario | Vertical Bar | Alternative | Recommendation |
|----------|--------------|-------------|----------------|
| Few categories, short names | ✓ Clear comparison | Horizontal: Works too | **Vertical** - conventional |
| Many categories | Crowded | Horizontal: Scannable | **Horizontal** |
| Long category names | Labels don't fit | Horizontal: Labels fit | **Horizontal** |
| Ranking emphasis | Can sort | Horizontal: Natural rank reading | **Horizontal** for rankings |
| Time dimension | Misleads | Line Chart: Shows continuity | **Line Chart** |
| Part of whole | Shows values | Pie/Stacked: Shows proportion | **Stacked** or **Pie** |

## Variants

### Basic Vertical Bar
Single measure across categories. Most common form.

### Grouped Bar
Multiple measures side-by-side per category. See [selection-bar-chart-grouped.md](./selection-bar-chart-grouped.md).

### Stacked Bar
Multiple measures stacked per category. See [selection-bar-chart-stacked.md](./selection-bar-chart-stacked.md).

### 100% Stacked Bar
Stacked bars normalized to 100%. See [selection-bar-chart-stacked-100-percent.md](./selection-bar-chart-stacked-100-percent.md).

## Critical Rules

> **Category labels must fit horizontally.**

If labels need to be rotated diagonally, switch to Horizontal Bar Chart instead.

> **Bars should be wider than gaps.**

The bar-to-gap ratio should be approximately 2:1 or higher for visual clarity.

> **Y-axis should start at zero.**

Truncating the y-axis exaggerates differences and can mislead. Always start at zero for bar charts.

## See Also

- [Selection Interface](./selection.md) — Decision tree and process
- [Bar Chart (Horizontal)](./selection-bar-chart-horizontal.md) — For rankings and long labels
- [Bar Chart (Grouped)](./selection-bar-chart-grouped.md) — For multi-measure comparison
- [Bar Chart (Stacked)](./selection-bar-chart-stacked.md) — For part-to-whole
