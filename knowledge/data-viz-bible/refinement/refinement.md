---
type: action-interface
action: refinement
tags: [refinement, classification, gestalt, hierarchy, declutter, cognitive-load, data-ink-ratio, final-output]
---

# Refinement

The Refinement action is the **final agent step** that outputs the complete chart specification with semantic classifications for data series and highlights. This is where design principles are applied to transform a basic chart into an effective visual communication.

> **Key Principle**: The agent outputs semantic classifications for **data series only**. The UI handles all structural element styling (axes, gridlines, borders) via its style guide.

## Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `chart_type` | String | Yes | Chart type ID from Selection |
| `data_mapping` | Object | Yes | How schema fields map to chart dimensions |
| `user_intent` | String | Yes | Original user intent |
| `insights` | Array | No | Key insights to highlight |
| `data_schema` | Object | Yes | Schema of available data fields |

### Input Example

```json
{
  "chart_type": "line_chart",
  "data_mapping": {
    "x_axis": "month",
    "y_axis": "value",
    "group_by": "metric_type"
  },
  "user_intent": "Show that revenue is outpacing costs",
  "insights": [
    {
      "id": "insight_growth",
      "summary": "Revenue grew 23% while costs only increased 8%",
      "type": "positive"
    }
  ],
  "data_schema": {
    "fields": [
      { "name": "month", "role": "TEMPORAL" },
      { "name": "revenue", "role": "MEASURE" },
      { "name": "costs", "role": "MEASURE" }
    ]
  }
}
```

## Output

The Refinement step outputs the final chart specification that the UI will render.

| Field | Type | Description |
|-------|------|-------------|
| `chart_type` | String | Chart type ID |
| `data_mapping` | Object | How schema fields map to chart dimensions |
| `data_series` | Array | Data series with semantic classifications |
| `highlights` | Array | Visual highlights linked to insights |

### Output Example

```json
{
  "chart_type": "line_chart",
  "data_mapping": {
    "x_axis": "month",
    "y_axis": "value",
    "group_by": "metric_type"
  },
  "data_series": [
    {
      "series_id": "revenue",
      "group_value": "Revenue",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "Revenue"
    },
    {
      "series_id": "costs",
      "group_value": "Costs",
      "prominence": "secondary",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Costs"
    }
  ],
  "highlights": [
    {
      "id": "highlight_growth",
      "insight_id": "insight_growth",
      "type": "band",
      "description": "Q3 Growth Period",
      "start": "2024-07",
      "end": "2024-09"
    }
  ]
}
```

### DataMapping Reference

| Field | Purpose | Example |
|-------|---------|---------|
| `x_axis` | Field for X-axis | `"month"`, `"date"` |
| `y_axis` | Field for Y-axis | `"revenue"`, `"value"` |
| `group_by` | Field to group by for creating series | `"product"`, `"metric_type"` |
| `value` | Primary value field (KPI, pie, treemap) | `"amount"`, `"share"` |
| `row` | Field for grid rows (heatmaps) | `"day"` |
| `column` | Field for grid columns (heatmaps) | `"hour"` |

### DataSeries Reference

| Field | Purpose | Example |
|-------|---------|---------|
| `series_id` | Unique identifier | `"revenue"`, `"product_a"` |
| `field` | Column name (wide-format) | `"revenue"`, `"costs"` |
| `group_value` | Value in group_by field (long-format) | `"Product A"`, `"Online"` |
| `value_range` | Numeric range (value-based) | `{ "min": 80, "max": null }` |
| `prominence` | Visual weight | `"primary"`, `"secondary"` |
| `purpose` | Functional role | `"data-focus"`, `"data-comparison"` |
| `sentiment` | Evaluative meaning | `"positive"`, `"negative"` |
| `label` | Human-readable label | `"Revenue"`, `"Total Sales"` |

## What the Agent Does NOT Output

The following are handled by the **UI style guide**, not the agent:

| Field | Handled By |
|-------|------------|
| `structuralConfig` (showDots, showLegend, gridlines, etc.) | UI defaults per chart type |
| `elementClassifications` (axes, borders, titles) | UI style guide (consistent across all charts) |
| `accessibilityHints` | UI accessibility system |
| `lineStyle` | UI derives from `purpose` |
| Colors, fonts, sizes, stroke widths | UI design system |

See [Agent-UI Handoff](../03-agent-ui-handoff.md) for the complete boundary specification.

## Process

### Step 1: Evaluate Base Structure

Assess whether the chart structure is sound:
- Is the chart type appropriate for the data?
- Are all necessary elements present?
- Are there obvious structural issues?

### Step 2: Apply Classification System

For each element, assign classifications across three axes:

**Prominence** (how much attention):
- `hide` → Remove entirely
- `background` → Barely visible
- `baseline` → Present but passive
- `secondary` → Visible but subordinate
- `primary` → Main focus
- `callout` → Maximum prominence (one per chart)

**Purpose** (what function):
- `data-focus` → Primary data
- `data-comparison` → Comparison data
- `data-projection` → Forecast data
- `reference` → Reference lines
- `annotation` → Labels and callouts
- `structural` → Axes, gridlines, borders
- `navigational` → Titles, legends

**Sentiment** (evaluative meaning):
- `positive` → Good outcome
- `negative` → Bad outcome
- `neutral` → No evaluation
- `warning` → Attention needed

See [Classification System](../02-classification-system.md) for detailed guidance.

### Step 3: Identify Structural Corrections

Flag issues that need fixing:
- Diagonal or rotated text
- Center-aligned text blocks
- Legends that could be direct labels
- Multiple callout elements
- Overcrowded areas
- Sidebar-positioned insights

### Step 4: Apply Cognitive Anchoring

Ensure insights are properly connected to data:
- Each insight should have a corresponding visual anchor
- Insights should be proximate to relevant data
- Visual pointers may be needed for connection

### Step 5: Establish Narrative Sequence

If multiple insights exist, order them logically:
1. **Trend** (what happened)
2. **Cause** (why it happened)
3. **Recommendation** (what to do)

## Handoff to UI

The Refinement output is the final agent output. Pass directly to the UI:

```json
{
  "chart_type": "line_chart",
  "data_mapping": {
    "x_axis": "month",
    "y_axis": "value",
    "group_by": "metric_type"
  },
  "data_series": [
    {
      "series_id": "revenue",
      "group_value": "Revenue",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "Revenue"
    }
  ],
  "highlights": [ ... ]
}
```

The UI then:
1. Applies `structuralConfig` defaults for the chart type (showDots, showLegend, etc.)
2. Applies `elementClassifications` defaults (axes, gridlines, borders - consistent across all charts)
3. Derives `lineStyle` from `purpose` (data-focus → solid, data-comparison → dashed, data-projection → dotted)
4. Maps `prominence` to visual weight (opacity, stroke width)
5. Maps `sentiment` to colors from its design system

---

## Core Philosophy

### Data-Ink Ratio

Every visual element consumes cognitive load. Maximize the ratio of meaningful information to visual elements:

```
Data-Ink Ratio = Ink used for data / Total ink used
```

Elements that don't represent data—borders, backgrounds, redundant labels—dilute this ratio and should be scrutinized for removal.

### Cognitive Load and Clutter

**Cognitive load** is the mental effort required to process information. Every element added to a chart takes up cognitive load.

**Clutter** consists of visual elements that take up space but don't increase understanding. Clutter causes the "ugh" moment—when someone looks at a chart and decides it's too complicated to be worth their time.

**Perceived cognitive load** matters most: how hard the audience *believes* they'll have to work to understand the chart. Even if a chart is actually simple, if it *looks* complex, engagement drops.

### The "Ugh" Test

If someone looking at the chart would say "ugh" (out loud or mentally), it has too much clutter. The goal is charts that invite engagement rather than resistance.

---

## Gestalt Principles for Refinement

