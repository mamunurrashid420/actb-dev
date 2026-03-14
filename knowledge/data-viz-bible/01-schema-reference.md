---
type: reference
category: schema
tags: [schema, field-roles, data-types, measures, dimensions, temporal, data-patterns]
---

# Schema Reference

This document defines the field roles used to classify data columns and the patterns for matching data shapes to visualizations.

## Field Roles

Every field in a data schema is assigned one of the following roles:

### IDENTIFIER

- **Definition**: Unique row key, primary key, or record ID
- **Purpose**: Identifies individual records
- **Visualization Use**: Not typically visualized directly; used for row keys in tables
- **Examples**: `row_id`, `order_id`, `customer_id`, `uuid`
- **Detection Hints**: Column name contains "id", "key", "uuid"; values are unique per row

### DIMENSION

- **Definition**: Categorical grouping variable
- **Purpose**: Segments data into groups for comparison
- **Visualization Use**: X-axis categories, legend groups, facets, table columns
- **Examples**: `product_category`, `region`, `department`, `status`, `customer_segment`
- **Detection Hints**: String type with repeated values; limited distinct values relative to row count

### MEASURE

- **Definition**: Numeric value to aggregate, calculate, or display
- **Purpose**: The quantitative data being visualized
- **Visualization Use**: Y-axis values, bar heights, point positions, color intensity, bubble size
- **Examples**: `sales_amount`, `quantity`, `revenue`, `percentage`, `count`, `price`
- **Detection Hints**: Numeric type (INT, FLOAT, DECIMAL); meaningful to sum/average

### TEMPORAL

- **Definition**: Date, time, or datetime field
- **Purpose**: Represents time-based data for trend analysis
- **Visualization Use**: Time axis (X-axis for time series), period comparisons
- **Examples**: `order_date`, `created_at`, `month`, `fiscal_quarter`, `year`
- **Detection Hints**: Date/datetime type; column name contains "date", "time", "period"

### GEOGRAPHIC

- **Definition**: Location-based field
- **Purpose**: Represents spatial data for maps
- **Visualization Use**: Map regions, coordinates, location markers
- **Examples**: `country`, `state`, `zip_code`, `latitude`, `longitude`
- **Detection Hints**: Known geographic terms; coordinate patterns

## Data Pattern Syntax

Patterns are expressed as: `{D}D + {M}M + [TEMPORAL] + [row count]`

Where:
- `D` = Number of DIMENSION fields
- `M` = Number of MEASURE fields
- `TEMPORAL` = Presence of time dimension
- Row count = Approximate number of rows

## Core Data Patterns

| Pattern | Description | Primary Chart Types | Alternative Chart Types |
|---------|-------------|---------------------|------------------------|
| `0D + 1M (1 row)` | Single aggregate value | KPI Card | — |
| `0D + 2M (1 row)` | Value with comparison/delta | KPI Card with delta | — |
| `1D + 1M (few rows)` | Categorical comparison (<15 categories) | Bar (V/H), Lollipop | Pie/Donut (if ≤6) |
| `1D + 1M (many rows)` | Large categorical set (15+ categories) | Data Table, Treemap | Horizontal Bar (top N) |
| `0D + 1M + TEMPORAL` | Single metric over time | Line Chart, Area Chart | Timeseries |
| `1D + 1M + TEMPORAL` | Category over time | Multi-line, Stacked Area | Grouped Bar |
| `2D + 1M (grid)` | Two-dimensional categorical | Heatmap | Grouped Bar |
| `0D + 2M (many rows)` | Two numeric variables | Scatter Plot | Bubble (with 3rd measure) |
| `1D + 2M` | Before/after or paired values | Slope Chart | Dumbbell, Grouped Bar |
| `0D + 1M (distribution)` | Single measure distribution | Histogram, Boxplot | — |
| `1D + 1M (hierarchical)` | Part-to-whole with hierarchy | Treemap | Pie/Donut (flat) |
| `Complex` | Many dimensions/measures | Data Table | — |

## Pattern Detection Logic

