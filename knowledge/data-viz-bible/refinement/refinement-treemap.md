---
type: action-implementation
action: refinement
chart-type: treemap
tags: [refinement, treemap, classification, hierarchy, data-series]
---

# Refinement: Treemap

Refinement guidance for treemaps showing hierarchical part-to-whole relationships.

> **Key Principle**: The agent outputs `data_series` with semantic classifications (prominence, purpose, sentiment). The UI handles structural elements (axes, gridlines, borders) via its style guide.

## Sample Data

```json
[
  { "category": "Electronics", "subcategory": "Phones", "sales": 450000 },
  { "category": "Electronics", "subcategory": "Laptops", "sales": 320000 },
  { "category": "Electronics", "subcategory": "Tablets", "sales": 180000 },
  { "category": "Clothing", "subcategory": "Shirts", "sales": 210000 },
  { "category": "Clothing", "subcategory": "Pants", "sales": 175000 },
  { "category": "Home", "subcategory": "Furniture", "sales": 280000 },
  { "category": "Home", "subcategory": "Decor", "sales": 95000 }
]
```

## DataMapping Configuration

For treemaps, use `group_by` and `value`:

```json
{
  "data_mapping": {
    "group_by": "subcategory",
    "value": "sales"
  }
}
```

For hierarchical treemaps:

```json
{
  "data_mapping": {
    "row": "category",
    "group_by": "subcategory",
    "value": "sales"
  }
}
```

| Field | Purpose |
|-------|---------|
| `row` | Parent level in hierarchy (optional) |
| `group_by` | Field that defines rectangles |
| `value` | Field containing the numeric value for rectangle size |

## Element Inventory

| Element | Handled By | Notes |
|---------|------------|-------|
| Rectangle colors | UI (from `sentiment` or categorical) | Groups get distinct colors |
| Rectangle opacity | UI (from `prominence`) | Callout > primary > secondary |
| Labels | UI style guide | Category names |
| Parent labels | UI style guide | Hierarchy levels |
| Color legend | UI style guide | If color encodes meaning |
| Title | UI style guide | Primary prominence |

## DataSeries Patterns

### Single Level (Flat Treemap)

When showing simple composition:

```json
{
  "chart_type": "treemap",
  "data_mapping": {
    "group_by": "subcategory",
    "value": "sales"
  },
  "data_series": [
    {
      "series_id": "phones",
      "group_value": "Phones",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Phones"
    },
    {
      "series_id": "laptops",
      "group_value": "Laptops",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Laptops"
    },
    {
      "series_id": "tablets",
      "group_value": "Tablets",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Tablets"
    },
    {
      "series_id": "furniture",
      "group_value": "Furniture",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Furniture"
    }
  ]
}
```

### With Highlighted Category

When one category is the focus:

```json
{
  "chart_type": "treemap",
  "data_mapping": {
    "group_by": "subcategory",
    "value": "sales"
  },
  "data_series": [
    {
      "series_id": "phones",
      "group_value": "Phones",
      "prominence": "callout",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "Phones (Top Seller)"
    },
    {
      "series_id": "laptops",
      "group_value": "Laptops",
      "prominence": "secondary",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Laptops"
    },
    {
      "series_id": "tablets",
      "group_value": "Tablets",
      "prominence": "secondary",
      "purpose": "data-comparison",
      "sentiment": "neutral",
      "label": "Tablets"
    }
  ]
}
```

### With Performance Sentiment

When rectangles have evaluative meaning:

```json
{
  "chart_type": "treemap",
  "data_mapping": {
    "group_by": "product",
    "value": "profit"
  },
  "data_series": [
    {
      "series_id": "product_a",
      "group_value": "Product A",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "Product A (Profitable)"
    },
    {
      "series_id": "product_b",
      "group_value": "Product B",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "positive",
      "label": "Product B (Profitable)"
    },
    {
      "series_id": "product_c",
      "group_value": "Product C",
      "prominence": "callout",
      "purpose": "data-focus",
      "sentiment": "negative",
      "label": "Product C (Loss)"
    }
  ]
}
```

### Hierarchical Treemap

When showing nested categories:

```json
{
  "chart_type": "treemap",
  "data_mapping": {
    "row": "category",
    "group_by": "subcategory",
    "value": "sales"
  },
  "data_series": [
    {
      "series_id": "electronics",
      "group_value": "Electronics",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Electronics"
    },
    {
      "series_id": "clothing",
      "group_value": "Clothing",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Clothing"
    },
    {
      "series_id": "home",
      "group_value": "Home",
      "prominence": "primary",
      "purpose": "data-focus",
      "sentiment": "neutral",
      "label": "Home"
    }
  ]
}
```

**Note**: For hierarchical treemaps, `data_series` can classify at the parent level, with child rectangles inheriting the parent's styling.

## Gestalt Applications

### Enclosure

**Treemap application**: Nested rectangles show hierarchy through enclosure. Parent contains children.

### Proximity

**Treemap application**: Rectangles within the same parent are adjacent, creating visual grouping.

### Similarity

**Treemap application**: Color can group related items across different parents.

## Common Structural Corrections

| Issue | Correction | Rationale |
|-------|------------|-----------|
| Labels don't fit | Use tooltips for small rectangles | Readability |
| Too many nesting levels | Limit to 2-3 levels | Comprehension |
| No color meaning | Use categorical or sentiment | Add information |
| Thin rectangles | Combine small values | Readability |

## Decluttering Checklist

- [ ] Each rectangle has `group_value` matching data?
- [ ] Sentiment reflects business meaning (profit/loss)?
- [ ] Labels provided for display?
- [ ] Small categories combined or at `secondary` prominence?
- [ ] Hierarchy limited to 2-3 levels?

## See Also

- [Refinement Interface](./refinement.md)
- [Agent-UI Handoff](../03-agent-ui-handoff.md) — Agent vs UI responsibilities
