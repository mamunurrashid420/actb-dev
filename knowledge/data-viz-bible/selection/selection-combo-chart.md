---
type: action-implementation
action: selection
chart-type: combo
aliases: [combination chart, mixed chart, dual-axis chart, multi-chart]
data-pattern: multi-measure-different-scales
family: composition
priority: P2
tags: [selection, combo, composition, dual-axis, multi-chart, sub-charts]
---

# Selection: Combo Chart

Renders multiple chart types together as a composition of independent sub-charts. Each sub-chart is a fully self-contained chart spec that shares the parent's data but uses its own data mapping and visual encoding.

## When to Use

- **Measures on different scales**: Revenue in dollars alongside margin in percentage — a single Y-axis cannot serve both
- **Different visual encodings for different measures**: Bars for absolute values, lines for trends, areas for cumulative totals
- **Multi-layered insights**: The user's question spans multiple aspects that benefit from different chart types (e.g., "Show revenue breakdown AND trend")
- **Dashboard-like compositions**: Grouping related charts that share a common dimension (time, category)

### Data Pattern

- 1 SHARED DIMENSION (time or category) + 2+ MEASURE GROUPS with different units or scales
- Each measure group maps naturally to a different chart type
- Measures are conceptually related but visually incompatible on a single chart

### User Intent Signals

Queries that suggest a combo chart:
- "Show X **and** Y together" (where X and Y have different units)
- "Revenue with profit margin trend"
- "Compare volumes (bars) with growth rate (line)"
- "Plot sales alongside conversion rate"
- "Show breakdown AND trend"

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| All measures share the same scale | No need for separate charts | `bar_chart_grouped`, `line_chart` with multi-series |
| Only one measure type | Combo adds unnecessary complexity | Single chart type |
| Measures are unrelated | Co-location implies false correlation | Separate independent charts |
| More than 3 sub-charts | Cognitive overload | Dashboard layout with independent charts |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| SHARED DIMENSION | Yes | Common X-axis across sub-charts (time, category) |
| MEASURE GROUP 1 | Yes | Fields for first sub-chart (e.g., revenue, costs) |
| MEASURE GROUP 2 | Yes | Fields for second sub-chart (e.g., margin percentage) |

## Combo Structure

A combo chart is a **parent Chart** with `chart_type: combo` that contains `sub_charts` — each a complete chart spec:

```
Parent (combo):
  chart_type: combo
  title: "Overall title"
  sub_charts:
    - chart_type: bar_chart_vertical  (sub-chart 1)
    - chart_type: line_chart          (sub-chart 2)
```

Each sub-chart:
- Has its own `id`, `chart_type`, `title`, `data_mapping`, `data_series`
- Inherits the parent's `chart_data_slice_ids` (shared data)
- Uses its own `data_mapping` to select which fields to render

## Common Combo Patterns

| Pattern | Sub-chart 1 | Sub-chart 2 | Example |
|---------|-------------|-------------|---------|
| Bar + Line | `bar_chart_vertical` (absolute values) | `line_chart` (rate/trend) | Revenue bars + margin line |
| Bar + Area | `bar_chart_vertical` (discrete values) | `area_chart` (cumulative) | Monthly sales + running total |
| Grouped Bar + Line | `bar_chart_grouped` (comparison) | `line_chart` (ratio) | Actual vs budget + variance % |
| Stacked Bar + Line | `bar_chart_stacked` (composition) | `line_chart` (total trend) | Category breakdown + total |

## Selection Decision

```
IF measures have different units/scales:
  AND measures share a common dimension:
    AND measures are conceptually related:
      → combo
    ELSE:
      → separate independent charts
  ELSE:
    → separate independent charts
ELSE:
  → single chart type (bar_chart_grouped, line_chart multi-series, etc.)
```

## Alternatives Comparison

| Chart Type | When to Prefer Over Combo |
|------------|--------------------------|
| `bar_chart_grouped` | All measures share the same unit and scale |
| `line_chart` (multi-series) | All measures are trends on the same scale |
| `area_chart` (stacked) | Part-of-whole over time, same unit |
| Separate dashboard charts | Measures are unrelated, no shared dimension |

## Critical Rules

1. **Maximum 3 sub-charts** — more than 3 creates cognitive overload
2. **Shared dimension** — all sub-charts must share the same X-axis dimension
3. **Different scales** — if measures fit on the same scale, prefer a single multi-series chart
4. **Each sub-chart is complete** — every sub-chart must have its own `chart_type`, `data_mapping`, and `data_series`
