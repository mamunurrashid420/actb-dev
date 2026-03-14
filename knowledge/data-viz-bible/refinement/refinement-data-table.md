---
type: action-implementation
action: refinement
chart-type: data_table
tags: [refinement, table, classification, tabular, data-series]
---

# Refinement: Data Table

Refinement guidance for data tables showing detailed tabular information.

> **Key Principle**: The agent outputs `data_series` with semantic classifications (prominence, purpose, sentiment). The UI handles structural elements (borders, alignment, formatting) via its style guide.

## Sample Data

```json
[
  { "product": "Widget A", "region": "North", "sales": 45000, "profit": 12500, "growth": 15.2 },
  { "product": "Widget B", "region": "North", "sales": 32000, "profit": -2100, "growth": -5.8 },
  { "product": "Widget C", "region": "South", "sales": 58000, "profit": 18200, "growth": 22.4 },
  { "product": "Widget D", "region": "South", "sales": 27000, "profit": 4300, "growth": 3.1 }
]
```

## DataMapping Configuration

For data tables, typically no explicit mapping is needed—all columns are displayed:

```json
{
  "data_mapping": {}
}
```

For tables with grouped/highlighted rows:

```json
{
  "data_mapping": {
    "group_by": "region"
  }
}
```

| Field | Purpose |
|-------|---------|
| `group_by` | Field to group rows (optional) |

## Element Inventory

| Element | Handled By | Notes |
|---------|------------|-------|
| Row background | UI (from `sentiment`) | Highlight specific rows |
| Cell colors | UI (from column `sentiment`) | For value-based coloring |
| Table border | UI style guide | Minimal or none |
| Header row | UI style guide | Primary prominence |
| Row dividers | UI style guide | Background prominence |
| Column alignment | UI style guide | Right for numbers, left for text |
| Title | UI style guide | Primary prominence |

## DataSeries Patterns

For tables, `data_series` typically classifies **columns** rather than rows:

### Basic Table (All Columns Equal)

When displaying data without emphasis:

```json
{
  "chart_type": "data_table",
  "data_mapping": {},
  "data_series": [
    {
      "series_id": "product",
      "field": "product",
      "prominence": "primary",
      "purpose": "navigational",
      "sentiment": "neutral",
      "label": "Product"
    },
    {
      "series_id": "sales",
      "field": "sales",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Sales ($)"
    },
    {
      "series_id": "profit",
      "field": "profit",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Profit ($)"
    },
    {
      "series_id": "growth",
      "field": "growth",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Growth (%)"
    }
  ]
}
```

### With Column-Level Sentiment (Conditional Formatting)

When values in a column have evaluative meaning:

```json
{
  "chart_type": "data_table",
  "data_mapping": {},
  "data_series": [
    {
      "series_id": "product",
      "field": "product",
      "prominence": "primary",
      "purpose": "navigational",
      "sentiment": "neutral",
      "label": "Product"
    },
    {
      "series_id": "profit_positive",
      "field": "profit",
      "value_range": { "min": 0, "max": null },
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "Profit"
    },
    {
      "series_id": "profit_negative",
      "field": "profit",
      "value_range": { "min": null, "max": 0 },
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "negative",
      "label": "Profit"
    },
    {
      "series_id": "growth",
      "field": "growth",
      "prominence": "secondary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Growth (%)"
    }
  ]
}
```

**How the UI renders this**:
- Profit values ≥ 0 → green (positive sentiment)
- Profit values < 0 → red (negative sentiment)

### With Row Highlights

When specific rows need emphasis:

```json
{
  "chart_type": "data_table",
  "data_mapping": {},
  "data_series": [
    {
      "series_id": "all_columns",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral"
    }
  ],
  "highlights": [
    {
      "id": "top_performer",
      "type": "points",
      "description": "Top Performer",
      "field_filters": [
        { "field": "product", "values": ["Widget C"] }
      ],
      "prominence": "callout",
      "sentiment": "positive"
    },
    {
      "id": "loss_maker",
      "type": "points",
      "description": "Needs Attention",
      "field_filters": [
        { "field": "product", "values": ["Widget B"] }
      ],
      "prominence": "primary",
      "sentiment": "negative"
    }
  ]
}
```

### Focus Column Pattern

When one column is the primary focus:

```json
{
  "chart_type": "data_table",
  "data_mapping": {},
  "data_series": [
    {
      "series_id": "product",
      "field": "product",
      "prominence": "primary",
      "purpose": "navigational",
      "sentiment": "neutral",
      "label": "Product"
    },
    {
      "series_id": "profit",
      "field": "profit",
      "prominence": "callout",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Profit ($)"
    },
    {
      "series_id": "sales",
      "field": "sales",
      "prominence": "secondary",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Sales ($)"
    },
    {
      "series_id": "growth",
      "field": "growth",
      "prominence": "secondary",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Growth (%)"
    }
  ]
}
```

## Gestalt Applications

### Proximity

**Principle**: Elements close together are perceived as grouped.

**Table application**: 
- Row spacing groups data horizontally
- Column headers close to data below
- Consistent cell padding creates rhythm

### Similarity

**Principle**: Similar elements are perceived as related.

**Table application**:
- Consistent text styling within columns
- Similar numeric formatting (all currency, all percentages)
- Alternating row colors can aid scanning

### Continuity

**Principle**: The eye follows the smoothest path.

**Table application**:
- Horizontal lines guide the eye across rows
- Consistent alignment creates vertical columns
- Avoid breaking visual flow

## Common Structural Corrections

| Issue | Correction | Rationale |
|-------|------------|-----------|
| Numbers left-aligned | Right-align numbers | Digits align for comparison |
| Too many columns | Reduce to essentials | More than 8 columns hard to scan |
| Heavy borders | Minimize or remove | Borders add clutter |
| Inconsistent formatting | Standardize | Same format per column |

## Decluttering Checklist

- [ ] Columns classified with appropriate `field` names?
- [ ] `value_range` used for conditional formatting?
- [ ] Row highlights via `highlights` array (not per-row series)?
- [ ] Focus column at `callout` prominence?
- [ ] Labels provided for column headers?

## Number Formatting Guidelines

| Data Type | Format | Alignment |
|-----------|--------|-----------|
| Currency | $1,234.56 | Right |
| Percentage | 45.2% | Right |
| Integer | 1,234 | Right |
| Decimal | 1,234.56 | Right |
| Date | Jan 15, 2024 | Left |
| Text | As-is | Left |

**Note**: The UI applies formatting based on column data type; the agent focuses on semantic classification.

## See Also

- [Refinement Interface](./refinement.md)
- [Agent-UI Handoff](../03-agent-ui-handoff.md) — Agent vs UI responsibilities
