---
type: action-implementation
action: selection
chart-type: donut_chart
aliases: [donut chart, doughnut chart, ring chart]
data-pattern: categorical-composition
family: partOfWhole
priority: P0
tags: [selection, donut_chart, composition, part-to-whole, percentage, dashboard]
---

# Selection: Donut Chart

Shows part-to-whole relationships using angular slices of a ring, with a hollow center for annotation. **Donut = component.**

## When to Use

- **Chart is part of a system**: Lives inside a dashboard tile, not standalone
- **Center annotation needed**: Total, KPI, label, or summary stat in the center
- **Hover / interaction / labels expected**: Modern interactive UI pattern
- **Dense dashboards**: Reduces visual weight compared to filled pie
- **UI-first, modern analytics**: Contemporary look and feel

### Why It Works

- The center hole gives **semantic real estate** — show total, KPI, or label
- Reduces visual weight in dense dashboards
- Plays better with modern UI patterns and interaction models
- Repeating tiles across a dashboard grid look cleaner

### Typical Examples

- "Revenue split" with total in the center
- Status distributions with a big number inside (e.g., "87% On Track")
- Repeating tiles across a dashboard grid
- Budget allocation with total budget in center

### Data Pattern

- 1 DIMENSION + 1 MEASURE
- Values sum to meaningful total (100%)
- Few categories (ideally ≤ 5)

### User Intent Signals

Queries that suggest a donut chart:
- "Breakdown of... with total"
- "Distribution across..."
- "Show the split and overall..."
- "Dashboard view of..."
- "Status overview..."

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| Many categories (>5) | Small slices unreadable | Bar Chart, Treemap |
| Comparing values across charts | Angles hard to compare | Bar Chart |
| Values don't sum to whole | Donut implies 100% | Bar Chart |
| Precise comparisons needed | Angles hard to judge | Bar Chart |
| Showing change over time | Can't show temporal | Stacked Area, Line |
| Simple standalone statement | No center needed | Pie Chart |
| Quick executive binary glance | Pie is more direct | Pie Chart |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| DIMENSION | Yes | Category labels |
| MEASURE | Yes | Values (should sum to meaningful total) |

### Category Count Considerations

- **2-3 categories**: Ideal
- **4-5 categories**: Acceptable
- **6+ categories**: Consider alternatives or group into "Other"

## Selection Decision

```
IF dimensions == 1:
    AND measures == 1:
    AND intent == "composition" OR "percentage" OR "share":
    AND rowCount <= 5:
        IF context == "dashboard tile" OR "needs total annotation" OR "modern UI":
            → Donut Chart
        IF context == "standalone" OR "executive summary":
            → Pie Chart
    
    AND rowCount > 5:
        → Group small values into "Other" 
        OR use Bar Chart / Treemap
```

## Pie vs Donut Decision Table

| Question being answered | Better choice |
|-------------------------|---------------|
| "Is this mostly one thing?" | pie_chart |
| "How does this fit in the dashboard?" | **donut_chart** |
| "What's the total + breakdown?" | **donut_chart** |
| "Quick executive glance?" | pie_chart |
| "UI-first, modern analytics?" | **donut_chart** |

**Rule of thumb**: Pie = statement. Donut = component.

## Alternatives Comparison

| Scenario | Donut Chart | Alternative | Recommendation |
|----------|-------------|-------------|----------------|
| 3 categories + total | ✓ Center annotation | Pie: No center | **Donut** |
| 6+ categories | Small slices | Bar: All readable | **Bar Chart** |
| Compare two periods | Two donuts hard to compare | Grouped Bar | **Grouped Bar** |
| Hierarchical composition | Flat only | Treemap: Shows hierarchy | **Treemap** |
| Simple binary split | Unnecessary complexity | Pie: Simpler | **Pie Chart** |

## Critical Rules

> **Slices must sum to 100% of a meaningful whole.**

Donut charts imply parts of a total. If values don't sum to a complete set, don't use donut.

> **Limit to 5 categories maximum.**

Human perception of arc lengths is poor. More than 5 slices makes comparison difficult.

> **Center annotation should be meaningful.**

The center is premium real estate. Use it for the total, a KPI, or a descriptive label — not decoration.

> **Start at 12 o'clock, go clockwise.**

Convention is to start the first slice at the top and proceed clockwise.

> **Largest slice first (usually).**

Order slices by size for easier reading, unless there's a meaningful categorical order.

## See Also

- [Selection Interface](./selection.md)
- [Pie Chart](./selection-pie-chart.md) — For simple standalone statements
- [Treemap](./selection-treemap.md) — For hierarchical part-to-whole
- [Bar Chart (Stacked)](./selection-bar-chart-stacked.md) — For composition over categories
