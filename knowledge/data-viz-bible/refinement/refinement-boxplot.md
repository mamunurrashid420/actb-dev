---
type: action-implementation
action: refinement
chart-type: boxplot
tags: [refinement, boxplot, classification, distribution, data-series]
---

# Refinement: Box Plot

Refinement guidance for box plots.

> **Key Principle**: The agent outputs `dataSeries` with semantic classifications (prominence, purpose, sentiment). The UI handles structural elements (axes, gridlines, borders) via its style guide.

## Element Inventory

| Element | Default Prominence | Default Purpose | Notes |
|---------|-------------------|-----------------|-------|
| `chartBorder` | `hide` | `structural` | |
| `gridlines` | `background` | `structural` | Help read values |
| `boxes` | `primary` | `data-focus` | IQR (Q1-Q3) |
| `medianLines` | `primary` | `data-focus` | Center line |
| `whiskers` | `secondary` | `data-focus` | Min/max or fences |
| `outliers` | `callout` or `secondary` | `data-focus` | Points beyond fences |
| `xAxisLabels` | `baseline` | `navigational` | Group names |
| `yAxisLabels` | `baseline` | `navigational` | Value scale |
| `title` | `primary` | `navigational` | |

## Classification Patterns

### Basic Box Plot

```json
{
  "elementClassifications": {
    "boxes_all": { "prominence": "primary", "purpose": "data-focus" },
    "medianLines": { "prominence": "primary", "purpose": "data-focus" },
    "whiskers": { "prominence": "secondary", "purpose": "data-focus" },
    "outliers": { "prominence": "secondary", "purpose": "data-focus" },
    "gridlines": { "prominence": "background", "purpose": "structural" }
  }
}
```

### With Highlighted Group

```json
{
  "elementClassifications": {
    "box_highlighted": { 
      "prominence": "callout", 
      "purpose": "data-focus" 
    },
    "boxes_other": { 
      "prominence": "secondary", 
      "purpose": "data-comparison" 
    }
  }
}
```

### With Emphasized Outliers

```json
{
  "elementClassifications": {
    "boxes_all": { "prominence": "primary", "purpose": "data-focus" },
    "outliers": { 
      "prominence": "callout", 
      "purpose": "data-focus", 
      "sentiment": "warning"
    }
  }
}
```

## Gestalt Applications

### Enclosure

**Box plot application**: The box encloses the middle 50% of data (IQR).

### Similarity

**Box plot application**: All boxes should have consistent styling unless highlighting specific groups.

## Common Structural Corrections

| Issue | Correction | Rationale |
|-------|------------|-----------|
| Missing median line | Add distinct median | Key summary stat |
| Outliers not marked | Add outlier points | Important information |
| No gridlines | Add subtle gridlines | Help read values |
| Whisker definition unclear | Document in annotation | Different conventions exist |

## Decluttering Checklist

- [ ] Median line visible?
- [ ] Whisker definition documented?
- [ ] Outliers marked?
- [ ] Gridlines subtle?
- [ ] Groups have enough data?

## See Also

- [Refinement Interface](./refinement.md)
- [Agent-UI Handoff](../03-agent-ui-handoff.md) — Agent vs UI responsibilities
