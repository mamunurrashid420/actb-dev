---
type: action-implementation
action: refinement
chart-type: bar_chart_stacked
tags: [refinement, bar-chart, stacked, classification, composition, data-series]
---

# Refinement: Bar Chart (Stacked)

Refinement guidance for stacked bar charts showing part-to-whole composition.

> **Key Principle**: The agent outputs `data_series` with semantic classifications (prominence, purpose, sentiment). The UI handles structural elements (axes, gridlines, borders) via its style guide.

## Sample Data

```json
[
  { "quarter": "Q1", "product": "Widget A", "revenue": 120000 },
  { "quarter": "Q1", "product": "Widget B", "revenue": 85000 },
  { "quarter": "Q1", "product": "Services", "revenue": 45000 },
  { "quarter": "Q2", "product": "Widget A", "revenue": 135000 },
  { "quarter": "Q2", "product": "Widget B", "revenue": 92000 },
  { "quarter": "Q2", "product": "Services", "revenue": 58000 }
]
```

## DataMapping Configuration

For stacked bars, use `x_axis`, `y_axis`, and `group_by`:

```json
{
  "data_mapping": {
    "x_axis": "quarter",
    "y_axis": "revenue",
    "group_by": "product"
  }
}
```

| Field | Purpose |
|-------|---------|
| `x_axis` | Category axis (bars) |
| `y_axis` | Value axis (segment height) |
| `group_by` | Field that creates stacked segments |

## DataSeries Patterns

### Pattern 1: Equal Segments (Composition Overview)

All segments have equal importance:

```json
{
  "chart_type": "bar_chart_stacked",
  "data_mapping": {
    "x_axis": "quarter",
    "y_axis": "revenue",
    "group_by": "product"
  },
  "data_series": [
    {
      "series_id": "widget_a",
      "group_value": "Widget A",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Widget A"
    },
    {
      "series_id": "widget_b",
      "group_value": "Widget B",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Widget B"
    },
    {
      "series_id": "services",
      "group_value": "Services",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Services"
    }
  ]
}
```

### Pattern 2: Highlighted Segment (Story Focus)

One segment is the story's focus:

```json
{
  "chart_type": "bar_chart_stacked",
  "data_mapping": {
    "x_axis": "quarter",
    "y_axis": "revenue",
    "group_by": "product"
  },
  "data_series": [
    {
      "series_id": "services",
      "group_value": "Services",
      "prominence": "callout",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "Services (Growing!)"
    },
    {
      "series_id": "widget_a",
      "group_value": "Widget A",
      "prominence": "secondary",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Widget A"
    },
    {
      "series_id": "widget_b",
      "group_value": "Widget B",
      "prominence": "secondary",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Widget B"
    }
  ]
}
```

### Pattern 3: Performance Sentiment

Segments have evaluative meaning:

```json
{
  "chart_type": "bar_chart_stacked",
  "data_mapping": {
    "x_axis": "quarter",
    "y_axis": "cost",
    "group_by": "category"
  },
  "data_series": [
    {
      "series_id": "fixed_costs",
      "group_value": "Fixed Costs",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Fixed Costs"
    },
    {
      "series_id": "variable_costs",
      "group_value": "Variable Costs",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "negative",
      "label": "Variable Costs (Rising)"
    },
    {
      "series_id": "waste",
      "group_value": "Waste",
      "prominence": "callout",
      "purpose": "data-focus",
      "sentiment": "negative",
      "label": "Waste (Problem Area)"
    }
  ]
}
```

## Element Inventory

| Element | Handled By | Notes |
|---------|------------|-------|
| Segment colors | UI (from `sentiment`) | Each segment gets color from classification |
| Segment opacity | UI (from `prominence`) | Callout > primary > secondary |
| X-axis | UI style guide | Baseline prominence |
| Y-axis | UI style guide | Starts at zero |
| Gridlines | UI style guide | Hidden by default |
| Legend | UI style guide | Required for multi-segment |
| Title | UI style guide | Primary prominence |

## Gestalt Applications

### Proximity
Segments within a bar are perceived as parts of a whole because they're stacked together. The physical adjacency reinforces the part-to-whole relationship.

### Enclosure
Each bar encloses its segments, creating natural grouping without needing explicit borders.

## Common Structural Corrections

| Issue | Correction | Rationale |
|-------|------------|-----------|
| Too many segments (>5) | Combine small segments into "Other" | Indistinguishable colors |
| Random segment order | Order by size (largest at bottom) | Bottom segment easiest to compare |
| No legend | Add legend | Segments need identification |
| Important segment not at bottom | Move to bottom | Only bottom has common baseline |

## Segment Ordering Strategy

The order of segments in stacked bars matters for readability:

1. **Most important segment at bottom** — only baseline that's easy to compare
2. **Second most important at top** — next easiest to compare
3. **Order by average size** — if no importance hierarchy
4. **Consistent order across all bars** — don't reorder segments per bar

## Decluttering Checklist

- [ ] 5 or fewer segments?
- [ ] Most important segment at bottom?
- [ ] Legend present and clear?
- [ ] Y-axis starts at zero?
- [ ] Colors distinguishable?
- [ ] Segment labels accessible?

## See Also

- [Refinement Interface](./refinement.md)
- [Agent-UI Handoff](../03-agent-ui-handoff.md) — Agent vs UI responsibilities