```
FUNCTION detectPattern(schema, rowCount):
    
    dimensions = fields WHERE role = DIMENSION
    measures = fields WHERE role = MEASURE
    temporal = fields WHERE role = TEMPORAL
    
    # Single value patterns
    IF rowCount == 1:
        IF measures.count == 1 AND dimensions.count == 0:
            RETURN "0D-1M-single" → KPI Card
        IF measures.count == 2 AND dimensions.count == 0:
            RETURN "0D-2M-single" → KPI Card with comparison
    
    # Time-based patterns
    IF temporal.count > 0:
        IF dimensions.count == 0 AND measures.count == 1:
            RETURN "temporal-single-measure" → Line Chart
        IF dimensions.count == 1 AND measures.count == 1:
            RETURN "temporal-categorical" → Multi-line Chart
    
    # Categorical patterns
    IF dimensions.count == 1 AND measures.count == 1:
        IF rowCount <= 6:
            RETURN "categorical-few" → Bar or Pie
        IF rowCount <= 15:
            RETURN "categorical-moderate" → Bar Chart
        ELSE:
            RETURN "categorical-many" → Table or Treemap
    
    # Correlation patterns
    IF dimensions.count == 0 AND measures.count == 2:
        RETURN "correlation" → Scatter Plot
    IF dimensions.count == 0 AND measures.count == 3:
        RETURN "correlation-sized" → Bubble Chart
    
    # Grid patterns
    IF dimensions.count == 2 AND measures.count == 1:
        IF isGridPattern(data):
            RETURN "grid" → Heatmap
        ELSE:
            RETURN "two-categorical" → Grouped Bar
    
    # Distribution patterns
    IF detectDistributionIntent(userIntent):
        RETURN "distribution" → Histogram or Boxplot
    
    # Fallback
    RETURN "complex" → Data Table
```

## Schema to Chart Mapping

### Bar Chart Mapping

| Schema Role | Chart Property |
|-------------|----------------|
| DIMENSION | X-axis category labels |
| MEASURE | Bar height (Y-axis value) |
| DIMENSION (2nd) | Grouping/stacking variable |

### Line Chart Mapping

| Schema Role | Chart Property |
|-------------|----------------|
| TEMPORAL | X-axis values |
| MEASURE | Y-axis line values |
| DIMENSION | Series grouping (multiple lines) |

### Scatter Plot Mapping

| Schema Role | Chart Property |
|-------------|----------------|
| MEASURE (1st) | X-axis position |
| MEASURE (2nd) | Y-axis position |
| MEASURE (3rd) | Point size (bubble) |
| DIMENSION | Point color/shape grouping |

### Heatmap Mapping

| Schema Role | Chart Property |
|-------------|----------------|
| DIMENSION (1st) | Row categories |
| DIMENSION (2nd) | Column categories |
| MEASURE | Cell color intensity |

### Table Mapping

| Schema Role | Chart Property |
|-------------|----------------|
| IDENTIFIER | Row key |
| DIMENSION | Text column |
| MEASURE | Numeric column (with formatting) |
| TEMPORAL | Date column (with formatting) |

## Example Schema

```json
{
  "fields": [
    {
      "name": "order_id",
      "type": "STRING",
      "role": "IDENTIFIER"
    },
    {
      "name": "product_category",
      "type": "STRING",
      "role": "DIMENSION",
      "cardinality": 8
    },
    {
      "name": "region",
      "type": "STRING",
      "role": "DIMENSION",
      "cardinality": 4
    },
    {
      "name": "order_date",
      "type": "DATE",
      "role": "TEMPORAL"
    },
    {
      "name": "sales_amount",
      "type": "FLOAT",
      "role": "MEASURE"
    },
    {
      "name": "quantity",
      "type": "INTEGER",
      "role": "MEASURE"
    }
  ],
  "rowCount": 1250
}
```

**Pattern Analysis**:
- 2 DIMENSIONS + 2 MEASURES + TEMPORAL
- Multiple valid visualizations depending on intent:
  - "Sales over time" → Line Chart (temporal + 1 measure)
  - "Sales by category" → Bar Chart (1 dimension + 1 measure)
  - "Sales by region and category" → Heatmap or Grouped Bar (2 dimensions + 1 measure)
  - "Sales vs quantity correlation" → Scatter Plot (2 measures)

## See Also

- [Selection Interface](./selection/selection.md) — How to use patterns for chart selection
- [Classification System](./02-classification-system.md) — How to classify chart elements
