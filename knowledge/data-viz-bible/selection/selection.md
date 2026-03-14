---
type: action-interface
action: selection
tags: [selection, decision-tree, data-patterns, chart-selection, intent]
---

# Selection

The Selection action determines which chart type best represents the given data and user intent.

## Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `dataSchema` | Schema | Yes | Field definitions with roles (DIMENSION, MEASURE, TEMPORAL) |
| `rowCount` | Integer | Yes | Number of data rows |
| `userIntent` | String | Yes | Natural language description of what user wants to show |
| `constraints` | Object | No | Available libraries, space constraints, accessibility requirements |

### Input Example

```json
{
  "dataSchema": {
    "fields": [
      { "name": "month", "role": "TEMPORAL", "type": "DATE" },
      { "name": "revenue", "role": "MEASURE", "type": "FLOAT" },
      { "name": "region", "role": "DIMENSION", "type": "STRING", "cardinality": 4 }
    ]
  },
  "rowCount": 48,
  "userIntent": "Show revenue trends by region over the past 4 years",
  "constraints": {
    "libraries": ["recharts", "d3"],
    "maxWidth": 800
  }
}
```

## Output

| Field | Type | Description |
|-------|------|-------------|
| `chartType` | String | Selected chart type ID |
| `rationale` | String | Explanation of why this chart was selected |
| `alternatives` | Array | Other viable chart types with trade-offs |
| `dataMapping` | Object | How schema fields map to chart dimensions |
| `warnings` | Array | Potential issues or considerations |

### Output Example

```json
{
  "chartType": "line_chart",
  "rationale": "Temporal data with multiple categories (regions) is best shown as multi-line chart to reveal trends over time and enable comparison between regions",
  "alternatives": [
    {
      "chartType": "area_chart",
      "tradeoff": "Emphasizes cumulative magnitude; may obscure individual series if stacked"
    },
    {
      "chartType": "bar_chart_grouped",
      "tradeoff": "Better for discrete period comparisons; loses trend continuity"
    }
  ],
  "dataMapping": {
    "xAxis": "month",
    "yAxis": "revenue",
    "series": "region"
  },
  "warnings": [
    "4 series is manageable; more than 5 would require highlighting strategy"
  ]
}
```

## Process

### Step 1: Analyze Data Pattern

Count and classify schema fields:

```
dimensions = COUNT(fields WHERE role = DIMENSION)
measures = COUNT(fields WHERE role = MEASURE)
hasTemporal = EXISTS(fields WHERE role = TEMPORAL)
```

Map to pattern code:
- `0D-1M-1row` → Single value
- `1D-1M` → Categorical comparison
- `0D-1M-TEMPORAL` → Time series
- `1D-1M-TEMPORAL` → Categorical time series
- `2D-1M` → Two-dimensional categorical
- `0D-2M` → Correlation
- etc.

### Step 2: Apply Selection Decision Tree

```
START
│
├─ rowCount == 1?
│  ├─ YES: measures == 1? → KPI Card
│  │        measures == 2? → KPI Card with comparison
│  └─ NO: continue
│
├─ hasTemporal?
│  ├─ YES: dimensions == 0?
│  │       ├─ YES → Line Chart (single series)
│  │       └─ NO → Line Chart (multi-series) or Area Chart
│  └─ NO: continue
│
├─ dimensions == 1 AND measures == 1?
│  ├─ rowCount <= 6? → Bar Chart or Pie Chart
│  ├─ rowCount <= 15? → Bar Chart (horizontal for ranking)
│  └─ rowCount > 15? → Table or Treemap
│
├─ dimensions == 2 AND measures == 1?
│  ├─ Grid pattern? → Heatmap
│  └─ Otherwise → Grouped Bar or Stacked Bar
│
├─ dimensions == 0 AND measures == 2?
│  └─ Scatter Plot (or Bubble if 3rd measure)
│
├─ dimensions == 1 AND measures == 2?
│  └─ Slope Chart or Dumbbell
│
└─ Complex pattern?
   └─ Data Table (universal fallback)
```

### Step 3: Consider User Intent

Adjust selection based on intent signals:

| Intent Signal | Suggests | Chart Types |
|---------------|----------|-------------|
| "trend", "over time", "change", "growth" | Temporal analysis | Line, Area, Timeseries |
| "compare", "versus", "difference" | Comparison | Bar, Grouped Bar, Slope |
| "rank", "top", "bottom", "best", "worst" | Ranking | Horizontal Bar, Lollipop |
| "distribution", "spread", "range" | Distribution | Histogram, Boxplot |
| "relationship", "correlation", "versus" (2 measures) | Correlation | Scatter, Bubble |
| "composition", "breakdown", "share", "percent" | Part-to-whole | Pie, Treemap, Stacked Bar |
| "flow", "change breakdown", "waterfall" | Sequential change | Waterfall |

### Step 4: Apply Constraints

Check selection against constraints:
- Library availability
- Space limitations (prefer horizontal bar for narrow widths)
- Accessibility requirements (avoid pie charts if color-blind support critical)

### Step 5: Identify Alternatives

