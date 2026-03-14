---
type: action-implementation
action: refinement
chart-type: bar_chart_grouped
tags: [refinement, bar-chart, grouped, classification, comparison, data-series]
---

# Refinement: Bar Chart (Grouped)

Refinement guidance for grouped bar charts comparing multiple measures across categories.

> **Key Principle**: The agent outputs `data_series` with semantic classifications (prominence, purpose, sentiment). The UI handles structural elements (axes, gridlines, borders) via its style guide.

## Sample Data

```json
[
  { "region": "North", "metric": "Actual", "sales": 150000 },
  { "region": "North", "metric": "Target", "sales": 140000 },
  { "region": "South", "metric": "Actual", "sales": 120000 },
  { "region": "South", "metric": "Target", "sales": 145000 },
  { "region": "East", "metric": "Actual", "sales": 175000 },
  { "region": "East", "metric": "Target", "sales": 160000 }
]
```

## DataMapping Configuration

For grouped bars, use `x_axis`, `y_axis`, and `group_by`:

```json
{
  "data_mapping": {
    "x_axis": "region",
    "y_axis": "sales",
    "group_by": "metric"
  }
}
```

| Field | Purpose |
|-------|---------|
| `x_axis` | Category axis (bar groups) |
| `y_axis` | Value axis (bar height) |
| `group_by` | Field that creates bars within each group |

## DataSeries Patterns

### Pattern 1: Equal Comparison (Both Groups Important)

Compare two metrics without favoring either:

```json
{
  "chart_type": "bar_chart_grouped",
  "data_mapping": {
    "x_axis": "region",
    "y_axis": "sales",
    "group_by": "metric"
  },
  "data_series": [
    {
      "series_id": "actual",
      "group_value": "Actual",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Actual Sales"
    },
    {
      "series_id": "target",
      "group_value": "Target",
      "prominence": "primary",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Target"
    }
  ]
}
```

### Pattern 2: Focus vs. Benchmark

One group is the primary focus, other is reference:

```json
{
  "chart_type": "bar_chart_grouped",
  "data_mapping": {
    "x_axis": "quarter",
    "y_axis": "revenue",
    "group_by": "company"
  },
  "data_series": [
    {
      "series_id": "our_company",
      "group_value": "Our Company",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Our Company"
    },
    {
      "series_id": "competitor",
      "group_value": "Competitor",
      "prominence": "secondary",
      "purpose": "reference",
      "sentiment": "neutral",
      "label": "Competitor Avg"
    }
  ]
}
```

### Pattern 3: Performance with Sentiment

Groups carry evaluative meaning based on comparison:

```json
{
  "chart_type": "bar_chart_grouped",
  "data_mapping": {
    "x_axis": "region",
    "y_axis": "sales",
    "group_by": "metric"
  },
  "data_series": [
    {
      "series_id": "actual_above",
      "group_value": "Actual",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "Actual (Above Target)"
    },
    {
      "series_id": "target",
      "group_value": "Target",
      "prominence": "secondary",
      "purpose": "reference",
      "sentiment": "neutral",
      "label": "Target"
    }
  ],
  "highlights": [
    {
      "id": "below_target_regions",
      "type": "points",
      "description": "Regions below target",
      "sentiment": "negative",
      "field_filters": [
        { "field": "region", "values": ["South"] }
      ]
    }
  ]
}
```

### Pattern 4: Multi-Group Comparison

Comparing more than two groups (keep to 4 or fewer):

```json
{
  "chart_type": "bar_chart_grouped",
  "data_mapping": {
    "x_axis": "quarter",
    "y_axis": "units",
    "group_by": "channel"
  },
  "data_series": [
    {
      "series_id": "online",
      "group_value": "Online",
      "prominence": "callout",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "Online (Fastest Growing)"
    },
    {
      "series_id": "retail",
      "group_value": "Retail",
      "prominence": "primary",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Retail"
    },
    {
      "series_id": "wholesale",
      "group_value": "Wholesale",
      "prominence": "primary",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Wholesale"
    }
  ]
}
```

## Element Inventory

| Element | Handled By | Notes |
|---------|------------|-------|
| Bar colors | UI (from `sentiment`) | Each group gets color from classification |
| Bar opacity | UI (from `prominence`) | Callout > primary > secondary |
| X-axis | UI style guide | Category labels |
| Y-axis | UI style guide | Starts at zero |
| Gridlines | UI style guide | Optional, helps comparison |
| Legend | UI style guide | Required for multi-group |
| Gap between groups | UI style guide | Distinguishes categories |
| Title | UI style guide | Primary prominence |

## Gestalt Applications

### Proximity
Bars within a group are closer together than bars between groups. This creates clear category groupings and enables within-category comparison.

### Similarity
All bars of the same measure share the same color across categories. Color creates cross-category grouping, enabling comparison of the same metric across different categories.

## Common Structural Corrections

| Issue | Correction | Rationale |
|-------|------------|-----------|
| Too many groups (>4) | Reduce or use small multiples | Bars become too narrow |
| Inconsistent group order | Standardize order | Same measure should be in same position |
| No legend | Add legend | Groups need identification |
| Groups touching | Add gap between groups | Distinguish categories |

## Group Ordering

1. **Consistent across all categories** — never reorder within categories
2. **Meaningful order if exists** — e.g., Actual before Target
3. **Most important first** — primary measure on left/front

## Decluttering Checklist

- [ ] 4 or fewer groups per category?
- [ ] Consistent group order across categories?
- [ ] Legend present and clear?
- [ ] Gap between category groups?
- [ ] Colors distinguishable?
- [ ] Clear which group is focus vs. comparison?

## See Also

- [Refinement Interface](./refinement.md)
- [Agent-UI Handoff](../03-agent-ui-handoff.md) — Agent vs UI responsibilities
