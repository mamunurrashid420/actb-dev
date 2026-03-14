---
type: action-implementation
action: selection
chart-type: pie_chart
aliases: [pie chart, circle chart]
data-pattern: categorical-composition
family: partOfWhole
priority: P0
tags: [selection, pie_chart, composition, part-to-whole, percentage]
---

# Selection: Pie Chart

Shows part-to-whole relationships using angular slices of a complete circle. **Pie = statement.**

## When to Use

- **Binary or obvious takeaway**: "Is this mostly X or not?"
- **One slice clearly dominates**: The story is immediately visible
- **Precision is not required**: Relative size matters, not exact values
- **Quick executive glance**: Minimal cognitive load, instantly familiar

### Why It Works

- Humans are good at spotting one big wedge
- Instantly familiar — lowest learning curve of any chart
- Minimal cognitive load for simple compositions

### Typical Examples

- Yes / No split
- Used vs unused capacity
- Market share with a clear leader

### Data Pattern

- 1 DIMENSION + 1 MEASURE
- Values sum to meaningful total (100%)
- Few categories (ideally ≤ 5)

### User Intent Signals

Queries that suggest a pie chart:
- "Breakdown of..."
- "Share of..."
- "What percentage is..."
- "Is this mostly...?"
- "Dominant category..."

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| Many categories (>5) | Small slices unreadable | Bar Chart, Treemap |
| Comparing values across charts | Angles hard to compare | Bar Chart |
| Values don't sum to whole | Pie implies 100% | Bar Chart |
| Precise comparisons needed | Angles hard to judge | Bar Chart |
| Showing change over time | Can't show temporal | Stacked Area, Line |
| Part of a dashboard system | No center annotation | Donut Chart |
| UI-first modern analytics | Traditional feel | Donut Chart |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| DIMENSION | Yes | Category labels |
| MEASURE | Yes | Values (should sum to meaningful total) |

### Category Count Considerations

- **2-3 categories**: Ideal for pie
- **4-5 categories**: Acceptable
- **6+ categories**: Consider alternatives or group into "Other"

## Selection Decision

```
IF dimensions == 1:
    AND measures == 1:
    AND intent == "composition" OR "percentage" OR "share":
    AND rowCount <= 5:
        IF context == "standalone" OR "executive summary":
            → Pie Chart
        IF context == "dashboard tile" OR "needs total annotation":
            → Donut Chart
    
    AND rowCount > 5:
        → Group small values into "Other" 
        OR use Bar Chart / Treemap
```

## Pie vs Donut Decision Table

| Question being answered | Better choice |
|-------------------------|---------------|
| "Is this mostly one thing?" | **pie_chart** |
| "How does this fit in the dashboard?" | donut_chart |
| "What's the total + breakdown?" | donut_chart |
| "Quick executive glance?" | **pie_chart** |
| "UI-first, modern analytics?" | donut_chart |

**Rule of thumb**: Pie = statement. Donut = component.

## Alternatives Comparison

| Scenario | Pie Chart | Alternative | Recommendation |
|----------|-----------|-------------|----------------|
| 3 categories | ✓ Clear composition | Bar: Also works | **Pie** for simplicity |
| 6+ categories | Small slices | Bar: All readable | **Bar Chart** |
| Compare two periods | Two pies hard to compare | Grouped Bar | **Grouped Bar** |
| Hierarchical composition | Flat only | Treemap: Shows hierarchy | **Treemap** |
| Exact values matter | Hard to read | Bar: Precise | **Bar Chart** |
| Dashboard tile with total | No center space | Donut: Center annotation | **Donut Chart** |

## Critical Rules

> **Slices must sum to 100% of a meaningful whole.**

Pie charts imply parts of a total. If values don't sum to a complete set, don't use pie.

> **Limit to 5 categories maximum.**

Human perception of angles is poor. More than 5 slices makes comparison difficult.

> **Start at 12 o'clock, go clockwise.**

Convention is to start the first slice at the top and proceed clockwise.

> **Largest slice first (usually).**

Order slices by size for easier reading, unless there's a meaningful categorical order.

## See Also

- [Selection Interface](./selection.md)
- [Donut Chart](./selection-donut-chart.md) — For dashboard components with center annotation
- [Treemap](./selection-treemap.md) — For hierarchical part-to-whole
- [Bar Chart (Stacked)](./selection-bar-chart-stacked.md) — For composition over categories
