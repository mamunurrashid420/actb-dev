---
type: reference
category: classification
tags: [classification, prominence, purpose, sentiment, visual-hierarchy, multi-axis, semantic]
---

# Classification System

The multi-axis classification system provides semantic labels for chart elements. The agent assigns classifications; the frontend CSS layer translates them into visual styles.

## Why Multi-Axis Classification?

A single prominence scale cannot capture all distinctions needed for effective visual hierarchy:

- Two data series at the same prominence level may need different visual treatment based on their function (primary data vs. comparison benchmark)
- A highlighted element representing good news should look different from one representing bad news, despite having the same prominence
- Projected/forecast data should be visually distinct from actual data, independent of prominence

The multi-axis system separates these concerns:
- **Prominence**: How much attention should this element receive?
- **Purpose**: What function does this element serve?
- **Sentiment**: What is the evaluative meaning?

## The Three Axes

### Axis 1: Prominence

*How visually prominent should this element be?*

Prominence determines visual weight—how much the element demands viewer attention relative to other elements.

| Value | Definition | Cognitive Purpose | Typical Elements |
|-------|------------|-------------------|------------------|
| `hide` | Remove from rendering entirely | Reduce clutter; element adds no value | Unnecessary borders, backgrounds, redundant markers, legends replaced by direct labels |
| `background` | Barely visible; structural scaffolding | Present for orientation but shouldn't attract conscious attention | Subtle gridlines, minor tick marks, light enclosure shading |
| `baseline` | Present but passive; neutral reference | Provides context without competing for analytical focus | Axis lines, reference lines, comparison benchmarks, standard axis labels |
| `secondary` | Visible but clearly subordinate | Supports the primary focus; noticeable but not dominant | Comparison data series, supporting annotations, subtitles |
| `primary` | Main visual focus | Core information the viewer should process and remember | Primary data series, key labels, chart title, main metric values |
| `callout` | Maximum prominence; demands immediate attention | Key insight, critical value, anomaly, or required action | Insight annotations, anomaly markers, recommendation callouts |

**The Callout Constraint**: A chart should have at most one element classified as `callout`. Multiple callouts compete for attention and defeat the purpose of maximum prominence.

---

### Axis 2: Purpose

*What function does this element serve?*

Purpose determines visual style—how the element should be rendered to communicate its function.

| Value | Definition | Typical Elements | Visual Treatment |
|-------|------------|------------------|------------------|
| `data-focus` | The primary data being analyzed | Main series, key metric bars, central values | Solid lines/fills; most saturated colors |
| `data-comparison` | Data shown for context or comparison | Benchmarks, competitors, prior period, industry average | Dashed lines; slightly desaturated |
| `data-projection` | Forecast, estimate, or target values | Projections, goals, predicted values | Dotted lines; may include uncertainty indicators |
| `reference` | Static reference points or thresholds | Zero line, target threshold, average line, limit markers | Thin rule lines; minimal visual weight |
| `annotation` | Explanatory text or visual markers | Insight callouts, data labels, notes, pointers | Text-based; may include connector lines |
| `structural` | Chart scaffolding and framework | Axes, gridlines, borders, tick marks | Should recede; never compete with data |
| `navigational` | Orientation and interpretive aids | Legend, axis titles, chart title, subtitle | Supports comprehension; consistent positioning |

---

### Axis 3: Sentiment

*What is the evaluative meaning?* (Optional—applies when data has evaluative context)

Sentiment determines color palette, independent of prominence and purpose.

| Value | Definition | When to Assign | Examples |
|-------|------------|----------------|----------|
| `positive` | Good outcome, success, gain | Desirable result achieved | Revenue up, costs down, goal exceeded |
| `negative` | Bad outcome, failure, loss | Undesirable result | Revenue down, costs up, target missed |
| `neutral` | No evaluative meaning | Objective data, structural elements | Most axes, gridlines, informational comparisons |
| `warning` | Caution, attention needed | Approaching threshold, potential issue | Near budget limit, trending toward problem |

