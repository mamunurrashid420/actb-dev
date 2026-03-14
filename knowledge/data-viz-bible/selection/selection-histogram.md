---
type: action-implementation
action: selection
chart-type: histogram
aliases: [distribution chart, frequency distribution, bin chart]
data-pattern: single-measure-distribution
family: distribution
priority: P1
tags: [selection, histogram, distribution, frequency, statistical]
---

# Selection: Histogram

Shows the distribution of a single numeric variable by grouping values into bins.

## When to Use

- **Understanding distribution shape**: Normal, skewed, bimodal
- **Single continuous variable**: Ages, prices, durations
- **Identifying outliers**: Values far from the center
- **Comparing to expected distribution**: Actual vs. normal

### Data Pattern

- 0 DIMENSIONS + 1 MEASURE
- Many rows (20+ for meaningful distribution)
- Continuous numeric values

### User Intent Signals

Queries that suggest a histogram:
- "Distribution of..."
- "How are values spread..."
- "Frequency of..."
- "Most common range..."
- "Is it normally distributed..."

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| Categorical data | Not continuous | Bar Chart |
| Few data points (<20) | Distribution unclear | Dot plot, table |
| Comparing distributions | Single histogram only | Multiple histograms, box plots |
| Time series | Loses temporal order | Line Chart |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| MEASURE | Yes | Continuous numeric values |
| DIMENSION | No | Not used (pure distribution) |

### Row Count Considerations

- **< 20 rows**: Distribution may be meaningless
- **20-100 rows**: Reasonable distribution
- **100-1000 rows**: Good distribution clarity
- **1000+ rows**: Very clear patterns

## Selection Decision

```
IF measures == 1:
    AND values are continuous:
    AND intent == "distribution" OR "frequency" OR "spread":
    AND rowCount >= 20:
        → Histogram
```

## Bin Count Guidelines

| Data Points | Suggested Bins |
|-------------|----------------|
| 20-50 | 5-7 bins |
| 50-100 | 7-10 bins |
| 100-500 | 10-15 bins |
| 500+ | 15-20 bins |

Or use Sturges' rule: `bins = 1 + 3.322 * log10(n)`

## Variants

### Basic Histogram
Standard frequency bars.

### Density Histogram
Y-axis shows density instead of count (area = 1).

### Cumulative Histogram
Shows cumulative frequency.

### Stacked Histogram
Multiple distributions overlaid or stacked.

## Critical Rules

> **Use only for continuous numeric data.**

Histograms bin continuous values. Categorical data needs bar charts.

> **Bars should touch.**

Unlike bar charts, histogram bars touch because they represent continuous ranges.

> **Bin width affects interpretation.**

Too few bins hide patterns; too many create noise.

## See Also

- [Selection Interface](./selection.md)
- [Box Plot](./selection-boxplot.md) — For comparing distributions
- [Bar Chart](./selection-bar-chart-vertical.md) — For categorical data
