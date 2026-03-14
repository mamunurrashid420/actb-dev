---
type: action-implementation
action: selection
chart-type: bar_chart_horizontal
aliases: [horizontal bar chart, bar chart horizontal, horizontal bars, row chart]
data-pattern: categorical-measure
family: ranking
priority: P0
tags: [selection, bar-chart, horizontal, ranking, comparison, categorical]
---

# Selection: Bar Chart (Horizontal)

Compares values across categories using horizontal bars. Ideal for rankings and long category labels.

## When to Use

- **Ranking data**: Showing items from highest to lowest (or vice versa)
- **Long category names**: Labels fit naturally on the left
- **Many categories (8-20+)**: Vertical scrolling is natural for lists
- **Comparing a focus item to others**: "Our product vs. competitors"

### Data Pattern

- 1 DIMENSION + 1 MEASURE (basic)
- Sorted by value (descending for rankings)
- Works well with many categories

### User Intent Signals

Queries that suggest a horizontal bar chart:
- "Rank by..."
- "Top 10..."
- "Which are the highest/lowest..."
- "Compare [long names]..."
- "Show [entity] vs. competitors..."
- "List by performance..."

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| Time-based data | Bars imply discreteness | Line Chart |
| Few categories with short names | Horizontal uses more vertical space | Vertical Bar |
| Showing composition | Bars don't show whole | Stacked Bar, Pie |
| Exact value reading critical | Hard to read from axis | Table with bars |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| DIMENSION | Yes | Category labels (y-axis) |
| MEASURE | Yes | Bar lengths (x-axis) |

### Row Count Considerations

- **3-7 categories**: Works, but vertical bar also fine
- **8-15 categories**: Ideal for horizontal
- **16-30 categories**: Still works, may need scrolling
- **>30 categories**: Consider filtering to top N, or use table

## Selection Decision

```
IF dimensions == 1 AND measures == 1:
    AND intent == "ranking" OR intent == "top N":
        → Bar Chart (Horizontal), sorted descending
    
    AND categoryLabelLength > 10 characters (avg):
        → Bar Chart (Horizontal)
    
    AND rowCount > 12:
        → Bar Chart (Horizontal)
```

## Alternatives Comparison

| Scenario | Horizontal Bar | Alternative | Recommendation |
|----------|----------------|-------------|----------------|
| Ranking top 10 | ✓ Natural list format | Vertical: Harder to scan | **Horizontal** |
| Long product names | ✓ Labels fit | Vertical: Labels diagonal/truncated | **Horizontal** |
| 5 short categories | Works but tall | Vertical: More compact | **Vertical** |
| Showing change over time | Implies discreteness | Line: Shows continuity | **Line Chart** |

## Sorting

**Always sort horizontal bar charts** unless there's a meaningful categorical order.

### Sort Options

| Sort | When to Use |
|------|-------------|
| Descending (highest first) | Rankings, "top performers" |
| Ascending (lowest first) | "Bottom performers", cost efficiency |
| Alphabetical | When no ranking implied, reference lookup |
| Custom order | Logical sequence (stages, regions) |

## Variants

### Basic Horizontal Bar
Single measure, sorted by value.

### With Highlight
Focus category in accent color, others gray.

### Bullet Chart
Bar with reference marker (target/benchmark).

### Diverging Bar
Bars extend left and right from center (positive/negative).

## Critical Rules

> **Sort by value for rankings.**

Unsorted horizontal bars are confusing. The eye expects a ranked list.

> **Start X-axis at zero.**

Same rule as vertical bars—bar length must be proportional to value.

> **Labels on the left, values readable.**

The natural reading position for category names is left-aligned on the y-axis.

## See Also

- [Selection Interface](./selection.md) — Decision tree and process
- [Bar Chart (Vertical)](./selection-bar-chart-vertical.md) — For fewer categories
- [Lollipop Chart](./selection-lollipop-chart.md) — Cleaner alternative for sparse data