**Context-Dependent Sentiment**: The same metric can have different sentiments:
- "Costs decreased 15%" → `positive` (cost reduction is good)
- "Revenue decreased 15%" → `negative` (revenue reduction is bad)
- "Headcount decreased 15%" → depends on context (efficiency vs. layoffs)

**Default to Neutral**: When sentiment is unclear, use `neutral`. Structural and navigational elements are typically `neutral`.

---

## Output Schema

For each chart element, output:

```json
{
  "elementId": {
    "prominence": "hide | background | baseline | secondary | primary | callout",
    "purpose": "data-focus | data-comparison | data-projection | reference | annotation | structural | navigational",
    "sentiment": "positive | negative | neutral | warning"
  }
}
```

Sentiment is optional—omit if not applicable (e.g., for structural elements).

### Complete Output Example

```json
{
  "chartId": "quarterly-revenue-analysis",
  "elements": {
    "chartBorder": {
      "prominence": "hide",
      "purpose": "structural"
    },
    "gridlines": {
      "prominence": "hide",
      "purpose": "structural"
    },
    "xAxisLine": {
      "prominence": "baseline",
      "purpose": "structural"
    },
    "yAxisLine": {
      "prominence": "hide",
      "purpose": "structural"
    },
    "xAxisLabels": {
      "prominence": "baseline",
      "purpose": "navigational"
    },
    "yAxisLabels": {
      "prominence": "baseline",
      "purpose": "navigational"
    },
    "dataSeries_revenue": {
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "positive"
    },
    "dataSeries_lastYear": {
      "prominence": "secondary",
      "purpose": "data-comparison",
      "sentiment": "neutral"
    },
    "dataSeries_forecast": {
      "prominence": "secondary",
      "purpose": "data-projection",
      "sentiment": "neutral"
    },
    "dataPoint_q3Peak": {
      "prominence": "callout",
      "purpose": "data-focus",
      "sentiment": "positive"
    },
    "referenceLine_target": {
      "prominence": "baseline",
      "purpose": "reference",
      "sentiment": "neutral"
    },
    "annotation_insight": {
      "prominence": "callout",
      "purpose": "annotation",
      "sentiment": "positive"
    },
    "legend": {
      "prominence": "hide",
      "purpose": "navigational"
    },
    "directLabel_revenue": {
      "prominence": "primary",
      "purpose": "annotation"
    },
    "title": {
      "prominence": "primary",
      "purpose": "navigational"
    }
  }
}
```

---

## Frontend CSS Mapping

The frontend translates classifications to visual styles. Example mapping:

```css
/* Prominence → Visual Weight */
[data-prominence="hide"] { display: none; }
[data-prominence="background"] { opacity: 0.3; }
[data-prominence="baseline"] { opacity: 0.6; }
[data-prominence="secondary"] { opacity: 0.8; }
[data-prominence="primary"] { opacity: 1.0; font-weight: 600; }
[data-prominence="callout"] { opacity: 1.0; font-weight: 700; }

/* Purpose → Visual Style */
[data-purpose="data-focus"] { stroke-dasharray: none; }
[data-purpose="data-comparison"] { stroke-dasharray: 4 2; }
[data-purpose="data-projection"] { stroke-dasharray: 2 2; }
[data-purpose="reference"] { stroke-width: 1px; }

/* Sentiment → Color Palette */
[data-sentiment="positive"] { --color: #22c55e; }
[data-sentiment="negative"] { --color: #ef4444; }
[data-sentiment="neutral"] { --color: #6b7280; }
[data-sentiment="warning"] { --color: #f59e0b; }

/* Combinations */
[data-prominence="primary"][data-purpose="data-focus"][data-sentiment="negative"] {
  stroke: #ef4444;
  stroke-width: 2.5px;
  stroke-dasharray: none;
}
```

This separation ensures:
- Agent decisions are portable across themes and brands
- Style changes don't require agent retraining
- Consistent design system enforcement

---

## Common Classification Patterns

### Default Element Classifications

