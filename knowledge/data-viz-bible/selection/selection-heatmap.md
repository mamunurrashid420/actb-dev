---
type: action-implementation
action: selection
chart-type: heatmap
aliases: [heat map, matrix, color matrix, density matrix]
data-pattern: two-dimensions-one-measure
family: correlation
priority: P1
tags: [selection, heatmap, matrix, color-encoding, patterns]
---

# Selection: Heatmap

Uses color intensity to show values across two categorical dimensions.

## When to Use

- **Two categorical dimensions**: Time × Category, Row × Column
- **Finding patterns in matrices**: Correlation matrices, schedules
- **Dense data display**: Many cells, color-encoded values
- **Identifying hot spots**: Where are values highest/lowest?

### Data Pattern

- 2 DIMENSIONS + 1 MEASURE
- Creates a grid/matrix of values
- Color encodes the measure value

### User Intent Signals

Queries that suggest heatmap:
- "Show patterns across X and Y..."
- "Matrix of..."
- "Correlation between..."
- "Activity by day and hour..."
- "Heat map of..."

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| Precise values needed | Hard to read from color | Table |
| One dimension only | Not a matrix | Bar Chart |
| Few cells (<20) | Heatmap overkill | Table, Bar Chart |
| Continuous axes | Not a grid | Scatter, Contour plot |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| DIMENSION (1st) | Yes | Row categories |
| DIMENSION (2nd) | Yes | Column categories |
| MEASURE | Yes | Color-encoded value |

### Cell Count Considerations

- **< 20 cells**: Probably overkill, use table
- **20-100 cells**: Good for heatmap
- **100-500 cells**: Ideal for pattern detection
- **500+ cells**: May need aggregation

## Selection Decision

```
IF dimensions == 2 AND measures == 1:
    AND intent == "pattern" OR "matrix" OR "correlation":
    AND cellCount >= 20:
        → Heatmap
```

## Color Scale Options

| Data Type | Color Scale |
|-----------|-------------|
| Sequential (low to high) | White → Blue (single hue) |
| Diverging (negative to positive) | Red ← White → Blue |
| Categorical | Not appropriate for heatmap |

## Variants

### Basic Heatmap
Color-encoded cells in a grid.

### Annotated Heatmap
Values displayed in cells alongside color.

### Clustered Heatmap
Rows/columns reordered by similarity.

### Calendar Heatmap
Days arranged in calendar format.

## Critical Rules

> **Color scale must match data type.**

Sequential data needs sequential scale. Diverging data (positive/negative) needs diverging scale.

> **Include a legend.**

Color interpretation requires a scale reference.

> **Consider color blindness.**

Avoid red-green scales. Use blue-orange or include value labels.

## See Also

- [Selection Interface](./selection.md)
- [Scatter Plot](./selection-scatter-plot.md) — For continuous dimensions
- [Data Table](./selection-data-table.md) — For precise values
