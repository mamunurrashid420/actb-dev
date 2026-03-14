---
type: worked-example
example-id: product-comparison
scenario: Product performance comparison
charts: [bar_chart_grouped, scatter_plot]
tags: [example, walkthrough, comparison, analysis]
---

# Worked Example: Product Comparison Analysis

A walkthrough showing how to choose between grouped bars and scatter plots.

## Scenario

**User Request**: "Compare our products' performance - I want to see revenue vs. units sold, and also how each product performs against its target."

**Data Available**:
```json
{
  "products": [
    { "name": "Alpha", "revenue": 450000, "units": 1200, "target": 400000 },
    { "name": "Beta", "revenue": 320000, "units": 2800, "target": 350000 },
    { "name": "Gamma", "revenue": 280000, "units": 950, "target": 300000 },
    { "name": "Delta", "revenue": 520000, "units": 1800, "target": 500000 }
  ]
}
```

---

## Step 1: Selection

### Analysis

The request has two parts:
1. **"Revenue vs. units sold"** → Relationship between two measures → **Scatter Plot**
2. **"Each product against its target"** → Actual vs. target comparison → **Grouped Bar Chart**

### Selection Output

```json
{
  "selections": [
    {
      "id": "revenue-units-relationship",
      "chartType": "scatter_plot",
      "rationale": "Shows relationship between two continuous measures (revenue, units)",
      "mapping": {
        "x": "units",
        "y": "revenue",
        "label": "name"
      }
    },
    {
      "id": "actual-vs-target",
      "chartType": "bar_chart_grouped",
      "rationale": "Direct comparison of actual vs target for each product",
      "mapping": {
        "category": "name",
        "groups": ["revenue", "target"]
      }
    }
  ]
}
```

---

## Step 2: Refinement

### Scatter Plot Refinement

**Element Classification**:
```json
{
  "chartId": "revenue-units-relationship",
  "elementClassifications": {
    "chartBorder": { "prominence": "hide", "purpose": "structural" },
    "gridlines": { "prominence": "background", "purpose": "structural" },
    "xAxisLine": { "prominence": "baseline", "purpose": "structural" },
    "yAxisLine": { "prominence": "baseline", "purpose": "structural" },
    "xAxisTitle": { "prominence": "baseline", "purpose": "navigational" },
    "yAxisTitle": { "prominence": "baseline", "purpose": "navigational" },
    "dataPoints_all": { 
      "prominence": "primary", 
      "purpose": "data-focus", 
      "sentiment": "neutral"
    },
    "pointLabels": { 
      "prominence": "secondary", 
      "purpose": "annotation" 
    },
    "title": { "prominence": "primary", "purpose": "navigational" }
  }
}
```

### Grouped Bar Refinement

**Element Classification**:
```json
{
  "chartId": "actual-vs-target",
  "elementClassifications": {
    "chartBorder": { "prominence": "hide", "purpose": "structural" },
    "gridlines": { "prominence": "hide", "purpose": "structural" },
    "xAxisLine": { "prominence": "baseline", "purpose": "structural" },
    "bars_actual_aboveTarget": { 
      "prominence": "primary", 
      "purpose": "data-focus", 
      "sentiment": "positive"
    },
    "bars_actual_belowTarget": { 
      "prominence": "primary", 
      "purpose": "data-focus", 
      "sentiment": "negative"
    },
    "bars_target": { 
      "prominence": "secondary", 
      "purpose": "reference", 
      "sentiment": "neutral"
    },
    "legend": { "prominence": "baseline", "purpose": "navigational" },
    "title": { "prominence": "primary", "purpose": "navigational" }
  }
}
```

**Rationale**: Actual bars colored by whether they beat target (Alpha, Delta = positive; Beta, Gamma = negative).

---

## Step 3: Formatting

### Scatter Plot Formatting

```json
{
  "chartId": "revenue-units-relationship",
  "formattedSpec": {
    "elements": {
      "dataPoints": {
        "r": 8,
        "fill": "#3b82f6",
        "fillOpacity": 0.7,
        "stroke": "#ffffff",
        "strokeWidth": 2
      },
      "pointLabels": {
        "fontSize": 11,
        "fontWeight": 500,
        "fill": "#1a1a1a",
        "offset": 12
      },
      "gridlines": {
        "stroke": "#e5e7eb",
        "strokeWidth": 0.5,
        "opacity": 0.5
      },
      "axisTitle": {
        "fontSize": 12,
        "fontWeight": 500,
        "fill": "#333333"
      }
    }
  }
}
```

