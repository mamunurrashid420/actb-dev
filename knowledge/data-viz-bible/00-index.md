---
type: reference
category: index
tags: [index, navigation, overview, pipeline]
---

# Data Viz Bible

A comprehensive knowledge base for AI agents to select and refine chart specifications. The UI renders charts from these specifications using its own design system and style guide.

## The Visualization Pipeline

```
DataSchema + UserIntent
        │
        ▼
┌─────────────────┐
│   SELECTION     │  Determine which chart type best represents the data
└─────────────────┘
        │ ChartType + DataMapping
        ▼
┌─────────────────┐
│   REFINEMENT    │  Classify data series, generate highlights
└─────────────────┘
        │ ChartSpec (dataSeries + highlights)
        ▼
    UI Renders Chart
    (applies structuralConfig, elementClassifications, colors, fonts from style guide)
```

## Key Principle: Agent-UI Boundary

**The agent outputs semantic classifications for data series; the UI applies all structural config and visual styling.**

- **Agent outputs**: `chartType`, `dataMapping`, `dataSeries[]` (with prominence, purpose, sentiment), `highlights[]`
- **UI handles**: `structuralConfig`, `elementClassifications`, colors, fonts, sizes, stroke widths, lineStyle

See [Agent-UI Handoff](./03-agent-ui-handoff.md) for the full specification.

## Quick Start

1. **Understand your data** → [Schema Reference](./01-schema-reference.md)
2. **Select a chart** → [Selection](./selection/selection.md)
3. **Refine and output** → [Refinement](./refinement/refinement.md) (final agent output)

## Foundation Documents

| Document | Purpose |
|----------|---------|
| [01-schema-reference.md](./01-schema-reference.md) | Field roles (DIMENSION, MEASURE, TEMPORAL) and data pattern detection |
| [02-classification-system.md](./02-classification-system.md) | Multi-axis classification: Prominence × Purpose × Sentiment |
| [03-agent-ui-handoff.md](./03-agent-ui-handoff.md) | Agent vs UI responsibilities (styling, highlights, series IDs) |
| [99-contributing.md](./99-contributing.md) | How to add new chart types |

## Action Interfaces

Each action has an interface document defining the process, input/output contracts, and cross-cutting principles.

| Action | Interface | Purpose |
|--------|-----------|---------|
| Selection | [selection.md](./selection/selection.md) | Decision logic for chart type selection |
| Refinement | [refinement.md](./refinement/refinement.md) | Data series classification, highlights, final output |

## Chart Types

### P0 — Core (Always Available)

| Chart Type | Selection | Refinement |
|------------|-----------|------------|
| KPI Card | [selection](./selection/selection-kpi-card.md) | [refinement](./refinement/refinement-kpi-card.md) |
| Data Table | [selection](./selection/selection-data-table.md) | [refinement](./refinement/refinement-data-table.md) |
| Bar Chart (Vertical) | [selection](./selection/selection-bar-chart-vertical.md) | [refinement](./refinement/refinement-bar-chart-vertical.md) |
| Bar Chart (Horizontal) | [selection](./selection/selection-bar-chart-horizontal.md) | [refinement](./refinement/refinement-bar-chart-horizontal.md) |
| Line Chart | [selection](./selection/selection-line-chart.md) | [refinement](./refinement/refinement-line-chart.md) |
| Area Chart | [selection](./selection/selection-area-chart.md) | [refinement](./refinement/refinement-area-chart.md) |
| Scatter Plot | [selection](./selection/selection-scatter-plot.md) | [refinement](./refinement/refinement-scatter-plot.md) |
| Pie Chart | [selection](./selection/selection-pie-chart.md) | [refinement](./refinement/refinement-pie-chart.md) |
| Donut Chart | [selection](./selection/selection-donut-chart.md) | [refinement](./refinement/refinement-donut-chart.md) |

### P1 — Extended

| Chart Type | Selection | Refinement |
|------------|-----------|------------|
| Bar Chart (Stacked) | [selection](./selection/selection-bar-chart-stacked.md) | [refinement](./refinement/refinement-bar-chart-stacked.md) |
| Bar Chart (Grouped) | [selection](./selection/selection-bar-chart-grouped.md) | [refinement](./refinement/refinement-bar-chart-grouped.md) |
| Histogram | [selection](./selection/selection-histogram.md) | [refinement](./refinement/refinement-histogram.md) |
| Heatmap | [selection](./selection/selection-heatmap.md) | [refinement](./refinement/refinement-heatmap.md) |
| Treemap | [selection](./selection/selection-treemap.md) | [refinement](./refinement/refinement-treemap.md) |
| Boxplot | [selection](./selection/selection-boxplot.md) | [refinement](./refinement/refinement-boxplot.md) |
| Slope Chart | [selection](./selection/selection-slope-chart.md) | [refinement](./refinement/refinement-slope-chart.md) |

### P2 — Specialized

| Chart Type | Selection | Refinement |
|------------|-----------|------------|
| Waterfall Chart | [selection](./selection/selection-waterfall-chart.md) | [refinement](./refinement/refinement-waterfall-chart.md) |
| Combo Chart | [selection](./selection/selection-combo-chart.md) | [refinement](./refinement/refinement-combo-chart.md) |
| Bullet Chart | [selection](./selection/selection-bullet-chart.md) | — |
| Funnel Chart | [selection](./selection/selection-funnel-chart.md) | — |
| Bubble Chart | [selection](./selection/selection-bubble-chart.md) | — |
| Lollipop Chart | [selection](./selection/selection-lollipop-chart.md) | — |

## Worked Examples

End-to-end examples showing the complete pipeline:

| Example | Description |
|---------|-------------|
| [Sales Dashboard](./examples/example-01-sales-dashboard.md) | KPI + Line + Bar dashboard |
| [Product Comparison](./examples/example-02-product-comparison.md) | Scatter + Grouped Bar with sentiment |
| [Financial Bridge](./examples/example-03-financial-bridge.md) | Waterfall chart with narrative |
| [Trend with Insight](./examples/example-04-trend-with-insight.md) | Multi-series line with callout annotation |

## How to Use This Knowledge Base

### For Single-Agent Architecture

1. Read the Selection interface document to determine chart type
2. Read the Refinement interface document and chart-specific document
3. Output the chart specification with `dataSeries` and `highlights`

### For Multi-Agent Architecture

Each action can be handled by a specialized sub-agent:
- **Selection Agent**: Reads `selection.md` + `selection-<chart>.md`
- **Refinement Agent**: Reads `refinement.md` + `refinement-<chart>.md` (outputs final chart spec)

### UI Rendering

The UI receives the chart specification and:
1. Applies `structuralConfig` defaults for the chart type (showDots, showLegend, etc.)
2. Applies `elementClassifications` defaults (axes, gridlines, borders - consistent across all charts)
3. Derives `lineStyle` from `purpose` (data-focus → solid, data-comparison → dashed, data-projection → dotted)
4. Maps `prominence` to visual weight (opacity, stroke width)
5. Maps `sentiment` to colors from its design system
6. Renders using whatever library it prefers (D3, Recharts, etc.)