The Gestalt principles define how humans perceive and organize visual elements. Apply them to identify what can be removed or simplified.

### Proximity

**Principle**: Objects physically close together are perceived as belonging to a group.

**Application**:
- Use spacing to create groups without explicit borders
- In tables, row spacing creates visual rows without horizontal lines
- Place labels near their data elements
- Position insights close to the data they describe

**Refinement implication**: If borders or lines are used to create groups, evaluate whether spacing alone could achieve the same grouping. If so, classify the borders as `prominence: "hide"`.

### Similarity

**Principle**: Objects with similar color, shape, size, or orientation are perceived as related.

**Application**:
- Related data series should share visual treatment
- Labels should match their data element's classification
- Consistent classification → consistent visual treatment

**Refinement implication**: Ensure related elements receive consistent `purpose` classifications. When a label exists for a data element, they should share the same prominence level.

### Enclosure

**Principle**: Objects physically enclosed together are perceived as a group. Light shading is often sufficient.

**Application**:
- Subtle shaded regions can distinguish forecast from actual data
- Light backgrounds can group related annotations
- Enclosure directs attention to specific chart regions

**Refinement implication**: When enclosure is used, classify the background as `prominence: "background"` so it recedes. Prefer subtle shading over heavy borders.

### Closure

**Principle**: The mind perceives complete shapes even when parts are missing. We "close" incomplete figures.

**Application**:
- **Chart borders are unnecessary**—the data and white space create a cohesive visual unit
- Background fills are unnecessary—the chart appears complete without them
- The brain perceives the chart as complete without explicit boundaries

**Refinement implication**: Chart borders should almost always be `prominence: "hide"`. Background fills should be `prominence: "hide"` unless serving a specific enclosure purpose.

### Continuity

**Principle**: The eye follows the smoothest path and creates continuity even where it doesn't explicitly exist.

**Application**:
- **Y-axis lines can often be removed**—white space between labels and data creates implicit alignment
- The consistent gap creates a visual "line" through continuity
- Line charts leverage continuity to show trends

**Refinement implication**: Evaluate whether axis lines are necessary. If consistent white space provides alignment, classify axis lines as `prominence: "hide"`.

### Connection

**Principle**: Objects physically connected are perceived as grouped. Connection has stronger associative value than color or shape.

**Application**:
- Line charts work because connected points show order and trend
- Annotation pointers connect insights to data regions
- Flow lines show relationships between elements

**Refinement implication**: In line charts, the connecting lines are essential—classify with appropriate prominence. For annotations, ensure pointers share classification with their associated text.

---

## Decluttering Process

Apply these steps systematically to remove unnecessary elements:

### Step 1: Remove Chart Borders

Chart borders are included by default in most tools but rarely serve a purpose. The closure principle tells us the chart appears complete without them.

**Action**: Classify `chartBorder` as `prominence: "hide"`.

### Step 2: Remove or Minimize Gridlines

Gridlines can help when precise values need to be read, but often add more noise than value—especially when trends matter more than exact numbers.

**Decision logic**:
- Trend/pattern focus → `prominence: "hide"`
- Approximate reference helpful → `prominence: "background"`
- Precise reading required → `prominence: "baseline"`

### Step 3: Remove Unnecessary Data Markers

On line charts, data markers (dots at each point) are often redundant when the line itself communicates the information.

**Decision logic**:
- Dense, evenly spaced data → markers `prominence: "hide"`
- Sparse data or individual points matter → markers visible
- Only emphasis points need markers → selective visibility

### Step 4: Clean Up Axis Labels

Diagonal text is significantly harder to read—one study found 45-degree rotation is 52% slower to read than horizontal text.

**Corrections to flag**:
- Diagonal labels → correct to horizontal
- Excessive precision → recommend reduction
- Overly long labels → recommend abbreviation

### Step 5: Replace Legends with Direct Labels

Legends force the audience to move their eyes back and forth between legend and data. Direct labels eliminate this overhead.

