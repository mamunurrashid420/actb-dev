---
type: action-implementation
action: selection
chart-type: data_table
aliases: [table, data grid, spreadsheet view, tabular data]
data-pattern: multi-dimensional
family: tabular
priority: P0
tags: [selection, table, tabular, lookup, precise-values]
---

# Selection: Data Table

Displays data in rows and columns for precise value lookup and comparison.

## When to Use

- **Precise values needed**: When exact numbers matter more than patterns
- **Multiple attributes per item**: Showing several measures per entity
- **Lookup/reference**: Users need to find specific values
- **Small to medium datasets**: 5-50 rows typically
- **Heterogeneous data types**: Mix of text, numbers, dates

### Data Pattern

- N DIMENSIONS + M MEASURES (flexible)
- Structured rows and columns
- Any row count (with pagination for large sets)

### User Intent Signals

Queries that suggest a data table:
- "Show me the details..."
- "List all..."
- "What are the exact values..."
- "Full breakdown..."
- "Export the data..."

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| Showing trends | Tables don't show patterns | Line Chart |
| Comparing magnitudes | Hard to compare numbers visually | Bar Chart |
| Part-to-whole | No visual encoding | Pie Chart |
| Many rows (100+) | Overwhelming | Aggregated chart + drill-down |
| Single metric | Overkill | KPI Card |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| IDENTIFIER | Yes | Row identifier (name, ID, etc.) |
| DIMENSION | No | Categorical columns |
| MEASURE | No | Numeric columns |
| TEMPORAL | No | Date/time columns |

### Row Count Considerations

- **1-10 rows**: Ideal, all visible
- **10-25 rows**: Good, may need scrolling
- **25-50 rows**: Acceptable with good design
- **50-100 rows**: Consider pagination
- **100+ rows**: Aggregate first, then drill-down

## Selection Decision

```
IF intent == "exact values" OR "lookup" OR "details":
    → Data Table

IF dimensions >= 2 AND measures >= 2:
    AND rowCount <= 50:
    AND NOT intent == "trend" OR "pattern":
        → Data Table

IF allOtherChartsFail:
    → Data Table (fallback)
```

## Alternatives Comparison

| Scenario | Table | Alternative | Recommendation |
|----------|-------|-------------|----------------|
| Exact values needed | ✓ Precise | Charts: Approximate | **Table** |
| Showing trends | Hard to see | Line Chart | **Line Chart** |
| Comparing 5 items | Works | Bar Chart: Visual | **Bar** for comparison, **Table** for detail |
| 100+ rows | Overwhelming | Summary chart | **Chart** first |

## Variants

### Basic Table
Simple rows and columns, minimal styling.

### Table with Bars
Inline bar charts in cells for quick comparison.

### Heatmap Table
Cell background color encodes values.

### Sortable/Filterable Table
Interactive sorting and filtering.

### Hierarchical Table
Expandable row groups.

## Critical Rules

> **Tables are for precision, not patterns.**

If the goal is to see trends or compare magnitudes visually, use a chart.

> **Keep column count manageable.**

More than 6-8 columns becomes hard to scan. Consider which columns are essential.

> **Align numbers right.**

Numeric columns should be right-aligned for easy comparison of digit positions.

## See Also

- [Selection Interface](./selection.md)
- [KPI Card](./selection-kpi-card.md) — For single metrics
- [Bar Chart](./selection-bar-chart-vertical.md) — For visual comparison