### Grouped Bar Formatting

```json
{
  "chartId": "actual-vs-target",
  "formattedSpec": {
    "elements": {
      "bars_actual_positive": {
        "fill": "#22c55e"
      },
      "bars_actual_negative": {
        "fill": "#ef4444"
      },
      "bars_target": {
        "fill": "#d1d5db"
      }
    },
    "layout": {
      "barCategoryGap": "25%",
      "barGap": 4
    }
  }
}
```

---

## Step 4: Implementation

### Scatter Plot (Recharts)

```tsx
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Label } from 'recharts';

const data = [
  { name: 'Alpha', units: 1200, revenue: 450000 },
  { name: 'Beta', units: 2800, revenue: 320000 },
  { name: 'Gamma', units: 950, revenue: 280000 },
  { name: 'Delta', units: 1800, revenue: 520000 },
];

function RevenueUnitsScatter() {
  return (
    <div>
      <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>
        Revenue vs. Units Sold
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 20, right: 20, bottom: 50, left: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" opacity={0.5} />
          <XAxis 
            type="number" 
            dataKey="units" 
            name="Units"
            tick={{ fontSize: 12, fill: '#666666' }}
          >
            <Label value="Units Sold" offset={-10} position="insideBottom" style={{ fontSize: 12, fill: '#333333' }} />
          </XAxis>
          <YAxis 
            type="number" 
            dataKey="revenue" 
            name="Revenue"
            tick={{ fontSize: 12, fill: '#666666' }}
            tickFormatter={(v) => `$${(v / 1000)}K`}
          >
            <Label value="Revenue" angle={-90} position="insideLeft" style={{ fontSize: 12, fill: '#333333' }} />
          </YAxis>
          <Tooltip 
            formatter={(value, name) => [
              name === 'revenue' ? `$${value.toLocaleString()}` : value,
              name === 'revenue' ? 'Revenue' : 'Units'
            ]}
          />
          <Scatter 
            data={data} 
            fill="#3b82f6" 
            fillOpacity={0.7}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
```

### Grouped Bar with Sentiment (Recharts)

```tsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';

const data = [
  { name: 'Alpha', actual: 450000, target: 400000 },
  { name: 'Beta', actual: 320000, target: 350000 },
  { name: 'Gamma', actual: 280000, target: 300000 },
  { name: 'Delta', actual: 520000, target: 500000 },
];

function ActualVsTargetChart() {
  return (
    <div>
      <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>
        Actual vs. Target Revenue
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart 
          data={data} 
          margin={{ top: 20, right: 30, bottom: 20, left: 60 }}
          barCategoryGap="25%"
          barGap={4}
        >
          <XAxis 
            dataKey="name" 
            axisLine={{ stroke: '#d1d5db' }}
            tickLine={false}
            tick={{ fontSize: 12, fill: '#666666' }}
          />
          <YAxis 
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 12, fill: '#666666' }}
            tickFormatter={(v) => `$${(v / 1000)}K`}
          />
          <Tooltip formatter={(v) => `$${v.toLocaleString()}`} />
          <Legend />
          <Bar dataKey="actual" name="Actual" radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => (
              <Cell 
                key={`cell-${index}`}
                fill={entry.actual >= entry.target ? '#22c55e' : '#ef4444'}
              />
            ))}
          </Bar>
          <Bar dataKey="target" name="Target" fill="#d1d5db" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

---

## Key Decisions

| Question | Answer | Rationale |
|----------|--------|-----------|
| Why scatter for revenue vs. units? | Both are continuous measures | Scatter shows relationship between two numeric variables |
| Why grouped bar for actual vs. target? | Need side-by-side comparison | Grouped bars allow direct comparison at each category |
| Why color actual bars by performance? | Adds semantic meaning | Green = beat target, Red = missed target |
| Why is target bar gray? | It's reference, not data-focus | Secondary prominence, not competing with actual |

---

## Final Insight

The scatter plot reveals that **higher unit volume doesn't always mean higher revenue** (Beta has most units but lower revenue than Alpha/Delta). The grouped bar shows that **Alpha and Delta exceeded targets** while **Beta and Gamma fell short**.
