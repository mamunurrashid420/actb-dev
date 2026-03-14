---
type: action-implementation
action: refinement
chart-type: pie_chart
tags: [refinement, pie_chart, classification, composition, data-series]
---

# Refinement: Pie Chart

Refinement guidance for pie charts showing part-to-whole composition as a filled circle.

> **Key Principle**: The agent outputs `data_series` with semantic classifications (prominence, purpose, sentiment). The UI handles structural elements (axes, gridlines, borders) via its style guide.

## Sample Data

```json
[
  { "category": "Product A", "share": 35 },
  { "category": "Product B", "share": 28 },
  { "category": "Product C", "share": 22 },
  { "category": "Product D", "share": 10 },
  { "category": "Other", "share": 5 }
]
```

## DataMapping Configuration

For pie charts, use `group_by` and `value`:

```json
{
  "data_mapping": {
    "group_by": "category",
    "value": "share"
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
| Title | UI style guide | Primary prominence |

## DataSeries Patterns

### Basic Pie (All Slices Equal Importance)

When showing general composition without emphasis:

```json
{
  "chart_type": "pie_chart",
  "data_mapping": {
    "group_by": "category",
    "value": "share"
  },
  "data_series": [
    {
      "series_id": "product_a",
      "group_value": "Product A",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Product A"
    },
    {
      "series_id": "product_b",
      "group_value": "Product B",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Product B"
    },
    {
      "series_id": "product_c",
      "group_value": "Product C",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Product C"
    },
    {
      "series_id": "product_d",
      "group_value": "Product D",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Product D"
    },
    {
      "series_id": "other",
      "group_value": "Other",
      "prominence": "secondary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Other"
    }
  ]
}
```

### With Highlighted Slice

When one category is the story focus:

```json
{
  "chart_type": "pie_chart",
  "data_mapping": {
    "group_by": "category",
    "value": "share"
  },
  "data_series": [
    {
      "series_id": "product_a",
      "group_value": "Product A",
      "prominence": "callout",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "Product A (Growing!)"
    },
    {
      "series_id": "product_b",
      "group_value": "Product B",
      "prominence": "secondary",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Product B"
    },
    {
      "series_id": "product_c",
      "group_value": "Product C",
      "prominence": "secondary",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Product C"
    },
    {
      "series_id": "other",
      "group_value": "Other",
      "prominence": "background",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Other"
    }
  ]
}
```

## Gestalt Applications

### Proximity

**Principle**: Elements close together are perceived as grouped.

**Pie application**: Labels should be close to their slices. Direct labels on or near slices are better than legends.

### Enclosure

**Principle**: Enclosed elements are perceived as grouped.

**Pie application**: The circle itself provides natural enclosure. No border needed.

### Similarity

**Principle**: Similar elements are perceived as related.

**Pie application**: Each slice is distinct by position. Color should differentiate categories meaningfully.

## Common Structural Corrections

| Issue | Correction | Rationale |
|-------|------------|-----------|
| Too many slices (>5) | Group small into "Other" | Small slices unreadable |
| Legend instead of direct labels | Use direct labels if space | Reduces eye travel |
| 3D effect | Use flat 2D | 3D distorts perception |
| Exploded slices | Keep together | Explosion breaks whole |
| Random slice order | Order by size | Easier to compare |
| Missing percentages | Add value labels | Angles hard to judge |

## Decluttering Checklist

- [ ] 5 or fewer slices (small values grouped)?
- [ ] Each slice has `group_value` matching data?
- [ ] Sentiment reflects business meaning?
- [ ] Labels provided for legend/direct labels?
- [ ] "Other" category uses `secondary` or `background` prominence?

## Handling Many Categories

If data has >5 categories:

1. **Group small values**: Create "Other" slice with `prominence: "secondary"`
2. **Or recommend alternative**: Switch to horizontal bar chart for 8+ categories

## See Also

- [Refinement Interface](./refinement.md)
- [Donut Chart Refinement](./refinement-donut-chart.md) — For donut-specific patterns (center label)
- [Agent-UI Handoff](../03-agent-ui-handoff.md) — Agent vs UI responsibilities
