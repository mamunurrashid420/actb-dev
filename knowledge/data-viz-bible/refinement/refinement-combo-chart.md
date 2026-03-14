---
type: action-implementation
action: refinement
chart-type: combo
tags: [refinement, combo, composition, sub-charts, classification, data-series]
---

# Refinement: Combo Chart

Refinement guidance for combo charts. A combo is a composition of independent sub-charts, each rendered by its own chart type. The agent's job is to define each sub-chart's data mapping and data series classifications.

> **Key Principle**: Each sub-chart is a complete, self-contained chart spec. The agent defines `data_mapping` and `data_series` per sub-chart. The UI handles layout (responsive flex/grid).

## Sample Data

```json
[
  { "quarter": "Q1 2024", "revenue": 12000, "operating_costs": 8000, "profit_margin_pct": 33 },
  { "quarter": "Q2 2024", "revenue": 15000, "operating_costs": 9500, "profit_margin_pct": 37 },
  { "quarter": "Q3 2024", "revenue": 13500, "operating_costs": 8800, "profit_margin_pct": 35 },
  { "quarter": "Q4 2024", "revenue": 18000, "operating_costs": 11000, "profit_margin_pct": 39 }
]
```

## Combo Structure

The parent chart has `chart_type: "combo"` and contains `sub_charts`:

```json
{
  "chart_type": "combo",
  "title": "Revenue vs Costs with Profit Margin",
  "sub_charts": [
    {
      "id": "combo__bars",
      "chart_type": "bar_chart_vertical",
      "title": "Revenue & Operating Costs",
      "data_mapping": { "x_axis": "quarter", "y_axis": "revenue" },
      "data_series": [...]
    },
    {
      "id": "combo__line",
      "chart_type": "line_chart",
      "title": "Profit Margin Trend",
      "data_mapping": { "x_axis": "quarter", "y_axis": "profit_margin_pct" },
      "data_series": [...]
    }
  ]
}
```

## Sub-Chart DataMapping

Each sub-chart defines its own `data_mapping`:

| Sub-chart | `x_axis` | `y_axis` | `group_by` | Notes |
|-----------|----------|----------|------------|-------|
| Bar (revenue/costs) | `quarter` | `revenue` | — | Multiple fields via data_series |
| Line (margin) | `quarter` | `profit_margin_pct` | — | Single series |

The **shared dimension** (`quarter`) must be consistent across all sub-charts.

## DataSeries Patterns

### Pattern: Bar Sub-chart (Multiple Measures)

```json
{
  "data_series": [
    {
      "series_id": "revenue",
      "field": "revenue",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "Revenue"
    },
    {
      "series_id": "costs",
      "field": "operating_costs",
      "prominence": "secondary",
      "purpose": "data-comparison",
      "sentiment": "negative",
      "label": "Operating Costs"
    }
  ]
}
```

### Pattern: Line Sub-chart (Rate/Trend)

```json
{
  "data_series": [
    {
      "series_id": "margin",
      "field": "profit_margin_pct",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "Profit Margin %"
    }
  ]
}
```

## Element Inventory (UI Style Guide Reference)

The parent combo chart's elements are handled by the UI:

| Element | Handling | Notes |
|---------|----------|-------|
| Parent title | Rendered above all sub-charts | Single overall title |
| Sub-chart titles | Each sub-chart has its own title | Rendered by individual components |
| Layout | Responsive flex/grid | UI decides side-by-side vs. stacked |
| Legends | Per sub-chart | Each component manages its own legend |

Individual sub-chart elements (axes, gridlines, etc.) follow their respective chart type's refinement rules (e.g., line chart rules for the line sub-chart).

## Common Structural Corrections

| Issue | Fix |
|-------|-----|
| Sub-charts have different X-axis dimensions | Ensure all sub-charts share the same `x_axis` field |
| Too many sub-charts (>3) | Reduce to the most important 2-3 measure groups |
| Sub-chart measures share the same scale | Combine into a single multi-series chart instead |
| Missing data_series on a sub-chart | Every sub-chart must have at least one data_series entry |

## Decluttering Checklist

- [ ] Parent title summarizes the overall insight; sub-chart titles are specific
- [ ] Each sub-chart uses the same X-axis dimension for visual alignment
- [ ] Sub-chart titles are concise (avoid repeating the parent title)
- [ ] Data series labels are descriptive (not raw field names)
- [ ] No more than 3 sub-charts in a single combo
