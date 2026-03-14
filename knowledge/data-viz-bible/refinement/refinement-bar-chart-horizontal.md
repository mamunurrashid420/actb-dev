---
type: action-implementation
action: refinement
chart-type: bar_chart_horizontal
tags: [refinement, bar-chart, horizontal, classification, ranking, data-series]
---

# Refinement: Bar Chart (Horizontal)

Refinement guidance for horizontal bar charts, emphasizing ranking visualization and comparison patterns.

> **Key Principle**: The agent outputs `data_series` with semantic classifications (prominence, purpose, sentiment). The UI handles structural elements (axes, gridlines, borders) via its style guide.

## Sample Data

```json
[
  { "product": "Widget Pro", "sales": 85000 },
  { "product": "Widget Basic", "sales": 62000 },
  { "product": "Widget Plus", "sales": 78000 },
  { "product": "Widget Mini", "sales": 45000 },
  { "product": "Widget Max", "sales": 92000 }
]
```

## DataMapping Configuration

For horizontal bar charts, use `x_axis` and `y_axis`:

```json
{
  "data_mapping": {
    "x_axis": "sales",
    "y_axis": "product"
  }
}
```

| Field | Purpose |
|-------|---------|
| `x_axis` | Value axis (bar length) |
| `y_axis` | Category axis (bar labels) |

**Note**: In horizontal bars, `x_axis` is the value and `y_axis` is the category (opposite of vertical bars).

## Element Inventory

| Element | Handled By | Notes |
|---------|------------|-------|
| Bar colors | UI (from `sentiment`) or default | Agent provides semantic meaning |
| Bar opacity | UI (from `prominence`) | Callout > primary > secondary |
| X-axis | UI style guide | Value labels at bottom |
| Y-axis | UI style guide | Category names |
| Gridlines | UI style guide | Vertical if needed |
| Data labels | UI style guide | Values at end of bars |
| Title | UI style guide | Primary prominence |

## DataSeries Patterns

### Ranking (All Equal Importance)

When showing a simple ranking:

```json
{
  "chart_type": "bar_chart_horizontal",
  "data_mapping": {
    "x_axis": "sales",
    "y_axis": "product"
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

### Focus vs. Comparison (Our Product vs. Others)

When highlighting one category:

```json
{
  "chart_type": "bar_chart_horizontal",
  "data_mapping": {
    "x_axis": "sales",
    "y_axis": "product"
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
        { "field": "product", "values": ["Widget Pro"] }
      ],
      "prominence": "callout",
      "sentiment": "neutral"
    }
  ]
}
```

### Top N Highlight

When emphasizing the top performers:

```json
{
  "chart_type": "bar_chart_horizontal",
  "data_mapping": {
    "x_axis": "sales",
    "y_axis": "product"
  },
  "data_series": [
    {
      "series_id": "sales",
      "field": "sales",
      "prominence": "secondary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Sales"
    }
  ],
  "highlights": [
    {
      "id": "top_3",
      "type": "points",
      "description": "Top 3 Products",
      "field_filters": [
        { "field": "product", "values": ["Widget Max", "Widget Pro", "Widget Plus"] }
      ],
      "prominence": "primary",
      "sentiment": "positive"
    }
  ]
}
```

### Performance Threshold

When comparing to a target:

```json
{
  "chart_type": "bar_chart_horizontal",
  "data_mapping": {
    "x_axis": "sales",
    "y_axis": "product"
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
      "threshold_value": 70000,
      "sentiment": "neutral"
    },
    {
      "id": "above_target",
      "type": "points",
      "description": "Above Target",
      "field_filters": [
        { "field": "product", "values": ["Widget Max", "Widget Pro", "Widget Plus"] }
      ],
      "sentiment": "positive"
    },
    {
      "id": "below_target",
      "type": "points",
      "description": "Below Target",
      "field_filters": [
        { "field": "product", "values": ["Widget Basic", "Widget Mini"] }
      ],
      "sentiment": "negative"
    }
  ]
}
```

## Gestalt Applications

### Proximity

**Principle**: Elements close together are perceived as grouped.

**Horizontal bar application**: 
- Category labels close to their bars create clear association
- Data labels at the end of bars maintain proximity
- Consistent spacing between bars creates even rhythm

### Similarity

**Principle**: Similar elements are perceived as related.

**Horizontal bar application**:
- Comparison bars should all share the same neutral color
- Only the focus bar should be different
- Consistent label styling across all categories

### Continuity

**Principle**: The eye follows the smoothest path.

**Horizontal bar application**:
- Sorted bars create a natural diagonal line from longest to shortest
- This "staircase" pattern is easy to scan
- Unsorted bars break this flow and confuse

**Refinement implication**: Always recommend sorting unless there's a meaningful categorical order.

## Common Structural Corrections

| Issue | Correction | Rationale |
|-------|------------|-----------|
| Unsorted bars | Sort descending or ascending | Eye expects ranked list |
| X-axis not at zero | Start at zero | Bar length must be proportional |
| Gridlines prominent | `hide` or `background` | Bars show magnitude directly |
| Labels truncated | Increase left margin | Labels should be fully readable |
| Multiple colors no meaning | Single color + highlight | Avoid false categorical encoding |

## Decluttering Checklist

- [ ] Single value field correctly mapped?
- [ ] Highlights used for top N or focus items?
- [ ] Sentiment reflects performance vs. target?
- [ ] Labels provided for legend generation?
- [ ] Threshold highlights for reference lines?

## Sentiment Assignment

| Scenario | Sentiment |
|----------|-----------|
| Revenue/sales ranking | `neutral` (unless highlighting good/bad) |
| Top performers | `positive` for top N |
| Bottom performers | `negative` for bottom N |
| Above target | `positive` |
| Below target | `negative` |
| Focus item vs. comparison | Focus `neutral`, comparison `neutral` |

## Highlight Strategies

### Focus Category (Hawk in Pigeons)

```json
{
  "data_series": [
    { "series_id": "sales", "field": "sales", "prominence": "secondary", "purpose": "data-comparison", "sentiment": "neutral" }
  ],
  "highlights": [
    { "id": "focus", "type": "points", "field_filters": [{ "field": "product", "values": ["Widget Pro"] }], "prominence": "callout" }
  ]
}
```

**Result**: Focus bar in accent color, all others in light gray.

### Top N Performance

```json
{
  "highlights": [
    { "id": "top_3", "type": "points", "field_filters": [{ "field": "product", "values": ["Widget Max", "Widget Pro", "Widget Plus"] }], "sentiment": "positive" },
    { "id": "rest", "type": "points", "field_filters": [{ "field": "product", "values": ["Widget Basic", "Widget Mini"] }], "sentiment": "neutral" }
  ]
}
```

**Result**: Top 3 bars in green, rest in neutral.

## See Also

- [Refinement Interface](./refinement.md) — Full process and principles
- [Classification System](../02-classification-system.md) — Multi-axis reference
- [Agent-UI Handoff](../03-agent-ui-handoff.md) — Agent vs UI responsibilities