| Element Type | Prominence | Purpose | Sentiment |
|--------------|------------|---------|-----------|
| Chart border | `hide` | `structural` | — |
| Background fill | `hide` | `structural` | — |
| Gridlines (if shown) | `background` | `structural` | — |
| X-axis line | `baseline` | `structural` | — |
| Y-axis line | `hide` or `baseline` | `structural` | — |
| Axis labels | `baseline` | `navigational` | — |
| Axis titles | `baseline` | `navigational` | — |
| Primary data series | `primary` | `data-focus` | context-dependent |
| Comparison data | `secondary` | `data-comparison` | `neutral` |
| Forecast data | `secondary` | `data-projection` | `neutral` |
| Reference line | `baseline` | `reference` | context-dependent |
| Data labels | `primary` | `annotation` | — |
| Key insight | `callout` | `annotation` | context-dependent |
| Legend | `baseline` or `hide` | `navigational` | — |
| Title | `primary` | `navigational` | — |
| Subtitle | `secondary` | `navigational` | — |

### Multi-Axis Combination Examples

| Scenario | Prominence | Purpose | Sentiment | Result |
|----------|------------|---------|-----------|--------|
| Main revenue line (up) | `primary` | `data-focus` | `positive` | Bold solid green line |
| Main revenue line (down) | `primary` | `data-focus` | `negative` | Bold solid red line |
| Last year comparison | `secondary` | `data-comparison` | `neutral` | Medium dashed gray line |
| Forecast projection | `secondary` | `data-projection` | `neutral` | Medium dotted gray line |
| Target threshold | `baseline` | `reference` | `neutral` | Thin gray rule |
| Budget limit (near) | `baseline` | `reference` | `warning` | Thin amber rule |
| Key insight callout | `callout` | `annotation` | varies | Maximum weight, sentiment color |

---

## Decision Logic

### Prominence Decision Tree

```
Does this element add informational value?
├── NO → prominence: "hide"
└── YES → Does its value outweigh its cognitive cost?
    ├── NO → prominence: "hide"
    └── YES → Is this the key insight or callout?
        ├── YES → prominence: "callout"
        └── NO → Is this the primary data?
            ├── YES → prominence: "primary"
            └── NO → Does this support the primary data?
                ├── YES → prominence: "secondary"
                └── NO → Is this structural/contextual?
                    ├── YES → Is it essential?
                    │   ├── YES → prominence: "baseline"
                    │   └── NO → prominence: "background"
                    └── NO → prominence: "hide"
```

### Purpose Decision Tree

```
What function does this element serve?
├── Data element?
│   ├── Primary data being analyzed → purpose: "data-focus"
│   ├── Comparison/benchmark data → purpose: "data-comparison"
│   └── Forecast/projection → purpose: "data-projection"
├── Reference line or threshold? → purpose: "reference"
├── Text, label, or callout? → purpose: "annotation"
├── Axis, gridline, or border? → purpose: "structural"
└── Title, legend, or axis title? → purpose: "navigational"
```

### Sentiment Decision Tree

```
Does this element have evaluative meaning?
├── Structural or navigational? → sentiment: "neutral" (or omit)
└── Data element?
    ├── No evaluative context → sentiment: "neutral"
    └── Has evaluative context?
        ├── Good outcome → sentiment: "positive"
        ├── Bad outcome → sentiment: "negative"
        ├── Approaching threshold → sentiment: "warning"
        └── Neutral/informational → sentiment: "neutral"
```

---

## What the Agent Does NOT Output

The agent outputs semantic classifications only. It never outputs:

- Specific colors (hex values, RGB)
- Font sizes, weights, or families
- Line thicknesses or stroke widths
- Pixel dimensions or spacing
- Opacity values
- Any CSS properties

This maintains separation of concerns: the agent decides *what* elements mean; the frontend decides *how* they look.

---

## See Also

- [Refinement Interface](./refinement/refinement.md) — How to apply classifications
- [Formatting Interface](./formatting/formatting.md) — How frontend maps classifications to styles
