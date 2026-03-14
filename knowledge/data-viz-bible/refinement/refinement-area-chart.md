---
type: action-implementation
action: refinement
chart-type: area_chart
tags: [refinement, area, classification, trends, data-series]
---

# Refinement: Area Chart

Refinement guidance for area charts showing trends with magnitude.

> **Key Principle**: The agent outputs `data_series` with semantic classifications (prominence, purpose, sentiment). The UI handles structural elements (axes, gridlines, borders) via its style guide.

## Sample Data

```json
[
  { "month": "2024-01", "category": "Online", "revenue": 85000 },
  { "month": "2024-01", "category": "Retail", "revenue": 65000 },
  { "month": "2024-02", "category": "Online", "revenue": 92000 },
  { "month": "2024-02", "category": "Retail", "revenue": 68000 },
  { "month": "2024-03", "category": "Online", "revenue": 105000 },
  { "month": "2024-03", "category": "Retail", "revenue": 72000 }
]
```

## DataMapping Configuration

For area charts, use `x_axis`, `y_axis`, and optionally `group_by`:

```json
{
  "data_mapping": {
    "x_axis": "month",
    "y_axis": "revenue",
    "group_by": "category"
  }
}
```

| Field | Purpose |
|-------|---------|
| `x_axis` | Time or category axis |
| `y_axis` | Value axis |
| `group_by` | Field that creates stacked areas |

## DataSeries Patterns

### Single Area

When showing one metric with magnitude over time:

```json
{
  "chart_type": "area_chart",
  "data_mapping": {
    "x_axis": "month",
    "y_axis": "revenue"
  },
  "data_series": [
    {
      "series_id": "revenue",
      "field": "revenue",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Revenue"
    }
  ]
}
```

### Stacked Areas (Part-to-Whole Over Time)

When showing composition changing over time:

```json
{
  "chart_type": "area_chart",
  "data_mapping": {
    "x_axis": "month",
    "y_axis": "revenue",
    "group_by": "category"
  },
  "data_series": [
    {
      "series_id": "online",
      "group_value": "Online",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "Online Sales"
    },
    {
      "series_id": "retail",
      "group_value": "Retail",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Retail Sales"
    }
  ]
}
```

### With Forecast Region

When showing historical data with projections:

```json
{
  "chart_type": "area_chart",
  "data_mapping": {
    "x_axis": "month",
    "y_axis": "revenue"
  },
  "data_series": [
    {
      "series_id": "actual",
      "field": "actual_revenue",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Actual Revenue"
    },
    {
      "series_id": "forecast",
      "field": "forecast_revenue",
      "prominence": "secondary",
      "purpose": "data-projection",
      "sentiment": "neutral",
      "label": "Forecast"
    }
  ]
}
```

### With Highlighted Focus

When one area is the story focus:

```json
{
  "chart_type": "area_chart",
  "data_mapping": {
    "x_axis": "month",
    "y_axis": "revenue",
    "group_by": "category"
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
      "prominence": "secondary",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Retail"
    },
    {
      "series_id": "wholesale",
      "group_value": "Wholesale",
      "prominence": "secondary",
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
| Area fill colors | UI (from `sentiment`) | Each area gets color from classification |
| Area opacity | UI (from `prominence`) | Callout > primary > secondary |
| Top edge line | UI style guide | Shows exact trend |
| X-axis | UI style guide | Baseline prominence |
| Y-axis | UI style guide | Starts at zero |
| Gridlines | UI style guide | Hidden by default |
| Legend | UI style guide | Required for stacked areas |
| Title | UI style guide | Primary prominence |

## Gestalt Applications

### Enclosure

**Principle**: Enclosed elements are perceived as grouped.

**Area application**: The filled area creates natural enclosure. The area beneath the line emphasizes cumulative magnitude.

### Continuity

**Principle**: The eye follows the smoothest path.

**Area application**: The top edge of the area acts like a line, showing trend. The fill adds magnitude context while the edge shows direction.

## Common Structural Corrections

| Issue | Correction | Rationale |
|-------|------------|-----------|
| Multiple overlapping areas | Stack or use lines | Overlap is confusing |
| Too dark fill | Reduce opacity | Shouldn't overwhelm |
| Missing top line | Add visible line | Helps read exact trend |
| Y-axis not at zero | Start at zero | Area charts must start at zero |
| Too many stacked areas | Combine into "Other" | Pattern becomes noise |

## Decluttering Checklist

- [ ] Single area or properly stacked (no overlap)?
- [ ] Y-axis starts at zero?
- [ ] Sentiment correctly assigned to each area?
- [ ] Labels provided for legend?
- [ ] Forecast areas using `data-projection` purpose?
- [ ] 5 or fewer stacked areas?

## Area Ordering (Stacked)

For stacked areas, order matters:

1. **Most stable at bottom** — provides consistent baseline
2. **Most volatile at top** — easier to see changes
3. **Focus area at top or bottom** — easiest to compare
4. **Consistent order across time** — don't reorder

## See Also

- [Refinement Interface](./refinement.md)
- [Agent-UI Handoff](../03-agent-ui-handoff.md) — Agent vs UI responsibilities