**Decision logic**:
- Fewer than 4-5 series + no overlap → use direct labels, classify legend as `hide`
- Direct labels would create clutter → retain legend as `baseline`

### Step 6: Apply Consistent Color Classification

Each distinct color consumes cognitive resources. Colors should carry meaning through the sentiment axis, not merely provide decoration.

**Principles**:
- Assign sentiment based on business meaning
- Ensure related elements share purpose classifications
- Flag excessive color variation without semantic purpose

---

## Contrast Strategy

### The Hawk-in-Pigeons Principle

> "It's easy to spot a hawk in a sky full of pigeons, but as the variety of birds increases, that hawk becomes harder to pick out."

**The principle**: The more things we make different, the less any of them stand out.

**The corollary**: To make something stand out, make it the *one thing* that's different. Push everything else to neutral, consistent treatment.

### Strategic vs. Non-Strategic Contrast

| Non-Strategic | Strategic |
|---------------|-----------|
| Many colors without meaning | One accent color, rest neutral |
| Multiple highlighted elements | One callout, others recede |
| Every series equally prominent | Focus series prominent, comparison series muted |

### Application

1. Identify the single most important element
2. Classify that element as `callout` or `primary`
3. Demote competing elements to `secondary` or `baseline`
4. Ensure only meaningful differences receive visual distinction

---

## Cognitive Anchoring

### The Problem

When insight text is separated from the data it describes—in a sidebar, below the chart, or in a separate panel—the viewer must work to maintain the connection.

### The Solution

**Anchoring** places insight text directly above, within, or adjacent to the visualization region it describes, creating immediate cognitive link.

### Guidelines

1. **Place insights proximate to their data region**
   - Don't place insights in separate sidebars
   - Position near the relevant data

2. **Use visual pointers for explicit connection**
   - Subtle callout lines or arrows
   - Faded overlays linking text to data

3. **Maintain 1:1 mapping**
   - Each insight statement corresponds to a specific data region
   - If an insight references data that isn't visually distinct, consider highlighting that data

### Output Format

```json
{
  "anchorMappings": [
    { "insight": "annotation_q3Insight", "dataRegion": "dataPoint_q3" }
  ]
}
```

---

## Narrative Structure

### Temporal Rhythm for Insights

When multiple insights exist, order them as a narrative:

1. **Trend** (what happened)
   - Describe the pattern or change observed
   - Example: "Revenue increased 15% quarter-over-quarter"
   - Classification: `prominence: "primary"`

2. **Cause** (why it happened)
   - Explain the driver or context
   - Example: "Growth driven by Q3 product launch"
   - Classification: `prominence: "secondary"`

3. **Recommendation** (what to do)
   - Suggest action based on the finding
   - Example: "Recommend expanding to APAC region"
   - Classification: `prominence: "callout"`

### Output Format

```json
{
  "narrativeSequence": ["insight_trend", "insight_cause", "insight_recommendation"]
}
```

---

## Dashboard-Level Considerations

When refining charts within a dashboard:

### Consistent Patterns

- Same position for titles across tiles
- Same treatment for callouts
- Consistent annotation style

### Callout Budgeting

- One callout per tile maximum
- Consider whether multiple tiles should share focus
- Avoid "everything is highlighted" syndrome

### Visual Rhythm

Within each tile: insight → chart → optional action bar

Maintain this structure consistently across the dashboard.

---

## Element Classification Checklist

### Borders & Backgrounds

| Element | Default Classification |
|---------|----------------------|
| Chart border | `prominence: "hide"`, `purpose: "structural"` |
| Background fill | `prominence: "hide"`, `purpose: "structural"` |
| Plot area border | `prominence: "hide"`, `purpose: "structural"` |

### Gridlines

| Scenario | Classification |
|----------|---------------|
| Trend/pattern focus | `prominence: "hide"` |
| Approximate reference needed | `prominence: "background"`, `purpose: "structural"` |
| Precise reading required | `prominence: "baseline"`, `purpose: "structural"` |

### Axes

