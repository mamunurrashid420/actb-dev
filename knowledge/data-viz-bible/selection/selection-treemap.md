---
type: action-implementation
action: selection
chart-type: treemap
aliases: [tree map, rectangular treemap, space-filling]
data-pattern: hierarchical-composition
family: partOfWhole
priority: P1
tags: [selection, treemap, hierarchy, composition, part-to-whole]
---

# Selection: Treemap

Shows hierarchical part-to-whole relationships using nested rectangles.

## When to Use

- **Hierarchical composition**: Category → Subcategory breakdown
- **Many categories**: Works with 10-100+ items
- **Size comparison**: Rectangle area encodes value
- **Space efficiency**: Uses all available space

### Data Pattern

- 1+ DIMENSIONS (hierarchy levels) + 1 MEASURE
- Parent-child relationships
- Values should sum meaningfully

### User Intent Signals

Queries that suggest treemap:
- "Hierarchical breakdown..."
- "Nested composition..."
- "Size comparison across many items..."
- "Space-filling visualization..."

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| No hierarchy | Flat treemap less useful | Bar Chart, Pie |
| Precise comparison | Rectangles hard to compare | Bar Chart |
| Few items (<10) | Treemap overkill | Pie, Bar Chart |
| Showing trends | No temporal encoding | Line Chart |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| DIMENSION (1+) | Yes | Hierarchy levels |
| MEASURE | Yes | Rectangle size |
| MEASURE (2nd) | No | Rectangle color |

## Selection Decision

```
IF hierarchicalData:
    AND intent == "composition" OR "breakdown":
    AND itemCount >= 10:
        → Treemap
    
IF flatData AND itemCount > 10:
    AND intent == "part-to-whole":
        → Treemap (better than pie for many items)
```

## Variants

### Basic Treemap
Single level of rectangles.

### Nested Treemap
Multiple hierarchy levels with visual nesting.

### Treemap with Color Encoding
Second measure encoded as color.

## Critical Rules

> **Area must be proportional to value.**

Don't distort rectangle sizes.

> **Labels need careful handling.**

Small rectangles may not fit labels. Consider tooltips.

> **Limit nesting depth.**

More than 2-3 levels becomes hard to read.

## See Also

- [Selection Interface](./selection.md)
- [Pie Chart](./selection-pie-donut-chart.md) — For simple composition
- [Bar Chart (Stacked)](./selection-bar-chart-stacked.md) — For category comparison
