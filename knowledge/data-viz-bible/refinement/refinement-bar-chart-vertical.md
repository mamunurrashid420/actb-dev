---
type: action-implementation
action: refinement
chart-type: bar_chart_vertical
tags: [refinement, bar-chart, classification, comparison, declutter, data-series]
---

# Refinement: Bar Chart (Vertical)

Refinement guidance specific to vertical bar charts, applying classification and design principles.

> **Key Principle**: The agent outputs `data_series` with semantic classifications (prominence, purpose, sentiment). The UI handles structural elements (axes, gridlines, borders) via its style guide.

## Sample Data

```json
[
  { "category": "Product A", "sales": 45000 },
  { "category": "Product B", "sales": 32000 },
  { "category": "Product C", "sales": 58000 },
  { "category": "Product D", "sales": 27000 },
  { "category": "Product E", "sales": 41000 }
]
```

## DataMapping Configuration

For vertical bar charts, use `x_axis` and `y_axis`:

```json
{
  "data_mapping": {
    "x_axis": "category",
    "y_axis": "sales"
  }
}
```

| Field | Purpose |
|-------|---------|
| `x_axis` | Category axis (bar labels) |
| `y_axis` | Value axis (bar height) |

## Element Inventory

Elements typically present in a vertical bar chart:

| Element | Handled By | Notes |
|---------|------------|-------|
| Bar colors | UI (from `sentiment`) or default | Agent provides semantic meaning |
| Bar opacity | UI (from `prominence`) | Callout > primary > secondary |
| X-axis | UI style guide | Category labels |
| Y-axis | UI style guide | Starts at zero |
| Gridlines | UI style guide | Hidden by default |
| Data labels | UI style guide | Optional |
| Legend | UI style guide | Only if multiple series |
| Title | UI style guide | Primary prominence |

## DataSeries Patterns

### Single Series (All Equal Importance)

When all bars are equally important:

```json
{
  "chart_type": "bar_chart_vertical",
  "data_mapping": {
    "x_axis": "category",
    "y_axis": "sales"
  },
  "data_series": [
    {
      "series_id": "sales",
      "field": "sales",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Sales"
    }
  ]
}
```

### Single Series with Highlight (One Bar Emphasized)

When one category is the focus:

```json
{
  "chart_type": "bar_chart_vertical",
  "data_mapping": {
    "x_axis": "category",
    "y_axis": "sales"
  },
  "data_series": [
    {
      "series_id": "sales",
      "field": "sales",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Sales"
    }
  ],
  "highlights": [
    {
      "id": "highlight_top",
      "insight_id": "insight_winner",
      "type": "points",
      "description": "Top Performer",
      "field_filters": [
        { "field": "category", "values": ["Product C"] }
      ],
      "sentiment": "positive"
    }
  ]
}
```

### With Target/Threshold Reference

When comparing bars to a benchmark:

```json
{
  "chart_type": "bar_chart_vertical",
  "data_mapping": {
    "x_axis": "category",
    "y_axis": "sales"
  },
  "data_series": [
    {
      "series_id": "sales",
      "field": "sales",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Sales"
    }
  ],
  "highlights": [
    {
      "id": "target_line",
      "type": "threshold",
      "description": "Sales Target",
      "threshold_value": 40000,
      "sentiment": "neutral"
    },
    {
      "id": "below_target",
      "type": "points",
      "description": "Below Target",
      "field_filters": [
        { "field": "category", "values": ["Product B", "Product D"] }
      ],
      "sentiment": "negative"
    }
  ]
}
```

### Comparison Pattern (This vs. That)

When highlighting focus category:

```json
{
  "chart_type": "bar_chart_vertical",
  "data_mapping": {
    "x_axis": "category",
    "y_axis": "sales"
  },
  "data_series": [
    {
      "series_id": "sales",
      "field": "sales",
      "prominence": "secondary",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Sales"
    }
  ],
  "highlights": [
    {
      "id": "our_product",
      "type": "points",
      "description": "Our Product",
      "field_filters": [
        { "field": "category", "values": ["Product A"] }
      ],
      "prominence": "callout",
      "sentiment": "neutral"
    }
  ]
}
```

## Gestalt Applications

### Similarity

**Principle**: Similar elements are perceived as related.

**Bar chart application**: Bars of the same color are perceived as belonging to the same category or having the same meaning. Use this intentionally.

**Refinement implication**: 
- All comparison bars should share the same neutral color
- Only the focus bar(s) should have accent color
- Don't use different colors without semantic meaning

### Proximity

**Principle**: Elements close together are perceived as grouped.

**Bar chart application**: 
- Data labels should be close to their bars
- Bars within a group (in grouped bar charts) are closer together

### Closure

**Principle**: The mind completes incomplete shapes.

**Bar chart application**: Chart borders and full axis boxes are unnecessary—the bars themselves create visual closure.

## Common Structural Corrections

| Issue | Correction | Rationale |
|-------|------------|-----------|
| Diagonal x-axis labels | Switch to Horizontal Bar | Labels should never be diagonal |
| Y-axis not starting at zero | Start at zero | Truncated axis misleads bar comparisons |
| Bars too narrow | Reduce categories or widen chart | Bars should be wider than gaps |
| Too many colors | Single color + highlight | Hawk-in-pigeons principle |
| Center-aligned title | `left-aligned` | Clean visual edge |
| Gridlines prominent | `hide` | Bars communicate values directly |

## Decluttering Checklist

- [ ] Single value field correctly mapped?
- [ ] Highlights used for emphasis (not multiple data_series)?
- [ ] Sentiment reflects business meaning (above/below target)?
- [ ] Labels provided for legend generation?
- [ ] Threshold highlights for reference lines?

## Sentiment Assignment for Bar Charts

| Scenario | Sentiment |
|----------|-----------|
| Sales/revenue (higher is better) | `positive` for high, `negative` for low |
| Costs/expenses (lower is better) | `negative` for high, `positive` for low |
| Neutral comparison (no good/bad) | `neutral` for all |
| Above target | `positive` |
| Below target | `negative` |
| At-risk threshold | `warning` |

## Highlight Strategies

### Maximum Value Highlight

```json
{
  "highlights": [
    {
      "id": "max_highlight",
      "type": "points",
      "description": "Top Performer",
      "field_filters": [{ "field": "category", "values": ["Product C"] }],
      "prominence": "callout",
      "sentiment": "positive"
    }
  ]
}
```

### Threshold-Based Highlight

```json
{
  "highlights": [
    {
      "id": "threshold_line",
      "type": "threshold",
      "threshold_value": 40000
    },
    {
      "id": "above_threshold",
      "type": "points",
      "field_filters": [{ "field": "category", "values": ["Product A", "Product C", "Product E"] }],
      "sentiment": "positive"
    },
    {
      "id": "below_threshold",
      "type": "points",
      "field_filters": [{ "field": "category", "values": ["Product B", "Product D"] }],
      "sentiment": "negative"
    }
  ]
}
```

## See Also

- [Refinement Interface](./refinement.md) — Full process and principles
- [Classification System](../02-classification-system.md) — Multi-axis reference
- [Agent-UI Handoff](../03-agent-ui-handoff.md) — Agent vs UI responsibilities
