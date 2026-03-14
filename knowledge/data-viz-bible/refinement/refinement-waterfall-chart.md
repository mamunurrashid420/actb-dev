---
type: action-implementation
action: refinement
chart-type: waterfall_chart
tags: [refinement, waterfall, classification, financial, data-series]
---

# Refinement: Waterfall Chart

Refinement guidance for waterfall charts.

> **Key Principle**: The agent outputs `dataSeries` with semantic classifications (prominence, purpose, sentiment). The UI handles structural elements (axes, gridlines, borders) via its style guide.

## Element Inventory

| Element | Default Prominence | Default Purpose | Notes |
|---------|-------------------|-----------------|-------|
| `chartBorder` | `hide` | `structural` | Remove |
| `gridlines` | `background` | `structural` | Help read values |
| `xAxisLine` | `baseline` | `structural` | |
| `bars_start` | `primary` | `data-focus` | Starting value |
| `bars_increase` | `primary` | `data-focus` | Positive changes |
| `bars_decrease` | `primary` | `data-focus` | Negative changes |
| `bars_end` | `primary` | `data-focus` | Ending total |
| `connectorLines` | `baseline` | `structural` | Link bars |
| `valueLabels` | `secondary` | `annotation` | Show amounts |
| `title` | `primary` | `navigational` | |

## Classification Patterns

### Standard Bridge

```json
{
  "elementClassifications": {
    "chartBorder": { "prominence": "hide", "purpose": "structural" },
    "gridlines": { "prominence": "background", "purpose": "structural" },
    "bars_start": { 
      "prominence": "primary", 
      "purpose": "data-focus", 
      "sentiment": "neutral"
    },
    "bars_increase": { 
      "prominence": "primary", 
      "purpose": "data-focus", 
      "sentiment": "positive"
    },
    "bars_decrease": { 
      "prominence": "primary", 
      "purpose": "data-focus", 
      "sentiment": "negative"
    },
    "bars_end": { 
      "prominence": "primary", 
      "purpose": "data-focus", 
      "sentiment": "neutral"
    },
    "connectorLines": { 
      "prominence": "baseline", 
      "purpose": "structural" 
    },
    "valueLabels": { 
      "prominence": "secondary", 
      "purpose": "annotation" 
    }
  }
}
```

### With Highlighted Driver

```json
{
  "elementClassifications": {
    "bar_keyDriver": { 
      "prominence": "callout", 
      "purpose": "data-focus", 
      "sentiment": "positive"
    },
    "bars_other": { 
      "prominence": "secondary", 
      "purpose": "data-focus" 
    }
  }
}
```

## Gestalt Applications

### Connection

**Waterfall application**: Connector lines show the running total flow from bar to bar.

### Similarity

**Waterfall application**: All increases share green color; all decreases share red. Start/end are neutral gray.

### Continuity

**Waterfall application**: The eye follows the connector lines, creating a continuous "bridge" narrative.

## Common Structural Corrections

| Issue | Correction | Rationale |
|-------|------------|-----------|
| No connector lines | Add dashed connectors | Shows running total relationship |
| Same color for all bars | Use green/red/gray | Semantic meaning is critical |
| Missing value labels | Add labels | Hard to read exact values |
| End bar doesn't match total | Verify calculation | Must equal cumulative sum |

## Decluttering Checklist

- [ ] Green for increases, red for decreases, gray for totals?
- [ ] Connector lines present?
- [ ] Value labels on all bars?
- [ ] Start and end bars clearly distinguished?
- [ ] X-axis labels readable (rotated if needed)?

## See Also

- [Refinement Interface](./refinement.md)
- [Agent-UI Handoff](../03-agent-ui-handoff.md) — Agent vs UI responsibilities
