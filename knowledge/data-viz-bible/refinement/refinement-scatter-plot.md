---
type: action-implementation
action: refinement
chart-type: scatter_plot
tags: [refinement, scatter, classification, correlation, data-series]
---

# Refinement: Scatter Plot

Refinement guidance for scatter plots showing relationships between variables.

> **Key Principle**: The agent outputs `data_series` with semantic classifications (prominence, purpose, sentiment). The UI handles structural elements (axes, gridlines, borders) via its style guide.

## Sample Data

```json
[
  { "company": "Acme Corp", "segment": "Enterprise", "revenue": 5200000, "employees": 450 },
  { "company": "Beta Inc", "segment": "SMB", "revenue": 1200000, "employees": 85 },
  { "company": "Gamma LLC", "segment": "Enterprise", "revenue": 8500000, "employees": 720 },
  { "company": "Delta Co", "segment": "SMB", "revenue": 800000, "employees": 45 },
  { "company": "Epsilon", "segment": "Startup", "revenue": 350000, "employees": 12 }
]
```

## DataMapping Configuration

For scatter plots, use `x_axis`, `y_axis`, and optionally `group_by`:

```json
{
  "data_mapping": {
    "x_axis": "employees",
    "y_axis": "revenue",
    "group_by": "segment"
  }
}
```

| Field | Purpose |
|-------|---------|
| `x_axis` | Field for horizontal position |
| `y_axis` | Field for vertical position |
| `group_by` | Field that creates color-coded groups |

## Element Inventory

| Element | Handled By | Notes |
|---------|------------|-------|
| Point colors | UI (from `sentiment` or categorical) | Groups get distinct colors |
| Point opacity | UI (from `prominence`) | Callout > primary > secondary |
| Point size | UI style guide | Consistent or encode third variable |
| X-axis | UI style guide | With title |
| Y-axis | UI style guide | With title |
| Gridlines | UI style guide | Background prominence |
| Trend line | Agent (via `highlights`) | Optional reference |
| Legend | UI style guide | Required for grouped |
| Title | UI style guide | Primary prominence |

## DataSeries Patterns

### Basic Scatter (All Points Equal)

When showing relationship without grouping:

```json
{
  "chart_type": "scatter_plot",
  "data_mapping": {
    "x_axis": "employees",
    "y_axis": "revenue"
  },
  "data_series": [
    {
      "series_id": "all_points",
      "field": "revenue",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Companies"
    }
  ]
}
```

### With Category Grouping

When comparing segments:

```json
{
  "chart_type": "scatter_plot",
  "data_mapping": {
    "x_axis": "employees",
    "y_axis": "revenue",
    "group_by": "segment"
  },
  "data_series": [
    {
      "series_id": "enterprise",
      "group_value": "Enterprise",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Enterprise"
    },
    {
      "series_id": "smb",
      "group_value": "SMB",
      "prominence": "primary",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "SMB"
    },
    {
      "series_id": "startup",
      "group_value": "Startup",
      "prominence": "primary",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Startup"
    }
  ]
}
```

### With Highlighted Outliers

When emphasizing specific points:

```json
{
  "chart_type": "scatter_plot",
  "data_mapping": {
    "x_axis": "employees",
    "y_axis": "revenue"
  },
  "data_series": [
    {
      "series_id": "all_points",
      "field": "revenue",
      "prominence": "secondary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Companies"
    }
  ],
  "highlights": [
    {
      "id": "outliers",
      "type": "points",
      "description": "High performers",
      "field_filters": [
        { "field": "company", "values": ["Gamma LLC"] }
      ],
      "prominence": "callout",
      "sentiment": "positive"
    }
  ]
}
```

### Focus Group vs. Comparison

When one segment is the focus:

```json
{
  "chart_type": "scatter_plot",
  "data_mapping": {
    "x_axis": "employees",
    "y_axis": "revenue",
    "group_by": "segment"
  },
  "data_series": [
    {
      "series_id": "enterprise",
      "group_value": "Enterprise",
      "prominence": "callout",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Enterprise (Focus)"
    },
    {
      "series_id": "smb",
      "group_value": "SMB",
      "prominence": "secondary",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "SMB"
    },
    {
      "series_id": "startup",
      "group_value": "Startup",
      "prominence": "secondary",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Startup"
    }
  ]
}
```

### With Trend Line

When showing correlation:

```json
{
  "chart_type": "scatter_plot",
  "data_mapping": {
    "x_axis": "employees",
    "y_axis": "revenue"
  },
  "data_series": [
    {
      "series_id": "all_points",
      "field": "revenue",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Companies"
    }
  ],
  "highlights": [
    {
      "id": "trend",
      "type": "trend_line",
      "description": "Linear correlation",
      "sentiment": "neutral"
    }
  ]
}
```

## Gestalt Applications

### Proximity

**Principle**: Elements close together are perceived as grouped.

**Scatter application**: Clusters of points naturally emerge when data is grouped. Don't need explicit enclosure.

### Similarity

**Principle**: Similar elements are perceived as related.

**Scatter application**: Points of the same color are perceived as belonging to the same group. Use consistently.

### Enclosure

**Principle**: Enclosed elements are perceived as grouped.

**Scatter application**: Can draw ellipses or regions around clusters, but use sparingly. Often unnecessary if color grouping is clear.

## Common Structural Corrections

| Issue | Correction | Rationale |
|-------|------------|-----------|
| Missing axis titles | Add titles | Critical for understanding what's plotted |
| Points too small | Increase size | Points should be easily visible |
| Overplotting | Add transparency | Overlapping points hide patterns |
| Too many groups | Simplify to focus | More than 5-6 groups confuses |

## Decluttering Checklist

- [ ] Axis fields correctly mapped?
- [ ] Groups using `group_by` (not multiple `data_series` per point)?
- [ ] Focus group at `callout` prominence if applicable?
- [ ] Labels provided for legend?
- [ ] Outliers highlighted via `highlights` array?

## Handling Overplotting

When many points overlap:

1. **Add transparency** - UI handles via `prominence: "secondary"`
2. **Reduce point size** - UI style guide
3. **Use highlights** for specific points of interest

## See Also

- [Refinement Interface](./refinement.md)
- [Agent-UI Handoff](../03-agent-ui-handoff.md) — Agent vs UI responsibilities
