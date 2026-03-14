---
type: action-implementation
action: refinement
chart-type: donut_chart
tags: [refinement, donut_chart, classification, composition, data-series, dashboard]
---

# Refinement: Donut Chart

Refinement guidance for donut charts showing part-to-whole composition with a hollow center for annotation.

> **Key Principle**: The agent outputs `data_series` with semantic classifications (prominence, purpose, sentiment). The UI handles structural elements (axes, gridlines, borders, center label) via its style guide.

## Key Differentiator from Pie

The donut chart's center is **semantic real estate**. The UI can render a total, KPI, or descriptive label in the center. The agent should consider this when designing the chart — the donut is a **component** in a dashboard, not a standalone statement.

## Sample Data

```json
[
  { "status": "On Track", "count": 45 },
  { "status": "At Risk", "count": 12 },
  { "status": "Behind", "count": 8 }
]
```

## DataMapping Configuration

For donut charts, use `group_by` and `value`:

```json
{
  "data_mapping": {
    "group_by": "status",
    "value": "count"
  }
}
```

| Field | Purpose |
|-------|---------|
| `group_by` | Field that defines slice categories |
| `value` | Field containing the numeric value for slice size |

## Element Inventory

| Element | Handled By | Notes |
|---------|------------|-------|
| Slice colors | UI (from `sentiment`) or categorical palette | Each slice gets color from classification |
| Slice opacity | UI (from `prominence`) | Callout > primary > secondary |
| Slice labels | UI style guide | Category names |
| Value labels | UI style guide | Percentages/values |
| Legend | UI style guide | If not using direct labels |
| **Center label** | **UI style guide** | **Donut-specific — total/title/KPI** |
| Title | UI style guide | Primary prominence |

## DataSeries Patterns

### Donut with Performance Sentiment

When slices have evaluative meaning:

```json
{
  "chart_type": "donut_chart",
  "data_mapping": {
    "group_by": "status",
    "value": "count"
  },
  "data_series": [
    {
      "series_id": "on_track",
      "group_value": "On Track",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "On Track"
    },
    {
      "series_id": "at_risk",
      "group_value": "At Risk",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "warning",
      "label": "At Risk"
    },
    {
      "series_id": "behind",
      "group_value": "Behind",
      "prominence": "callout",
      "purpose": "data-focus",
      "sentiment": "negative",
      "label": "Behind Schedule"
    }
  ]
}
```

### Revenue Split with Total in Center

When showing composition with a summary metric:

```json
{
  "chart_type": "donut_chart",
  "data_mapping": {
    "group_by": "region",
    "value": "revenue"
  },
  "data_series": [
    {
      "series_id": "north_america",
      "group_value": "North America",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "North America"
    },
    {
      "series_id": "europe",
      "group_value": "Europe",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Europe"
    },
    {
      "series_id": "asia_pacific",
      "group_value": "Asia Pacific",
      "prominence": "secondary",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "Asia Pacific"
    },
    {
      "series_id": "other",
      "group_value": "Other",
      "prominence": "background",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Other Regions"
    }
  ]
}
```

### Dashboard Tile with Equal Slices

When used as a compact overview in a dashboard grid:

```json
{
  "chart_type": "donut_chart",
  "data_mapping": {
    "group_by": "category",
    "value": "amount"
  },
  "data_series": [
    {
      "series_id": "marketing",
      "group_value": "Marketing",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Marketing"
    },
    {
      "series_id": "engineering",
      "group_value": "Engineering",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Engineering"
    },
    {
      "series_id": "sales",
      "group_value": "Sales",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Sales"
    }
  ]
}
```

## Gestalt Applications

### Proximity

**Principle**: Elements close together are perceived as grouped.

**Donut application**: Labels should be close to their slices. The center label relates to the whole.

### Enclosure

**Principle**: Enclosed elements are perceived as grouped.

**Donut application**: The ring provides natural enclosure. The center creates a focal point for summary information.

### Similarity

**Principle**: Similar elements are perceived as related.

**Donut application**: Each slice is distinct by position. Color should differentiate categories meaningfully.

## Common Structural Corrections

| Issue | Correction | Rationale |
|-------|------------|-----------|
| Too many slices (>5) | Group small into "Other" | Small slices unreadable |
| Empty center | Add total or label | Wasted semantic real estate |
| Legend instead of direct labels | Use direct labels if space | Reduces eye travel |
| 3D effect | Use flat 2D | 3D distorts perception |
| Random slice order | Order by size | Easier to compare |
| Missing percentages | Add value labels | Arc lengths hard to judge |

## Decluttering Checklist

- [ ] 5 or fewer slices (small values grouped)?
- [ ] Each slice has `group_value` matching data?
- [ ] Sentiment reflects business meaning?
- [ ] Labels provided for legend/direct labels?
- [ ] "Other" category uses `secondary` or `background` prominence?
- [ ] Center annotation is meaningful (total, KPI, label)?

## Handling Many Categories

If data has >5 categories:

1. **Group small values**: Create "Other" slice with `prominence: "secondary"`
2. **Or recommend alternative**: Switch to horizontal bar chart for 8+ categories

## See Also

- [Refinement Interface](./refinement.md)
- [Pie Chart Refinement](./refinement-pie-chart.md) — For standalone pie-specific patterns
- [Agent-UI Handoff](../03-agent-ui-handoff.md) — Agent vs UI responsibilities
