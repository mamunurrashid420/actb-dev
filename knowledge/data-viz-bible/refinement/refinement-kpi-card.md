---
type: action-implementation
action: refinement
chart-type: kpi_card
tags: [refinement, kpi, classification, metrics, summary, data-series]
---

# Refinement: KPI Card

Refinement guidance for KPI cards, focusing on hierarchy and sentiment clarity.

> **Key Principle**: The agent outputs `data_series` with semantic classifications (prominence, purpose, sentiment). The UI handles structural elements (layout, typography, icons) via its style guide.

## Sample Data

```json
{
  "metric_name": "Monthly Revenue",
  "current_value": 1250000,
  "previous_value": 1150000,
  "target_value": 1200000,
  "unit": "$"
}
```

## DataMapping Configuration

For KPI cards, use the `value` field:

```json
{
  "data_mapping": {
    "value": "current_value"
  }
}
```

| Field | Purpose |
|-------|---------|
| `value` | The primary metric field |

## Element Inventory

| Element | Handled By | Notes |
|---------|------------|-------|
| Value color | UI (from `sentiment`) | Green/red/neutral |
| Value size | UI style guide | Callout = largest |
| Label | UI style guide | Metric name |
| Delta | UI (from `sentiment` on delta series) | Change indicator |
| Delta icon | UI style guide | Arrow up/down |
| Unit | UI style guide | Currency, %, etc. |
| Sparkline | Agent (optional data_series) | Mini trend |
| Target indicator | Agent (via highlights) | Goal reference |
| Card border | UI style guide | Minimal |

## DataSeries Patterns

### Basic KPI (Value Only)

When showing a single metric without comparison:

```json
{
  "chart_type": "kpi_card",
  "data_mapping": {
    "value": "current_value"
  },
  "data_series": [
    {
      "series_id": "revenue",
      "field": "current_value",
      "prominence": "callout",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Monthly Revenue"
    }
  ]
}
```

### KPI with Positive Delta

When showing growth:

```json
{
  "chart_type": "kpi_card",
  "data_mapping": {
    "value": "current_value"
  },
  "data_series": [
    {
      "series_id": "revenue",
      "field": "current_value",
      "prominence": "callout",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "Monthly Revenue"
    },
    {
      "series_id": "delta",
      "field": "delta_value",
      "prominence": "secondary",
      "purpose": "annotation",
      "sentiment": "positive",
      "label": "+8.7% vs last month"
    }
  ]
}
```

### KPI with Negative Delta

When showing decline:

```json
{
  "chart_type": "kpi_card",
  "data_mapping": {
    "value": "current_value"
  },
  "data_series": [
    {
      "series_id": "revenue",
      "field": "current_value",
      "prominence": "callout",
      "purpose": "data-focus",
      "sentiment": "negative",
      "label": "Monthly Revenue"
    },
    {
      "series_id": "delta",
      "field": "delta_value",
      "prominence": "secondary",
      "purpose": "annotation",
      "sentiment": "negative",
      "label": "-5.2% vs last month"
    }
  ]
}
```

### KPI with Warning (Near Threshold)

When approaching a critical threshold:

```json
{
  "chart_type": "kpi_card",
  "data_mapping": {
    "value": "current_value"
  },
  "data_series": [
    {
      "series_id": "metric",
      "field": "current_value",
      "prominence": "callout",
      "purpose": "data-focus",
      "sentiment": "warning",
      "label": "Server Load"
    }
  ],
  "highlights": [
    {
      "id": "threshold",
      "type": "threshold",
      "description": "Critical threshold",
      "threshold_value": 85,
      "sentiment": "negative"
    }
  ]
}
```

### KPI with Target Reference

When comparing to a goal:

```json
{
  "chart_type": "kpi_card",
  "data_mapping": {
    "value": "current_value"
  },
  "data_series": [
    {
      "series_id": "revenue",
      "field": "current_value",
      "prominence": "callout",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "Monthly Revenue"
    }
  ],
  "highlights": [
    {
      "id": "target",
      "type": "reference",
      "description": "Monthly Target",
      "threshold_value": 1200000,
      "sentiment": "neutral"
    }
  ]
}
```

### KPI with Sparkline

When showing trend context:

```json
{
  "chart_type": "kpi_card",
  "data_mapping": {
    "value": "current_value"
  },
  "data_series": [
    {
      "series_id": "revenue",
      "field": "current_value",
      "prominence": "callout",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "Monthly Revenue"
    },
    {
      "series_id": "trend",
      "field": "historical_values",
      "prominence": "secondary",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "12-month trend"
    }
  ]
}
```

## Gestalt Applications

### Proximity

**Principle**: Elements close together are perceived as grouped.

**KPI application**:
- Value and label should be close together
- Delta should be near the value it modifies
- Unit should be adjacent to value (not separated)

### Hierarchy

**Principle**: Size and weight create importance hierarchy.

**KPI application**:
- Value is largest element (callout prominence)
- Label is smaller but readable
- Delta is smaller still
- Clear visual hierarchy: Value > Label > Delta > Context

## Common Structural Corrections

| Issue | Correction | Rationale |
|-------|------------|-----------|
| Value not prominent enough | Use `callout` prominence | Value is the point of the card |
| Delta unclear sentiment | Sentiment determines color + icon | Good/bad should be obvious |
| Too much decoration | Simplify card chrome | Focus on the number |
| Missing context | Add delta or comparison | Number alone lacks meaning |

## Decluttering Checklist

- [ ] Primary value uses `callout` prominence?
- [ ] Delta has explicit sentiment (positive/negative)?
- [ ] Label clearly describes the metric?
- [ ] Target/threshold expressed via `highlights`?
- [ ] Sparkline (if any) at `secondary` prominence?

## Sentiment Assignment

| Scenario | Sentiment |
|----------|-----------|
| Revenue up | `positive` |
| Revenue down | `negative` |
| Costs up | `negative` |
| Costs down | `positive` |
| On track to target | `neutral` or `positive` |
| Behind target | `warning` or `negative` |
| At-risk threshold | `warning` |

**Key**: Sentiment depends on business meaning, not just direction.

## See Also

- [Refinement Interface](./refinement.md) — Full process
- [Classification System](../02-classification-system.md) — Classification reference
- [Agent-UI Handoff](../03-agent-ui-handoff.md) — Agent vs UI responsibilities
