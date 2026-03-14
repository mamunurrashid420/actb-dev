---
type: reference
category: architecture
tags: [agent-ui, handoff, boundary, responsibilities, style-guide]
---

# Agent-UI Handoff

This document defines the boundary between what the agent outputs and what the UI handles. This separation ensures:

1. **Agent portability**: Agent output works with any UI/design system
2. **Design system control**: UI owns all visual decisions
3. **Simplified agent logic**: Agent focuses on semantic meaning, not presentation

## The Boundary

```
┌─────────────────────────────────────────────────────────────────┐
│                        AGENT OUTPUTS                            │
├─────────────────────────────────────────────────────────────────┤
│  chartType          │  "line", "bar_vertical", "pie", etc.      │
│  dataMapping        │  xAxis, yAxis, groupBy, value, row,       │
│                     │  column                                   │
│  dataSeries[]       │  seriesId, field, groupValue, valueRange, │
│                     │  prominence, purpose, sentiment, label    │
│  highlights[]       │  id, insight_id, type, description, etc.  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        UI HANDLES                               │
├─────────────────────────────────────────────────────────────────┤
│  structuralConfig   │  showDots, showLegend, showGridlines,     │
│                     │  labelPosition, titleAlignment, curve,    │
│                     │  barPadding, innerRadius, etc.            │
│  elementClassif.    │  Axes, gridlines, borders, titles         │
│                     │  (consistent across all charts)           │
│  lineStyle          │  Derived from purpose                     │
│  colors             │  Derived from sentiment + design system   │
│  fonts, sizes       │  From design system                       │
│  stroke widths      │  Derived from prominence                  │
│  accessibility      │  Component implementation                 │
└─────────────────────────────────────────────────────────────────┘
```

## Agent Output Schema

The agent outputs a chart specification with semantic classifications:

```json
{
  "chartType": "line_chart",
  "dataMapping": {
    "xAxis": "month",
    "yAxis": "value",
    "groupBy": "metric_type"
  },
  "dataSeries": [
    {
      "seriesId": "revenue",
      "groupValue": "Revenue",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "Revenue"
    },
    {
      "seriesId": "costs",
      "groupValue": "Costs",
      "prominence": "secondary",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Costs"
    }
  ],
  "highlights": [
    {
      "id": "highlight_growth",
      "insight_id": "insight_q3",
      "type": "band",
      "description": "Q3 Growth Period",
      "start": "2024-07",
      "end": "2024-09"
    }
  ]
}
```

### DataMapping Fields

| Field | Purpose | Example |
|-------|---------|---------|
| `xAxis` | Field for X-axis | `"month"`, `"date"` |
| `yAxis` | Field for Y-axis | `"revenue"`, `"value"` |
| `groupBy` | Field to group by for creating series | `"product"`, `"category"` |
| `value` | Primary value field (KPI, pie, treemap) | `"amount"`, `"share"` |
| `row` | Field for grid rows (heatmaps) | `"day"` |
| `column` | Field for grid columns (heatmaps) | `"hour"` |

### DataSeries Identification

Three ways to identify which data points belong to a series:

| Field | Use Case | Example |
|-------|----------|---------|
| `field` | Wide-format data (column name) | `"revenue"`, `"costs"` |
| `groupValue` | Long-format data (value in groupBy field) | `"Product A"`, `"Online"` |
| `valueRange` | Value-based styling (heatmaps, gauges) | `{ "min": 80, "max": Infinity }` |

## Classification Values

### Prominence (visual weight)

| Value | Meaning | UI Treatment |
|-------|---------|--------------|
| `hide` | Remove entirely | `display: none` |
| `background` | Barely visible | Low opacity (~0.3) |
| `baseline` | Present but passive | Medium opacity (~0.6) |
| `secondary` | Visible but subordinate | Higher opacity (~0.8) |
| `primary` | Main focus | Full opacity, heavier weight |
| `callout` | Maximum prominence | Full opacity, heaviest weight, decorations |

### Purpose (functional role)

| Value | Meaning | UI Treatment |
|-------|---------|--------------|
| `data-focus` | Primary data being analyzed | Solid lines/fills |
| `data-comparison` | Comparison/benchmark data | Dashed lines |
| `data-projection` | Forecast/projection data | Dotted lines |

### Sentiment (evaluative meaning)

| Value | Meaning | UI Treatment |
|-------|---------|--------------|
| `positive` | Good outcome | Success color (green) |
| `negative` | Bad outcome | Danger color (red) |
| `neutral` | No evaluation | Neutral color (gray/blue) |
| `warning` | Attention needed | Warning color (amber) |

## What the Agent Does NOT Output

The agent never outputs:

| Property | Why | Who Handles |
|----------|-----|-------------|
| Hex colors (`#22c55e`) | Visual styling | UI design system |
| RGB colors | Visual styling | UI design system |
| Font sizes (`18px`) | Visual styling | UI typography scale |
| Font families | Visual styling | UI typography |
| Stroke widths (`2.5px`) | Visual styling | UI derives from prominence |
| CSS classes | Framework-specific | UI implementation |
| `lineStyle` | Visual styling | UI derives from purpose |
| `structuralConfig` | Presentation | UI defaults per chart type |
| `elementClassifications` | Presentation | UI style guide (consistent) |
| `accessibilityHints` | Presentation | UI accessibility system |

