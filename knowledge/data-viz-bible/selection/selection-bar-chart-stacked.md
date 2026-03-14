---
type: action-implementation
action: selection
chart-type: bar_chart_stacked
aliases: [stacked bar, stacked column, stacked bar chart]
data-pattern: categorical-multi-measure-composition
family: partOfWhole
priority: P1
tags: [selection, bar-chart, stacked, composition, part-to-whole]
---

# Selection: Bar Chart (Stacked)

Shows part-to-whole composition across categories using stacked segments.

## When to Use

- **Composition by category**: Revenue breakdown by product line, per region
- **Comparing totals AND parts**: Both segment sizes and overall totals matter
- **2-5 segments per bar**: Few enough to distinguish
- **Part-to-whole + comparison**: Combine pie-like composition with bar comparison

### Data Pattern

- 1 DIMENSION (categories) + 1 DIMENSION (segments) + 1 MEASURE
- Or: 1 DIMENSION + multiple MEASURES (one per segment)

### User Intent Signals

Queries that suggest stacked bar:
- "Breakdown by... for each..."
- "Composition across categories..."
- "Total and parts..."
- "Stacked comparison..."

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| Compare segment sizes across categories | Middle segments hard to compare | Grouped Bar |
| Many segments (>5) | Too many to distinguish | Grouped Bar, Table |
| Only care about totals | Segments add noise | Simple Bar |
| Precise segment comparison | Stacking obscures | Grouped Bar |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| DIMENSION | Yes | Category axis |
| DIMENSION (2nd) | Yes | Segment grouping |
| MEASURE | Yes | Segment values |

## Selection Decision

```
IF dimensions == 2 AND measures == 1:
    AND intent == "composition" OR "breakdown":
    AND segmentCount <= 5:
        → Stacked Bar Chart
    
    AND intent == "compare segments":
        → Grouped Bar Chart
```

## Alternatives Comparison

| Scenario | Stacked Bar | Alternative | Recommendation |
|----------|-------------|-------------|----------------|
| Show composition + total | ✓ Shows both | Grouped: No total | **Stacked** |
| Compare specific segments | Hard to compare | Grouped: Easy compare | **Grouped** |
| Many segments | Cluttered | Table with sparklines | **Table** |

## Variants

### Stacked Vertical
Segments stack vertically.

### Stacked Horizontal
Segments stack horizontally. Good for rankings with composition.

### 100% Stacked
All bars same height, shows pure composition. See [selection-bar-chart-stacked-100-percent.md](./selection-bar-chart-stacked-100-percent.md).

## Critical Rules

> **Limit to 5 segments maximum.**

More segments become indistinguishable.

> **Bottom segment is easiest to compare.**

Only the bottom segment has a common baseline. Place most important segment there.

> **Consider if totals or segments matter more.**

If segment comparison is primary goal, use grouped bars instead.

## See Also

- [Selection Interface](./selection.md)
- [Bar Chart (Grouped)](./selection-bar-chart-grouped.md) — For segment comparison
- [Bar Chart (100% Stacked)](./selection-bar-chart-stacked-100-percent.md) — For pure composition
