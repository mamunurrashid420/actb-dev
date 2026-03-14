---
type: action-implementation
action: refinement
chart-type: histogram
tags: [refinement, histogram, classification, distribution, data-series, value-range]
---

# Refinement: Histogram

Refinement guidance for histograms showing data distribution.

> **Key Principle**: The agent outputs `data_series` with semantic classifications (prominence, purpose, sentiment). The UI handles structural elements (axes, gridlines, borders) via its style guide.

## Sample Data

```json
[
  { "response_time_ms": 45 },
  { "response_time_ms": 52 },
  { "response_time_ms": 48 },
  { "response_time_ms": 120 },
  { "response_time_ms": 85 },
  { "response_time_ms": 67 },
  { "response_time_ms": 250 },
  { "response_time_ms": 43 }
]
```

## DataMapping Configuration

For histograms, use the `value` field:

```json
{
  "data_mapping": {
    "value": "response_time_ms"
  }
}
```

| Field | Purpose |
|-------|---------|
| `value` | The numeric field to bin and count |

**Note**: The UI determines bin count and ranges automatically based on the data.

## DataSeries Patterns

Histograms support two approaches similar to heatmaps:

### Pattern 1: Default Distribution (80% of cases)

Single classification when exploring distribution without semantic thresholds:

```json
{
  "chart_type": "histogram",
  "data_mapping": {
    "value": "response_time_ms"
  },
  "data_series": [
    {
      "series_id": "distribution",
      "field": "response_time_ms",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Response Time Distribution"
    }
  ]
}
```

The UI renders all bins with the same styling, letting users interpret the distribution.

### Pattern 2: Semantic Value Ranges (When thresholds matter)

Use multiple `data_series` with `value_range` when the agent needs to express business meaning:

```json
{
  "chart_type": "histogram",
  "data_mapping": {
    "value": "response_time_ms"
  },
  "data_series": [
    {
      "series_id": "fast",
      "field": "response_time_ms",
      "value_range": { "min": 0, "max": 50 },
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "Fast (< 50ms)"
    },
    {
      "series_id": "acceptable",
      "field": "response_time_ms",
      "value_range": { "min": 50, "max": 100 },
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Acceptable (50-100ms)"
    },
    {
      "series_id": "slow",
      "field": "response_time_ms",
      "value_range": { "min": 100, "max": null },
      "prominence": "callout",
      "purpose": "data-focus",
      "sentiment": "negative",
      "label": "Slow (> 100ms)"
    }
  ]
}
```

**How the UI renders this**:
- Each bin is colored based on where its range falls
- Bins 0-50ms → green (positive sentiment)
- Bins 50-100ms → neutral
- Bins 100ms+ → red (negative sentiment) with callout emphasis

### Pattern 3: With Reference Line (Mean/Median)

Highlight central tendency with highlights:

```json
{
  "chart_type": "histogram",
  "data_mapping": {
    "value": "response_time_ms"
  },
  "data_series": [
    {
      "series_id": "distribution",
      "field": "response_time_ms",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Distribution"
    }
  ],
  "highlights": [
    {
      "id": "median_line",
      "type": "threshold",
      "description": "Median response time",
      "threshold_value": 65,
      "sentiment": "neutral"
    }
  ]
}
```

### When to Use Each Pattern

| Scenario | Pattern | Rationale |
|----------|---------|-----------|
| General exploration | Default distribution | Let users interpret |
| SLA monitoring | Semantic value ranges | Show which responses breach SLA |
| Outlier detection | Semantic value ranges | Highlight abnormal values |
| Comparing to average | With reference line | Show central tendency |

## Element Inventory

| Element | Handled By | Notes |
|---------|------------|-------|
| Bin colors | Agent (via `value_range` sentiment) or UI (uniform) | Based on pattern |
| Bin opacity | UI (from `prominence`) | Callout > primary > secondary |
| X-axis | UI style guide | Shows bin ranges |
| Y-axis | UI style guide | Frequency/count |
| Gridlines | UI style guide | Helps read frequencies |
| Reference lines | Agent (via `highlights`) | Mean, median, threshold |
| Title | UI style guide | Primary prominence |

## Gestalt Applications

### Proximity
Bars touch because they represent continuous ranges. No gaps between bins reinforces continuity.

### Similarity
All bars same color unless using semantic value ranges to highlight specific ranges (e.g., "values above threshold").

### Enclosure
Can shade a range of bins to highlight using the `value_range` pattern.

## Common Structural Corrections

| Issue | Correction | Rationale |
|-------|------------|-----------|
| Gaps between bars | Remove gaps | Histogram bars should touch |
| Too few bins | Increase bin count | Hides distribution shape |
| Too many bins | Reduce bin count | Creates noisy pattern |
| Y-axis not at zero | Start at zero | Bar length must be proportional |

## Bin Count Guidelines

| Data Points | Suggested Bins |
|-------------|----------------|
| < 50 | 5-7 bins |
| 50-200 | 8-12 bins |
| 200-1000 | 12-20 bins |
| > 1000 | 20-30 bins |

**Note**: The UI handles bin calculation; the agent focuses on semantic classification.

## Decluttering Checklist

- [ ] Single value field correctly mapped?
- [ ] Semantic thresholds reflect business meaning (if used)?
- [ ] Reference lines meaningful (mean, median, SLA)?
- [ ] Labels clear for value ranges?
- [ ] Distribution story communicated through classification?

## See Also

- [Refinement Interface](./refinement.md)
- [Agent-UI Handoff](../03-agent-ui-handoff.md) — Agent vs UI responsibilities
