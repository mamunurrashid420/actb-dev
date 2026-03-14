---
type: action-implementation
action: refinement
chart-type: line_chart
tags: [refinement, line_chart, classification, trends, declutter, gestalt, data-series]
---

# Refinement: Line Chart

Refinement guidance specific to line charts, applying classification and design principles to transform a basic line chart into an effective trend visualization.

> **Key Principle**: The agent outputs `data_series` with semantic classifications (prominence, purpose, sentiment). The UI handles structural elements (axes, gridlines, borders) via its style guide.

## Sample Data

```json
[
  { "month": "2024-01", "metric_type": "Revenue", "value": 120000 },
  { "month": "2024-01", "metric_type": "Costs", "value": 85000 },
  { "month": "2024-02", "metric_type": "Revenue", "value": 135000 },
  { "month": "2024-02", "metric_type": "Costs", "value": 88000 },
  { "month": "2024-03", "metric_type": "Revenue", "value": 142000 },
  { "month": "2024-03", "metric_type": "Costs", "value": 91000 }
]
```

## DataMapping Configuration

For line charts, use `x_axis`, `y_axis`, and optionally `group_by`:

```json
{
  "data_mapping": {
    "x_axis": "month",
    "y_axis": "value",
    "group_by": "metric_type"
  }
}
```

| Field | Purpose |
|-------|---------|
| `x_axis` | Time or category axis (typically temporal) |
| `y_axis` | Value axis |
| `group_by` | Field that creates multiple lines |

## Element Inventory (UI Style Guide Reference)

The following elements are handled by the **UI style guide** with consistent defaults. The agent does not output classifications for these elements.

| Element | UI Default Prominence | UI Default Purpose | Notes |
|---------|----------------------|-------------------|-------|
| `chartBorder` | `hide` | `structural` | Remove per closure principle |
| `gridlines` | `hide` | `structural` | Trends usually don't need precise reading |
| `xAxisLine` | `baseline` | `structural` | Keep for grounding |
| `yAxisLine` | `hide` | `structural` | Continuity principle: white space provides alignment |
| `xAxisLabels` | `baseline` | `navigational` | Time labels |
| `yAxisLabels` | `baseline` | `navigational` | Value labels |
| `dataMarkers` | usually `hide` | `data-focus` | Only for sparse data |
| `legend` | `hide` or `baseline` | `navigational` | Prefer direct labels |
| `title` | `primary` | `navigational` | Left-align |

**The agent outputs classifications for data series only** - see Data Series Classification Patterns below.

## Data Series Classification Patterns

### Single Series (Trend Focus)

When showing one metric over time:

```json
{
  "chart_type": "line_chart",
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
      "sentiment": "positive",
      "label": "Revenue"
    }
  ]
}
```

### Multi-Series (Focus vs. Comparison)

When one series is primary and others provide context:

```json
{
  "chart_type": "line_chart",
  "data_mapping": {
    "x_axis": "month",
    "y_axis": "value",
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
      "series_id": "competitor1",
      "group_value": "Competitor 1",
      "prominence": "baseline",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Competitor 1"
    },
    {
      "series_id": "competitor2",
      "group_value": "Competitor 2",
      "prominence": "baseline",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Competitor 2"
    }
  ]
}
```

**Rationale**: Hawk-in-pigeons principle. Push competitors to baseline so focus series stands out.

### Actual vs. Forecast

When showing historical data with projections:

```json
{
  "chart_type": "line_chart",
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
      "label": "Actual"
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

**Rationale**: Forecast uses `data-projection` purpose. The UI maps this to dotted line style and may add enclosure (light background) for forecast region.

### With Insight Highlight

When highlighting a specific point or trend:

```json
{
  "chart_type": "line_chart",
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
      "sentiment": "positive",
      "label": "Revenue"
    }
  ],
  "highlights": [
    {
      "id": "highlight_q3_peak",
      "insight_id": "insight_growth",
      "type": "point",
      "description": "Q3 Peak - $1.2M",
      "row_ids": ["r15"]
    }
  ]
}
```

## Gestalt Applications

### Connection

**Principle**: Connected elements are perceived as grouped.

**Line chart application**: This is why line charts work. The connecting line creates order and shows trend continuity. The line itself is the primary perceptual element.

**Refinement implication**: The connecting lines are essential—never hide them. Line weight and style carry meaning (solid for focus, dashed for comparison, dotted for projection).

### Continuity

**Principle**: The eye follows the smoothest path.

**Line chart application**: The y-axis line can often be removed. The consistent white space between value labels and the data creates implicit vertical alignment.

### Similarity

**Principle**: Similar elements are perceived as related.

**Line chart application**: All comparison series should share the same visual treatment. All actual data should look different from all forecast data.

**Refinement implication**: Ensure series with the same `purpose` classification receive consistent treatment. Don't mix dashed and solid lines within comparison data.

### Proximity

**Principle**: Elements close together are perceived as grouped.

**Line chart application**: Direct labels should be positioned at the end of their line (proximate to the data they describe).

## Common Structural Corrections

| Issue | Correction | Rationale |
|-------|------------|-----------|
| Diagonal x-axis labels | `horizontal` | 52% slower to read diagonal text |
| Center-aligned title | `left-aligned` | Clean visual edge, Z-pattern reading |
| Legend at bottom | `direct-labels` or `top-left` | Reduces eye travel |
| Data markers everywhere | Remove markers | Line itself communicates trend |
| Gridlines prominent | `hide` or `background` | Trends don't need precise reading |
| Y-axis line present | `hide` | Continuity principle |
| Multiple colors without meaning | Consistent neutral + one accent | Hawk-in-pigeons principle |

## Decluttering Checklist

- [ ] Primary series clearly identified?
- [ ] Comparison series pushed to baseline prominence?
- [ ] Forecast series using `data-projection` purpose?
- [ ] Sentiment aligned with business meaning?
- [ ] Labels provided for legend generation?
- [ ] Highlights linked to insights?

## Sentiment Assignment for Line Charts

| Scenario | Sentiment |
|----------|-----------|
| Revenue trending up | `positive` |
| Revenue trending down | `negative` |
| Costs trending up | `negative` |
| Costs trending down | `positive` |
| Comparison/benchmark line | `neutral` |
| Forecast line | `neutral` (unless tied to good/bad outcome) |
| Line approaching warning threshold | `warning` |

Remember: Sentiment is about business meaning, not just direction. "Costs down" is positive; "Revenue down" is negative.

## Multi-Series Strategies

### When all series are equally important
- All receive `prominence: "primary"`, `purpose: "data-focus"`
- Use distinct colors from categorical palette
- Direct labels at endpoints

### When one series is the focus
- Focus series: `prominence: "primary"`, `purpose: "data-focus"`
- Others: `prominence: "baseline"`, `purpose: "data-comparison"`
- All comparison series share same neutral color

### When showing actual vs. target
- Actual: `prominence: "primary"`, `purpose: "data-focus"`
- Target: `prominence: "baseline"`, `purpose: "reference"`

### When showing forecast
- Historical: `prominence: "primary"`, `purpose: "data-focus"`
- Forecast: `prominence: "secondary"`, `purpose: "data-projection"`
- Consider enclosure (light background) for forecast region

## Highlight Types for Line Charts

| Type | Use Case |
|------|----------|
| `point` | Single data point emphasis |
| `point_set` | Multiple related points |
| `band` | Time range (shaded region) |
| `threshold` | Horizontal reference line |
| `annotation` | Callout at specific point |

### Example

```json
{
  "highlights": [
    { "id": "h1", "insight_id": "i1", "type": "band", "description": "Growth period", "start": "2024-07", "end": "2024-09" },
    { "id": "h2", "insight_id": "i2", "type": "point", "description": "Peak revenue", "row_ids": ["r15"] }
  ]
}
```

## See Also

- [Refinement Interface](./refinement.md) — Full process and principles
- [Classification System](../02-classification-system.md) — Multi-axis reference
- [Agent-UI Handoff](../03-agent-ui-handoff.md) — Agent vs UI responsibilities