## UI Responsibilities

### 1. Structural Configuration

The UI applies default structural configuration per chart type:

```typescript
const STRUCTURAL_DEFAULTS = {
  line: {
    showDots: false,
    showLegend: false,
    showGridlines: false,
    labelPosition: "direct",
    curve: "monotone",
  },
  bar_vertical: {
    barPadding: 0.2,
    showGridlines: false,
    showValues: false,
  },
  // ... etc
};
```

### 2. Element Classifications

The UI applies consistent element classifications across all charts:

```typescript
const ELEMENT_DEFAULTS = {
  chartBorder: { prominence: "hide", purpose: "structural" },
  gridlines: { prominence: "hide", purpose: "structural" },
  xAxisLine: { prominence: "baseline", purpose: "structural" },
  yAxisLine: { prominence: "hide", purpose: "structural" },
  xAxisLabels: { prominence: "baseline", purpose: "navigational" },
  yAxisLabels: { prominence: "baseline", purpose: "navigational" },
  title: { prominence: "primary", purpose: "navigational" },
  legend: { prominence: "hide", purpose: "navigational" },
};
```

### 3. Line Style Derivation

The UI derives line style from the agent's `purpose` classification:

```typescript
function getLineStyle(purpose: Purpose): "solid" | "dashed" | "dotted" {
  switch (purpose) {
    case "data-focus": return "solid";
    case "data-comparison": return "dashed";
    case "data-projection": return "dotted";
  }
}
```

### 4. Semantic CSS

The UI maps classifications to visual styles via CSS:

```css
/* Prominence → Visual Weight */
[data-prominence="hide"] { display: none; }
[data-prominence="background"] { opacity: 0.3; }
[data-prominence="baseline"] { opacity: 0.6; }
[data-prominence="secondary"] { opacity: 0.8; }
[data-prominence="primary"] { opacity: 1.0; }

/* Purpose → Line Style */
[data-purpose="data-focus"] { stroke-dasharray: none; }
[data-purpose="data-comparison"] { stroke-dasharray: 4 2; }
[data-purpose="data-projection"] { stroke-dasharray: 2 2; }

/* Sentiment → Color */
[data-sentiment="positive"] { --series-color: var(--color-success); }
[data-sentiment="negative"] { --series-color: var(--color-danger); }
[data-sentiment="neutral"] { --series-color: var(--color-neutral); }
[data-sentiment="warning"] { --series-color: var(--color-warning); }
```

## Why This Separation?

### Agent Benefits

1. **Simpler output**: Agent doesn't need to know colors, fonts, or layout details
2. **Portable**: Same agent output works with any design system
3. **Focused**: Agent concentrates on semantic meaning (what data means)

### UI Benefits

1. **Design control**: All visual decisions in one place
2. **Consistency**: Structural elements look the same across all charts
3. **Themeable**: Can change appearance without changing agent
4. **Accessible**: Can implement accessibility at the component level

## Example: Revenue vs Costs Line Chart

### Agent Output

```json
{
  "chartType": "line_chart",
  "dataMapping": { "xAxis": "month" },
  "dataSeries": [
    { "seriesId": "revenue", "field": "revenue", "prominence": "primary", "purpose": "data-focus", "sentiment": "positive", "label": "Revenue" },
    { "seriesId": "costs", "field": "costs", "prominence": "secondary", "purpose": "data-comparison", "sentiment": "neutral", "label": "Costs" }
  ],
  "highlights": []
}
```

### UI Applies

1. **structuralConfig** for line chart: `showDots: false`, `curve: "monotone"`, etc.
2. **elementClassifications**: Hides chart border, gridlines, y-axis line
3. **lineStyle**: Revenue gets solid line (data-focus), costs gets dashed line (data-comparison)
4. **colors**: Revenue gets green (positive sentiment), costs gets gray (neutral sentiment)
5. **stroke width**: Revenue gets heavier stroke (primary), costs gets lighter (secondary)

## Example: Heatmap with Value-Based Styling

### Agent Output (Semantic Control)

```json
{
  "chartType": "heatmap",
  "dataMapping": {
    "row": "day",
    "column": "hour",
    "value": "activity"
  },
  "dataSeries": [
    {
      "seriesId": "critical-high",
      "field": "activity",
      "valueRange": { "min": 80, "max": null },
      "prominence": "callout",
      "sentiment": "negative",
      "label": "Overload"
    },
    {
      "seriesId": "optimal",
      "field": "activity",
      "valueRange": { "min": 50, "max": 80 },
      "prominence": "primary",
      "sentiment": "positive",
      "label": "Healthy"
    },
    {
      "seriesId": "low",
      "field": "activity",
      "valueRange": { "min": 0, "max": 50 },
      "prominence": "secondary",
      "sentiment": "warning",
      "label": "Underutilized"
    }
  ]
}
```

### UI Applies

Each cell finds its classification by value match:
- `activity = 85` → matches "critical-high" → red color + callout styling
- `activity = 65` → matches "optimal" → green color + primary styling
- `activity = 30` → matches "low" → amber color + secondary styling

## See Also

- [Classification System](./02-classification-system.md) — Full classification reference
- [Refinement Interface](./refinement/refinement.md) — Agent output specification