For every selection, identify 1-2 alternatives with trade-offs. This helps downstream refinement if the primary choice has issues.

## Handoff to Refinement

Pass to the Refinement action:

```json
{
  "chartType": "line_chart",
  "dataMapping": {
    "xAxis": "month",
    "yAxis": "revenue",
    "series": "region"
  },
  "userIntent": "Show revenue trends by region over the past 4 years",
  "insights": []  // Optional: pre-identified insights to highlight
}
```

---

## Cross-Cutting Principles for Selection

### Gestalt Principles in Selection

**Proximity**: When data has natural groupings, consider charts that leverage spatial proximity (grouped bars, small multiples).

**Similarity**: When categories need distinction, ensure the selected chart supports color/shape encoding (scatter with color groups, multi-line with distinct colors).

**Continuity**: For sequential or ordered data, prefer charts that show continuity (line charts over bar charts for time series).

**Connection**: When relationships between points matter, use connected forms (lines, flows) rather than discrete marks.

### Simplicity Principle

Prefer simpler chart types when they adequately convey the message:
- Don't use a bubble chart when a scatter plot suffices
- Don't use a stacked area when a simple line works
- Don't use a pie chart when a single number or bar would do

### Data-Ink Ratio Consideration

Consider how much "chart overhead" each type requires:
- KPI Card: Minimal overhead, maximum data focus
- Bar Chart: Low overhead
- Line Chart: Low overhead
- Pie Chart: Moderate overhead (legends, labels)
- Bubble Chart: Higher overhead (size legend, potential overlap)

---

## Selection Anti-Patterns

### Using Line Charts for Categorical Data

**Problem**: Lines imply continuity between points. Connecting "Apples" to "Oranges" with a line suggests interpolation that doesn't exist.

**Solution**: Use bar charts for categorical data.

### Using Pie Charts for Too Many Categories

**Problem**: Humans are poor at comparing angles. More than 5-6 slices become unreadable.

**Solution**: Use bar charts for 6+ categories, or group small categories into "Other".

### Using 3D Charts

**Problem**: 3D effects distort perception and add no information.

**Solution**: Never select 3D variants. Always use 2D.

### Dual Y-Axes

**Problem**: Two scales on one chart often mislead; easy to manipulate visual correlation.

**Solution**: Use separate charts, or ensure scales are clearly labeled and start at appropriate values.

### Truncated Axes Without Indication

**Problem**: Not starting Y-axis at zero can exaggerate differences.

**Solution**: Either start at zero, or clearly indicate truncation. Consider whether the exaggeration serves understanding.

---

## Chart Type Quick Reference

### For Single Values
- **KPI Card**: Best for 1-2 headline numbers

### For Comparisons
- **Bar (Vertical)**: Categorical comparison, few categories
- **Bar (Horizontal)**: Rankings, long category names
- **Lollipop**: Cleaner alternative to bar for sparse data

### For Trends
- **Line Chart**: Change over continuous interval
- **Area Chart**: Magnitude emphasis over time
- **Slope Chart**: Two-point comparison

### For Distributions
- **Histogram**: Single variable distribution
- **Boxplot**: Distribution comparison across categories

### For Relationships
- **Scatter Plot**: Two-variable correlation
- **Bubble Chart**: Three-variable correlation

### For Part-to-Whole
- **Pie/Donut**: Simple composition (≤6 parts)
- **Treemap**: Hierarchical composition
- **Stacked Bar**: Composition over categories/time

### For Complex Data
- **Heatmap**: Two-dimensional patterns
- **Data Table**: Universal fallback, many dimensions

---

## Chart-Specific Documents

For detailed selection criteria per chart type, see:

| Chart Type | Selection Document |
|------------|-------------------|
| KPI Card | [selection-kpi-card.md](./selection-kpi-card.md) |
| Data Table | [selection-data-table.md](./selection-data-table.md) |
| Bar Chart (Vertical) | [selection-bar-chart-vertical.md](./selection-bar-chart-vertical.md) |
| Bar Chart (Horizontal) | [selection-bar-chart-horizontal.md](./selection-bar-chart-horizontal.md) |
| Bar Chart (Stacked) | [selection-bar-chart-stacked.md](./selection-bar-chart-stacked.md) |
| Bar Chart (Grouped) | [selection-bar-chart-grouped.md](./selection-bar-chart-grouped.md) |
| Line Chart | [selection-line-chart.md](./selection-line-chart.md) |
| Area Chart | [selection-area-chart.md](./selection-area-chart.md) |
| Scatter Plot | [selection-scatter-plot.md](./selection-scatter-plot.md) |
| Pie/Donut Chart | [selection-pie-donut-chart.md](./selection-pie-donut-chart.md) |
| Histogram | [selection-histogram.md](./selection-histogram.md) |
| Heatmap | [selection-heatmap.md](./selection-heatmap.md) |
| Treemap | [selection-treemap.md](./selection-treemap.md) |

---

## See Also

- [Schema Reference](../01-schema-reference.md) — Field roles and data patterns
- [Refinement Interface](../refinement/refinement.md) — Next step in pipeline
