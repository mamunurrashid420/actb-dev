---
type: action-implementation
action: selection
chart-type: bar_chart_grouped
aliases: [grouped bar, clustered bar, side-by-side bar, multi-series bar]
data-pattern: categorical-multi-measure-comparison
family: ranking
priority: P1
tags: [selection, bar-chart, grouped, comparison, multi-series]
---

# Selection: Bar Chart (Grouped)

Compares multiple measures side-by-side for each category.

## When to Use

- **Direct comparison of segments**: Compare product lines head-to-head
- **2-4 groups per category**: Few enough to fit side-by-side
- **Segment values matter more than totals**: Focus on individual comparisons
- **Common baseline needed**: All bars start at zero

### Data Pattern

- 1 DIMENSION (categories) + multiple MEASURES
- Or: 1 DIMENSION (categories) + 1 DIMENSION (groups) + 1 MEASURE

### User Intent Signals

Queries that suggest grouped bar:
- "Compare X vs Y by category..."
- "Side-by-side comparison..."
- "How does A compare to B for each..."
- "Multiple metrics by..."

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| Need to show totals | Grouped doesn't show sum | Stacked Bar |
| Many groups (>4) | Bars too narrow | Small multiples, table |
| Part-to-whole focus | Grouped doesn't show whole | Stacked Bar, Pie |
| Many categories | Chart becomes wide | Horizontal grouped |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| DIMENSION | Yes | Category axis |
| MEASURES | Multiple | One bar per measure, per category |

## Selection Decision

```
IF dimensions == 1 AND measures >= 2:
    AND intent == "compare" OR "vs":
    AND measures <= 4:
        → Grouped Bar Chart
    
    AND intent == "composition" OR "total":
        → Stacked Bar Chart
```

## Alternatives Comparison

| Scenario | Grouped Bar | Alternative | Recommendation |
|----------|-------------|-------------|----------------|
| Compare 2 metrics | ✓ Clear comparison | Stacked: Obscures | **Grouped** |
| Show totals + parts | No totals visible | Stacked: Shows totals | **Stacked** |
| 5+ groups | Too crowded | Small multiples | **Small multiples** |
| Long category names | May not fit | Horizontal grouped | **Horizontal** |

## Variants

### Grouped Vertical
Groups of bars side-by-side, vertical orientation.

### Grouped Horizontal
Groups stacked horizontally. Better for long labels.

### Diverging Grouped
Bars extend left/right from center. For positive/negative comparisons.

## Critical Rules

> **Limit to 4 groups maximum per category.**

More groups make bars too narrow and hard to distinguish.

> **Keep group order consistent.**

Same measure should be in same position across all categories.

> **Color-code groups consistently.**

Each group (measure) should have consistent color throughout.

## See Also

- [Selection Interface](./selection.md)
- [Bar Chart (Stacked)](./selection-bar-chart-stacked.md) — For part-to-whole
- [Small Multiples](./selection-small-multiples.md) — For many groups