| Element | Classification |
|---------|---------------|
| X-axis line | `prominence: "baseline"` or `"hide"`, `purpose: "structural"` |
| Y-axis line | Usually `prominence: "hide"`, `purpose: "structural"` |
| Axis labels | `prominence: "baseline"`, `purpose: "navigational"` |
| Axis titles | `prominence: "baseline"`, `purpose: "navigational"` |

### Data Elements

| Element | Classification |
|---------|---------------|
| Primary data series | `prominence: "primary"`, `purpose: "data-focus"`, sentiment varies |
| Comparison data | `prominence: "secondary"`, `purpose: "data-comparison"` |
| Forecast/projection | `prominence: "secondary"`, `purpose: "data-projection"` |
| Key insight point | `prominence: "callout"`, `purpose: "data-focus"` |

### Labels & Legends

| Element | Classification |
|---------|---------------|
| Legend (when direct labels feasible) | `prominence: "hide"` |
| Legend (when necessary) | `prominence: "baseline"`, `purpose: "navigational"` |
| Direct data labels | `prominence: "primary"`, `purpose: "annotation"` |
| Title | `prominence: "primary"`, `purpose: "navigational"` |
| Subtitle | `prominence: "secondary"`, `purpose: "navigational"` |

### Annotations

| Element | Classification |
|---------|---------------|
| Primary insight callout | `prominence: "callout"`, `purpose: "annotation"` |
| Supporting observation | `prominence: "primary"` or `"secondary"`, `purpose: "annotation"` |
| Reference note | `prominence: "baseline"`, `purpose: "annotation"` |

---

## Structural Corrections Reference

| Issue | Correction | Rationale |
|-------|------------|-----------|
| `diagonal` | `horizontal` | Diagonal text is 52% slower to read |
| `center-aligned` | `left-aligned` | Left alignment creates clean edges, follows Z-pattern |
| `bottom-legend` | `top-left-legend` or `direct-labels` | Reduces eye travel |
| `sidebar-insight` | `proximate-to-data` | Cognitive anchoring principle |
| `multiple-callouts` | `single-callout` | Focus is lost with multiple highlights |
| `overcrowded` | `increase-spacing` | White space reduces cognitive load |
| `excessive-precision` | `round-numbers` | Unnecessary precision is clutter |

---

## Chart-Specific Documents

For detailed refinement guidance per chart type, see:

| Chart Type | Refinement Document |
|------------|---------------------|
| KPI Card | [refinement-kpi-card.md](./refinement-kpi-card.md) |
| Data Table | [refinement-data-table.md](./refinement-data-table.md) |
| Bar Chart (Vertical) | [refinement-bar-chart-vertical.md](./refinement-bar-chart-vertical.md) |
| Bar Chart (Horizontal) | [refinement-bar-chart-horizontal.md](./refinement-bar-chart-horizontal.md) |
| Bar Chart (Stacked) | [refinement-bar-chart-stacked.md](./refinement-bar-chart-stacked.md) |
| Bar Chart (Grouped) | [refinement-bar-chart-grouped.md](./refinement-bar-chart-grouped.md) |
| Line Chart | [refinement-line-chart.md](./refinement-line-chart.md) |
| Area Chart | [refinement-area-chart.md](./refinement-area-chart.md) |
| Scatter Plot | [refinement-scatter-plot.md](./refinement-scatter-plot.md) |
| Pie/Donut Chart | [refinement-pie-donut-chart.md](./refinement-pie-donut-chart.md) |
| Heatmap | [refinement-heatmap.md](./refinement-heatmap.md) |
| Histogram | [refinement-histogram.md](./refinement-histogram.md) |
| Treemap | [refinement-treemap.md](./refinement-treemap.md) |

---

## See Also

- [Classification System](../02-classification-system.md) — Full classification reference
- [Selection Interface](../selection/selection.md) — Previous step in pipeline
- [Agent-UI Handoff](../03-agent-ui-handoff.md) — Agent vs UI responsibilities
