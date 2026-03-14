---
type: action-implementation
action: selection
chart-type: waterfall_chart
aliases: [waterfall, bridge chart, cascade chart, flying bricks]
data-pattern: sequential-accumulation
family: evolution
priority: P2
tags: [selection, waterfall, cumulative, financial, change-breakdown]
---

# Selection: Waterfall Chart

Shows how an initial value changes through a series of positive and negative contributions to reach a final value.

## When to Use

- **Explaining cumulative change**: How did we get from A to B?
- **Financial breakdowns**: Revenue bridges, profit/loss analysis
- **Sequential contributions**: Each step adds or subtracts from running total
- **Before/after with intermediate steps**: Start → Changes → End

### Data Pattern

- ORDERED CATEGORIES + 1 MEASURE (signed values)
- First value is starting point
- Intermediate values are positive/negative changes
- Last value is ending total

### User Intent Signals

Queries that suggest waterfall chart:
- "How did we get from X to Y..."
- "Bridge from... to..."
- "Breakdown of changes..."
- "What drove the change..."
- "Walk through the numbers..."

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| No sequential story | Waterfall needs order | Bar Chart |
| Comparing categories | Not cumulative | Bar Chart |
| Showing trends over time | Waterfall is discrete | Line Chart |
| Part-to-whole | Doesn't show total context | Stacked Bar, Pie |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| CATEGORY | Yes | Step names (ordered) |
| MEASURE | Yes | Change values (+/-) |
| TYPE | Yes | "start", "change", or "total" |

## Selection Decision

```
IF intent == "bridge" OR "breakdown of change":
    AND hasStartValue:
    AND hasEndValue:
    AND intermediateSteps:
        → Waterfall Chart
```

## Variants

### Vertical Waterfall
Bars stack vertically, most common.

### Horizontal Waterfall
Bars stack horizontally.

### Nested Waterfall
Sub-categories within steps.

## Critical Rules

> **Order matters.**

Steps must be in logical sequence—this is a cumulative story.

> **Clearly distinguish positive from negative.**

Use color: green for increases, red for decreases.

> **Mark start and end totals.**

First and last bars should be distinguished from change bars.

## See Also

- [Selection Interface](./selection.md)
- [Bar Chart](./selection-bar-chart-vertical.md) — For non-cumulative comparison
