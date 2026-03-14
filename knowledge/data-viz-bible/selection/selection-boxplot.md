---
type: action-implementation
action: selection
chart-type: boxplot
aliases: [box plot, box-and-whisker, box and whisker plot]
data-pattern: distribution-comparison
family: distribution
priority: P1
tags: [selection, boxplot, distribution, statistical, comparison]
---

# Selection: Box Plot

Shows distribution summary statistics (median, quartiles, outliers) for comparing groups.

## When to Use

- **Comparing distributions across groups**: Salary by department, scores by class
- **Statistical summary**: Median, IQR, outliers at a glance
- **Many groups**: Works well with 3-20 groups
- **Identifying outliers**: Clearly marks extreme values

### Data Pattern

- 1 DIMENSION (groups) + 1 MEASURE (values)
- Multiple values per group
- Shows 5-number summary: min, Q1, median, Q3, max

### User Intent Signals

Queries that suggest box plot:
- "Distribution by group..."
- "Compare spread across..."
- "Median and quartiles..."
- "Outliers in..."
- "Statistical comparison..."

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| Single group | No comparison | Histogram |
| Showing full distribution shape | Box hides shape | Violin plot, Histogram |
| Non-statistical audience | May not understand | Bar with error bars |
| Few data points per group | Statistics unreliable | Dot plot |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| DIMENSION | Yes | Group categories |
| MEASURE | Yes | Values to summarize |

### Points per Group

- **< 10 points**: Statistics may be unreliable
- **10-30 points**: Acceptable
- **30+ points**: Good statistical basis

## Selection Decision

```
IF dimensions == 1 AND measures == 1:
    AND intent == "distribution comparison" OR "statistical":
    AND multipleValuesPerGroup:
        → Box Plot
```

## Anatomy

```
    ┬   Maximum (or upper fence)
    │
    ┼   Upper whisker
    │
┌───┴───┐
│       │  Q3 (75th percentile)
├───────┤  Median (50th percentile)
│       │  Q1 (25th percentile)
└───┬───┘
    │
    ┼   Lower whisker
    │
    ┴   Minimum (or lower fence)
    
    ○   Outliers (beyond fences)
```

## Variants

### Standard Box Plot
Whiskers to min/max or 1.5×IQR fences.

### Notched Box Plot
Notch shows confidence interval around median.

### Box Plot with Points
Individual data points overlaid.

### Violin Plot Alternative
Shows full distribution shape instead of summary.

## Critical Rules

> **Ensure audience understands box plots.**

Not everyone knows how to read them. Consider alternatives for general audiences.

> **Consistent whisker definition.**

Document whether whiskers show min/max or 1.5×IQR fences.

> **Enough data per group.**

Statistical summaries need sufficient data to be meaningful.

## See Also

- [Selection Interface](./selection.md)
- [Histogram](./selection-histogram.md) — For single distribution
- [Violin Plot](./selection-violin-plot.md) — For full distribution shape
