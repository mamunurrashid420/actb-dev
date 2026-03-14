---
type: action-implementation
action: refinement
chart-type: slope_chart
tags: [refinement, slope, classification, change, data-series]
---

# Refinement: Slope Chart

Refinement guidance for slope charts.

> **Key Principle**: The agent outputs `dataSeries` with semantic classifications (prominence, purpose, sentiment). The UI handles structural elements (axes, gridlines, borders) via its style guide.

## Element Inventory

| Element | Default Prominence | Default Purpose | Notes |
|---------|-------------------|-----------------|-------|
| `chartBorder` | `hide` | `structural` | |
| `lines` | `primary` | `data-focus` | Connecting slopes |
| `points_left` | `baseline` | `data-focus` | Start values |
| `points_right` | `baseline` | `data-focus` | End values |
| `labels_left` | `primary` | `annotation` | Item names + values |
| `labels_right` | `primary` | `annotation` | End values |
| `columnHeaders` | `secondary` | `navigational` | Time period labels |
| `title` | `primary` | `navigational` | |

## Classification Patterns

### All Lines Equal

```json
{
  "elementClassifications": {
    "lines_all": { "prominence": "primary", "purpose": "data-focus" },
    "labels_left": { "prominence": "primary", "purpose": "annotation" },
    "labels_right": { "prominence": "primary", "purpose": "annotation" }
  }
}
```

### With Highlighted Item

```json
{
  "elementClassifications": {
    "line_highlighted": { 
      "prominence": "callout", 
      "purpose": "data-focus", 
      "sentiment": "positive"
    },
    "lines_other": { 
      "prominence": "baseline", 
      "purpose": "data-comparison" 
    }
  }
}
```

### By Direction of Change

```json
{
  "elementClassifications": {
    "lines_increased": { 
      "prominence": "primary", 
      "purpose": "data-focus", 
      "sentiment": "positive"
    },
    "lines_decreased": { 
      "prominence": "primary", 
      "purpose": "data-focus", 
      "sentiment": "negative"
    },
    "lines_unchanged": { 
      "prominence": "secondary", 
      "purpose": "data-focus", 
      "sentiment": "neutral"
    }
  }
}
```

## Gestalt Applications

### Connection

**Slope chart application**: Lines connect the same item across time. The slope direction shows change.

### Similarity

**Slope chart application**: Lines can be colored by direction (up = green, down = red) or by category.

### Continuity

**Slope chart application**: The eye follows each line from left to right, tracking individual items.

## Common Structural Corrections

| Issue | Correction | Rationale |
|-------|------------|-----------|
| Many crossing lines | Highlight focus items, gray others | Reduce spaghetti |
| No endpoint labels | Add value labels | Need to read values |
| Too many items (>15) | Filter to top/bottom N | Overwhelming |
| Inconsistent spacing | Align by value or rank | Visual order |

## Decluttering Checklist

- [ ] Exactly 2 time points?
- [ ] Labels at both endpoints?
- [ ] Crossing lines manageable?
- [ ] Focus items highlighted if needed?
- [ ] Column headers showing time periods?

## Handling Crossed Lines

When many lines cross:

1. **Highlight strategy**: Focus 1-3 items, gray others
2. **Interactive**: Highlight on hover
3. **Small multiples**: Separate into groups
4. **Filter**: Show only top/bottom movers

## See Also

- [Refinement Interface](./refinement.md)
- [Agent-UI Handoff](../03-agent-ui-handoff.md) — Agent vs UI responsibilities
