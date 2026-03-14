---
type: action-implementation
action: selection
chart-type: scatter_plot
aliases: [scatter chart, scatter graph, XY chart, correlation chart, point cloud]
data-pattern: two-measures
family: correlation
priority: P0
tags: [selection, scatter, correlation, relationship, two-variables]
---

# Selection: Scatter Plot

Shows the relationship between two numeric variables using point positions.

## When to Use

- **Exploring correlation**: Does X relate to Y?
- **Two continuous measures**: Both axes are numeric values
- **Many data points**: Works best with 20+ points
- **Identifying outliers**: Points that don't fit the pattern
- **Showing clusters**: Natural groupings in data

### Data Pattern

- 0 DIMENSIONS + 2 MEASURES (basic)
- 1 DIMENSION + 2 MEASURES (with categorical coloring)
- Many rows (typically 20-500+)

### User Intent Signals

Queries that suggest a scatter plot:
- "Relationship between X and Y..."
- "Correlation of..."
- "Does X affect Y..."
- "X versus Y..."
- "Plot X against Y..."

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| Categorical X variable | Not true correlation | Bar Chart |
| Few data points (<10) | Pattern unclear | Table with values |
| Time-based relationship | Scatter loses sequence | Line Chart |
| Showing distribution of one variable | Overkill | Histogram |
| Exact values matter | Hard to read from points | Table |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| MEASURE (1st) | Yes | X-axis values |
| MEASURE (2nd) | Yes | Y-axis values |
| MEASURE (3rd) | No | Point size (creates Bubble Chart) |
| DIMENSION | No | Point color/shape grouping |

### Row Count Considerations

- **< 10 points**: Pattern may be unclear
- **10-100 points**: Ideal range
- **100-500 points**: Works well
- **> 500 points**: Consider sampling or density plot

## Selection Decision

```
IF measures >= 2:
    AND both measures continuous:
    AND intent == "relationship" OR "correlation":
        → Scatter Plot
    
    AND measures == 3:
        → Bubble Chart (3rd measure = size)
    
    AND dimensions == 1:
        → Scatter Plot with color grouping
```

## Alternatives Comparison

| Scenario | Scatter Plot | Alternative | Recommendation |
|----------|--------------|-------------|----------------|
| Two numeric variables | ✓ Shows relationship | Line: Implies causation | **Scatter** for correlation |
| With category grouping | Colored points | Small multiples | **Scatter with color** usually |
| 3 variables | Add size (bubble) | Parallel coordinates | **Bubble** if 3rd variable clear |
| Very many points | Overplotting | Hexbin, density | **Density** for >1000 points |

## Variants

### Basic Scatter
Two measures as X and Y positions.

### Scatter with Grouping
Points colored by category.

### Bubble Chart
Third measure encoded as point size. See [selection-bubble-chart.md](./selection-bubble-chart.md).

### Scatter with Trend Line
Regression or LOESS line overlaid.

## Critical Rules

> **Both axes should be continuous numeric values.**

Categorical data on an axis is a misuse of scatter plots.

> **Consider overplotting.**

Many overlapping points hide patterns. Use transparency, jitter, or density plots.

> **Don't imply causation.**

Scatter shows correlation, not causation. X → Y relationship requires careful interpretation.

## See Also

- [Selection Interface](./selection.md) — Decision tree
- [Bubble Chart](./selection-bubble-chart.md) — With size encoding
- [Line Chart](./selection-line-chart.md) — For sequential data
