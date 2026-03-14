---
type: reference
category: contributing
tags: [contributing, template, extensibility, adding-charts]
---

# Contributing: Adding New Chart Types

This guide explains how to extend the Data Viz Bible with new visualization types while maintaining consistency for the action-oriented pipeline and RAG retrieval.

## Overview

Adding a new chart type requires creating documents for each action in the pipeline:

1. **Selection document** — When to choose this chart
2. **Refinement document** — How to classify and improve elements
3. **Formatting document** — Visual style specifications
4. **Implementation document(s)** — Code for each supported library

Plus updates to:
- Index (`00-index.md`)
- Any relevant cross-references

## File Naming Convention

```
<action>-<chart-type-id>.md
```

Examples:
- `selection-waterfall-chart.md`
- `refinement-waterfall-chart.md`
- `formatting-waterfall-chart.md`
- `implementation-waterfall-chart-recharts.md`
- `implementation-waterfall-chart-d3.md`

**Chart Type ID**: Use snake_case (matching the proto ChartType enum), be specific about variants:
- `bar_chart_vertical` (not just `bar_chart`)
- `bar_chart_horizontal`
- `bar_chart_stacked`
- `pie_chart` and `donut_chart` (separate documents)

## Step 1: Create Selection Document

Create `selection/selection-<chart-type>.md`:

```markdown
---
type: action-implementation
action: selection
chart-type: <chart-type-id>
aliases: [<alternative names users might say>]
data-pattern: <pattern description>
family: <summary|ranking|evolution|distribution|correlation|partOfWhole|tabular>
priority: <P0|P1|P2>
tags: [selection, <chart-type>, <relevant keywords>]
---

# Selection: <Chart Type Display Name>

<One-line description of what this chart shows>

## When to Use

- <Primary use case>
- <Data shape requirements>
- <User intent signals>

### Data Pattern

- <N> DIMENSION + <M> MEASURE + [TEMPORAL]
- Row count considerations

### User Intent Signals

Queries that suggest this chart:
- "<example query 1>"
- "<example query 2>"

## When NOT to Use

- <Anti-pattern 1> → Use <alternative> instead
- <Anti-pattern 2> → Use <alternative> instead

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| DIMENSION | Yes/No | <how it's used> |
| MEASURE | Yes/No | <how it's used> |
| TEMPORAL | Yes/No | <how it's used> |

## Selection Decision

```
IF <condition>:
    AND <condition>:
    → Select <chart-type>
```

## Alternatives Comparison

| Scenario | This Chart | Alternative | Recommendation |
|----------|------------|-------------|----------------|
| <scenario> | <pros> | <pros> | <which to choose> |

## See Also

- [Selection Interface](./selection.md)
- [<Related chart>](./selection-<related>.md)
```

## Step 2: Create Refinement Document

Create `refinement/refinement-<chart-type>.md`:

```markdown
---
type: action-implementation
action: refinement
chart-type: <chart-type-id>
tags: [refinement, <chart-type>, classification, <relevant keywords>]
---

# Refinement: <Chart Type Display Name>

Refinement guidance specific to <chart type>.

## Element Inventory

Elements typically present in this chart type:

| Element | Default Prominence | Default Purpose | Notes |
|---------|-------------------|-----------------|-------|
| chartBorder | `hide` | `structural` | Remove per closure principle |
| gridlines | `hide` or `background` | `structural` | Usually unnecessary |
| xAxisLine | `baseline` | `structural` | |
| ... | ... | ... | ... |

## Classification Patterns

### Single Series

```json
{
  "dataSeries_main": { "prominence": "primary", "purpose": "data-focus", "sentiment": "<varies>" }
}
```

### Multiple Series (Focus + Comparison)

```json
{
  "dataSeries_focus": { "prominence": "primary", "purpose": "data-focus" },
  "dataSeries_comparison": { "prominence": "secondary", "purpose": "data-comparison" }
}
```

### With Callout

```json
{
  "dataPoint_key": { "prominence": "callout", "purpose": "data-focus", "sentiment": "<varies>" },
  "annotation_insight": { "prominence": "callout", "purpose": "annotation" }
}
```

## Gestalt Applications

### <Relevant Principle>

<How this principle applies specifically to this chart type>

## Common Structural Corrections

| Issue | Correction | Rationale |
|-------|------------|-----------|
| <issue> | <correction> | <why> |

## Decluttering Checklist

- [ ] <Chart-specific item to check>
- [ ] <Chart-specific item to check>

## Example Refinement

### Before

<Description of unrefined state>

### Classification Output

```json
{
  "elements": { ... },
  "structuralCorrections": [ ... ]
}
```

### Principles Applied

- <Principle 1>
- <Principle 2>

## See Also

- [Refinement Interface](./refinement.md)
- [Classification System](../02-classification-system.md)
```

## Step 3: Create Formatting Document

Create `formatting/formatting-<chart-type>.md`:

```markdown
---
type: action-implementation
action: formatting
chart-type: <chart-type-id>
tags: [formatting, <chart-type>, styling, <relevant keywords>]
---

# Formatting: <Chart Type Display Name>

Visual style specifications for <chart type>.

## Element Styling

### Data Elements

| Classification | Stroke/Fill | Width | Dash | Opacity |
|---------------|-------------|-------|------|---------|
| primary + data-focus + positive | #22c55e | 2.5px | none | 1.0 |
| primary + data-focus + negative | #ef4444 | 2.5px | none | 1.0 |
| secondary + data-comparison | #6b7280 | 1.5px | 4 2 | 0.8 |
| ... | ... | ... | ... | ... |

### Structural Elements

| Element | Color | Width | Style |
|---------|-------|-------|-------|
| gridlines (if shown) | #e5e7eb | 0.5px | solid |
| axis line | #d1d5db | 1px | solid |
| ... | ... | ... | ... |

### Typography

| Element | Size | Weight | Color |
|---------|------|--------|-------|
| title | 18px | 600 | #1a1a1a |
| axis labels | 12px | 400 | #666666 |
| ... | ... | ... | ... |

## Chart-Specific Considerations

### <Consideration 1>

<Formatting guidance specific to this chart>

### <Consideration 2>

<Formatting guidance specific to this chart>

## Responsive Adjustments

| Breakpoint | Adjustments |
|------------|-------------|
| < 400px | <adjustments> |
| 400-600px | <adjustments> |

## Accessibility Notes

- <Chart-specific accessibility consideration>

## See Also

- [Formatting Interface](./formatting.md)
```

## Step 4: Create Implementation Document(s)

Create `implementation/implementation-<chart-type>-<library>.md`:

```markdown
---
type: action-implementation
action: implementation
chart-type: <chart-type-id>
library: <recharts|d3|react>
tags: [implementation, <chart-type>, <library>, code]
---

# Implementation: <Chart Type> (<Library>)

<Library>-specific implementation for <chart type>.

## Dependencies

```javascript
import { ... } from '<library>';
```

## Basic Example

```tsx
<Complete minimal working example>
```

## Applying Classifications

### Primary Data (data-focus, positive)

```tsx
<Code showing how to apply this classification>
```

### Secondary Data (data-comparison)

```tsx
<Code showing how to apply this classification>
```

## Props Reference

| Prop | Type | Description |
|------|------|-------------|
| <prop> | <type> | <description> |

## Data Transformation

```javascript
// Transform raw data to format needed by this library
const chartData = ...
```

## Common Patterns

### <Pattern 1>

```tsx
<Code example>
```

### <Pattern 2>

```tsx
<Code example>
```

## See Also

- [Implementation Interface](./implementation.md)
- [<Library> Documentation](<external link>)
```

## Step 5: Update Index

Add the new chart to `00-index.md`:

1. Add to the appropriate priority tier table (P0/P1/P2)
2. Link all four action documents

## Frontmatter Requirements

All documents must include these frontmatter fields:

### Selection Documents

```yaml
---
type: action-implementation
action: selection
chart-type: <id>
aliases: [<list of alternative names>]
data-pattern: <pattern description>
family: <family name>
priority: P0|P1|P2
tags: [selection, <chart-type>, ...]
---
```

### Refinement Documents

```yaml
---
type: action-implementation
action: refinement
chart-type: <id>
tags: [refinement, <chart-type>, classification, ...]
---
```

### Formatting Documents

```yaml
---
type: action-implementation
action: formatting
chart-type: <id>
tags: [formatting, <chart-type>, styling, ...]
---
```

### Implementation Documents

```yaml
---
type: action-implementation
action: implementation
chart-type: <id>
library: <library-name>
tags: [implementation, <chart-type>, <library>, code, ...]
---
```

## RAG Optimization Tips

### Aliases

Include all ways users might refer to this chart:
- Formal names ("Horizontal Bar Chart")
- Informal names ("bar graph")
- Abbreviations
- Common misnomers (terms users might confuse)

### Tags

Include:
- The action name
- The chart type
- The chart family
- Relevant use case keywords
- Data pattern keywords

### Cross-References

Link to:
- The interface document for the action
- Related chart types
- Alternative chart types
- Relevant foundation documents

## Checklist for New Chart Types

- [ ] `selection/selection-<chart>.md` created with full template
- [ ] `refinement/refinement-<chart>.md` created with element inventory
- [ ] `formatting/formatting-<chart>.md` created with style specs
- [ ] `implementation/implementation-<chart>-recharts.md` (if applicable)
- [ ] `implementation/implementation-<chart>-d3.md` (if applicable)
- [ ] `implementation/implementation-<chart>-react.md` (if applicable)
- [ ] Added to `00-index.md` in appropriate tier
- [ ] Frontmatter includes all required fields
- [ ] Aliases populated for RAG retrieval
- [ ] Cross-references added to related documents
- [ ] Examples include classification output JSON

## Example: Adding Gauge Chart

### 1. Determine Metadata

- **Chart Type ID**: `gauge-chart`
- **Family**: `summary`
- **Priority**: `P2`
- **Aliases**: `speedometer`, `dial chart`, `meter`, `radial gauge`
- **Data Pattern**: Single value with range (0D + 1M + range definition)

### 2. Create Files

```
selection/selection-gauge-chart.md
refinement/refinement-gauge-chart.md
formatting/formatting-gauge-chart.md
implementation/implementation-gauge-chart-react.md
```

### 3. Key Content

**Selection**: When to use gauge vs. KPI card, data requirements, user intent signals like "show progress toward goal"

**Refinement**: Elements (arc, needle, labels, thresholds), classification patterns, when to show thresholds

**Formatting**: Arc colors by sentiment, needle styling, label positioning

**Implementation**: React component with SVG arc generation

### 4. Update Index

Add to P2 table in `00-index.md`

## See Also

- [Index](./00-index.md) — Document navigation
- [Schema Reference](./01-schema-reference.md) — Field roles
- [Classification System](./02-classification-system.md) — Multi-axis classification
