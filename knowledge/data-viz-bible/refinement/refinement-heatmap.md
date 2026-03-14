---
type: action-implementation
action: refinement
chart-type: heatmap
tags: [refinement, heatmap, classification, matrix, data-series, value-range]
---

# Refinement: Heatmap

Refinement guidance for heatmaps with semantic value-range styling.

> **Key Principle**: The agent outputs `data_series` with semantic classifications (prominence, purpose, sentiment). The UI handles structural elements (axes, gridlines, borders) via its style guide.

## Sample Data

```json
[
  { "day": "Monday", "hour": "9AM", "activity": 85 },
  { "day": "Monday", "hour": "10AM", "activity": 72 },
  { "day": "Monday", "hour": "11AM", "activity": 45 },
  { "day": "Tuesday", "hour": "9AM", "activity": 62 },
  { "day": "Tuesday", "hour": "10AM", "activity": 88 },
  { "day": "Tuesday", "hour": "11AM", "activity": 34 }
]
```

## DataMapping Configuration

For heatmaps, use `column`, `row`, and `value` fields:

```json
{
  "data_mapping": {
    "column": "hour",
    "row": "day",
    "value": "activity"
  }
}
```

| Field | Purpose |
|-------|---------|
| `column` | Field for X-axis (columns) |
| `row` | Field for Y-axis (rows) |
| `value` | Field containing the numeric value for color encoding |

## DataSeries Patterns

Heatmaps support two patterns for semantic styling:

### Pattern 1: Default Auto-Scaling (80% of cases)

Use a single `data_series` classification when the UI should automatically apply a color scale:

```json
{
  "chart_type": "heatmap",
  "data_mapping": {
    "column": "hour",
    "row": "day",
    "value": "activity"
  },
  "data_series": [
    {
      "series_id": "activity-grid",
      "field": "activity",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Activity Level"
    }
  ]
}
```

The UI automatically maps values to colors using a sequential scale (e.g., low=light, high=dark).

### Pattern 2: Semantic Value Ranges (When meaning matters)

Use multiple `data_series` with `value_range` when the agent needs to express semantic meaning about value thresholds:

```json
{
  "chart_type": "heatmap",
  "data_mapping": {
    "column": "hour",
    "row": "day",
    "value": "activity"
  },
  "data_series": [
    {
      "series_id": "critical-high",
      "field": "activity",
      "value_range": { "min": 80, "max": null },
      "prominence": "callout",
      "purpose": "data-focus",
      "sentiment": "negative",
      "label": "Overload"
    },
    {
      "series_id": "optimal",
      "field": "activity",
      "value_range": { "min": 50, "max": 80 },
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "Healthy Load"
    },
    {
      "series_id": "low",
      "field": "activity",
      "value_range": { "min": 0, "max": 50 },
      "prominence": "secondary",
      "purpose": "data-focus",
      "sentiment": "warning",
      "label": "Underutilized"
    }
  ]
}
```

**How the UI renders this**:
- Each cell finds its classification by matching its value to a `value_range`
- `cell.value = 85` → matches "critical-high" → gets negative sentiment color (red) + callout styling
- `cell.value = 65` → matches "optimal" → gets positive sentiment color (green) + primary styling
- `cell.value = 30` → matches "low" → gets warning sentiment color (amber) + secondary styling

### When to Use Each Pattern

| Scenario | Pattern | Rationale |
|----------|---------|-----------|
| General exploration | Default auto-scaling | Let users interpret values themselves |
| "High is bad" (server load, errors) | Semantic value ranges | Express that exceeding threshold is negative |
| "High is good" (sales, engagement) | Semantic value ranges | Express that high values are positive |
| Traffic-light status | Semantic value ranges | Red/yellow/green meaning is business-defined |

## Key Refinement Decisions

### 1. Choosing the Right Color Semantics

The agent must determine if values have inherent meaning:

| Data Type | Semantic Choice |
|-----------|-----------------|
| Server CPU load | High = negative (overload risk) |
| Sales performance | High = positive (good performance) |
| Temperature | Depends on context (could be warning either way) |
| Correlation coefficients | Diverging (negative vs positive) |

### 2. Defining Value Thresholds

When using semantic value ranges, thresholds should reflect business meaning:

```json
// Good: Business-meaningful thresholds
{ "value_range": { "min": 80, "max": null }, "sentiment": "negative" }  // Above 80% is overload

// Bad: Arbitrary percentile splits
{ "value_range": { "min": 66, "max": 100 } }  // Why 66? No business meaning
```

### 3. Handling Null/Missing Values

Use a separate classification for missing data:

```json
{
  "series_id": "no-data",
  "field": "activity",
  "value_range": { "min": null, "max": null },
  "prominence": "background",
  "purpose": "structural",
  "sentiment": "neutral",
  "label": "No Data"
}
```

## Element Inventory

| Element | Handled By | Notes |
|---------|------------|-------|
| Cell colors | Agent (via `data_series` sentiment) or UI (auto-scale) | Based on pattern choice |
| Cell borders | UI style guide | Subtle borders for cell distinction |
| Column labels | UI style guide | Baseline prominence |
| Row labels | UI style guide | Baseline prominence |
| Color legend | UI style guide | Required, auto-generated |
| Cell value text | UI style guide | Optional overlay |
| Title | UI style guide | Primary prominence |

## Gestalt Applications

### Proximity
Adjacent cells are perceived as related. Rows and columns create natural groupings without needing explicit borders.

### Similarity
Cells with similar colors are perceived as having similar values—this is the core mechanism of heatmap interpretation. Semantic coloring reinforces this by making business meaning visible.

### Enclosure
For correlation matrices or specific regions, subtle borders can highlight areas of interest.

## Common Structural Corrections

| Issue | Correction | Rationale |
|-------|------------|-----------|
| Missing color legend | Add legend | Essential for interpretation |
| Wrong color semantics | Align with business meaning | High load ≠ high sales |
| No value thresholds | Define business-meaningful ranges | Makes data actionable |
| Too many cells | Aggregate or cluster | Pattern becomes noise |
| Red-green scale | Use colorblind-safe palette | Accessibility |

## Decluttering Checklist

- [ ] Value thresholds reflect business meaning?
- [ ] Sentiment correctly expresses "high is good/bad"?
- [ ] Color legend will be auto-generated?
- [ ] Labels are readable (not too many rows/columns)?
- [ ] Missing values handled explicitly?

## See Also

- [Refinement Interface](./refinement.md)
- [Agent-UI Handoff](../03-agent-ui-handoff.md) — Agent vs UI responsibilities
