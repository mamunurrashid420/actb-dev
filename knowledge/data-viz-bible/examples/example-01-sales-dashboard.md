---
type: worked-example
example-id: sales-dashboard-kpi
scenario: Executive sales dashboard
charts: [kpi_card, line_chart, bar_chart_horizontal]
tags: [example, walkthrough, dashboard, sales]
---

# Worked Example: Sales Dashboard KPIs

A complete walkthrough from user request to implementation.

## Scenario

**User Request**: "Show me our sales performance this quarter with key metrics and trends."

**Data Available**:
```json
{
  "summary": {
    "totalRevenue": 2450000,
    "previousQuarter": 2180000,
    "target": 2500000,
    "dealsClosed": 156,
    "avgDealSize": 15705
  },
  "monthlyTrend": [
    { "month": "Oct", "revenue": 720000 },
    { "month": "Nov", "revenue": 850000 },
    { "month": "Dec", "revenue": 880000 }
  ],
  "topProducts": [
    { "product": "Enterprise Suite", "revenue": 890000 },
    { "product": "Professional", "revenue": 650000 },
    { "product": "Starter", "revenue": 480000 },
    { "product": "Add-ons", "revenue": 430000 }
  ]
}
```

---

## Step 1: Selection

### Analysis

| Data Element | Pattern | Recommended Chart |
|--------------|---------|-------------------|
| Total Revenue (single number) | 0D + 1M | **KPI Card** |
| Monthly Trend (time series) | Temporal + 1M | **Line Chart** |
| Top Products (ranking) | 1D + 1M, sorted | **Horizontal Bar** |

### Selection Output

```json
{
  "selections": [
    {
      "id": "revenue-kpi",
      "chartType": "kpi_card",
      "rationale": "Single headline metric with comparison to previous period",
      "data": {
        "value": 2450000,
        "comparison": 2180000,
        "target": 2500000
      }
    },
    {
      "id": "revenue-trend",
      "chartType": "line_chart",
      "rationale": "Shows temporal trend over 3 months",
      "data": "monthlyTrend"
    },
    {
      "id": "product-ranking",
      "chartType": "bar_chart_horizontal",
      "rationale": "Ranking of products, sorted by value",
      "data": "topProducts"
    }
  ]
}
```

---

## Step 2: Refinement

### KPI Card Refinement

**Element Classification**:
```json
{
  "chartId": "revenue-kpi",
  "elementClassifications": {
    "value": { 
      "prominence": "callout", 
      "purpose": "data-focus", 
      "sentiment": "positive"
    },
    "label": { 
      "prominence": "secondary", 
      "purpose": "navigational" 
    },
    "delta": { 
      "prominence": "secondary", 
      "purpose": "annotation", 
      "sentiment": "positive"
    },
    "deltaLabel": { 
      "prominence": "baseline", 
      "purpose": "annotation" 
    }
  }
}
```

**Rationale**: Revenue is up 12.4% vs previous quarter → positive sentiment.

### Line Chart Refinement

**Element Classification**:
```json
{
  "chartId": "revenue-trend",
  "elementClassifications": {
    "chartBorder": { "prominence": "hide", "purpose": "structural" },
    "gridlines": { "prominence": "hide", "purpose": "structural" },
    "xAxisLine": { "prominence": "baseline", "purpose": "structural" },
    "yAxisLine": { "prominence": "hide", "purpose": "structural" },
    "line_revenue": { 
      "prominence": "primary", 
      "purpose": "data-focus", 
      "sentiment": "positive"
    },
    "dataMarkers": { "prominence": "secondary", "purpose": "data-focus" },
    "title": { "prominence": "primary", "purpose": "navigational" }
  },
  "structuralCorrections": []
}
```

**Rationale**: Single series showing upward trend → positive sentiment. No corrections needed.

### Horizontal Bar Refinement

**Element Classification**:
```json
{
  "chartId": "product-ranking",
  "elementClassifications": {
    "chartBorder": { "prominence": "hide", "purpose": "structural" },
    "gridlines": { "prominence": "hide", "purpose": "structural" },
    "bars_all": { 
      "prominence": "primary", 
      "purpose": "data-focus", 
      "sentiment": "neutral"
    },
    "yAxisLabels": { "prominence": "baseline", "purpose": "navigational" },
    "dataLabels": { "prominence": "secondary", "purpose": "annotation" },
    "title": { "prominence": "primary", "purpose": "navigational" }
  },
  "structuralCorrections": [
    {
      "element": "bars",
      "issue": "unsorted",
      "correction": "sort-descending",
      "rationale": "Horizontal bars should be sorted for ranking"
    }
  ]
}
```

---

## Step 3: Formatting

### KPI Card Formatting

```json
{
  "chartId": "revenue-kpi",
  "formattedSpec": {
    "elements": {
      "value": {
        "fontSize": 36,
        "fontWeight": 700,
        "color": "#22c55e"
      },
      "label": {
        "fontSize": 14,
        "fontWeight": 500,
        "color": "#666666"
      },
      "delta": {
        "fontSize": 14,
        "fontWeight": 500,
        "color": "#22c55e",
        "icon": "▲"
      },
      "deltaLabel": {
        "fontSize": 12,
        "color": "#999999"
      }
    }
  }
}
```

### Line Chart Formatting

```json
{
  "chartId": "revenue-trend",
  "formattedSpec": {
    "elements": {
      "line_revenue": {
        "stroke": "#22c55e",
        "strokeWidth": 2.5
      },
      "dataMarkers": {
        "r": 4,
        "fill": "#22c55e",
        "stroke": "#ffffff",
        "strokeWidth": 2
      },
      "xAxisLine": {
        "stroke": "#d1d5db",
        "strokeWidth": 1
      },
      "xAxisLabels": {
        "fontSize": 12,
        "fill": "#666666"
      },
      "title": {
        "fontSize": 16,
        "fontWeight": 600,
        "fill": "#1a1a1a"
      }
    },
    "layout": {
      "margin": { "top": 40, "right": 20, "bottom": 40, "left": 50 }
    }
  }
}
```

### Horizontal Bar Formatting

```json
{
  "chartId": "product-ranking",
  "formattedSpec": {
    "elements": {
      "bars_all": {
        "fill": "#3b82f6",
        "radius": [0, 4, 4, 0]
      },
      "yAxisLabels": {
        "fontSize": 12,
        "fill": "#333333"
      },
      "dataLabels": {
        "fontSize": 11,
        "fontWeight": 500,
        "fill": "#1a1a1a"
      },
      "title": {
        "fontSize": 16,
        "fontWeight": 600,
        "fill": "#1a1a1a"
      }
    },
    "layout": {
      "margin": { "top": 40, "right": 60, "bottom": 20, "left": 120 },
      "barSize": 28
    }
  }
}
```

---

## Step 4: Implementation

### KPI Card (React)

```tsx
import React from 'react';

function RevenueKPI() {
  const value = 2450000;
  const previous = 2180000;
  const delta = ((value - previous) / previous * 100).toFixed(1);
  
  return (
    <div style={{ padding: 20, backgroundColor: '#ffffff', borderRadius: 8 }}>
      <div style={{ fontSize: 14, fontWeight: 500, color: '#666666', marginBottom: 4 }}>
        Total Revenue
      </div>
      <div style={{ fontSize: 36, fontWeight: 700, color: '#22c55e', marginBottom: 8 }}>
        $2.45M
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ fontSize: 14, fontWeight: 500, color: '#22c55e' }}>
          ▲ +{delta}%
        </span>
        <span style={{ fontSize: 12, color: '#999999' }}>
          vs. last quarter
        </span>
      </div>
    </div>
  );
}
```

### Line Chart (Recharts)

```tsx
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const data = [
  { month: 'Oct', revenue: 720000 },
  { month: 'Nov', revenue: 850000 },
  { month: 'Dec', revenue: 880000 },
];

function RevenueTrend() {
  return (
    <div>
      <h3 style={{ fontSize: 16, fontWeight: 600, color: '#1a1a1a', marginBottom: 16 }}>
        Monthly Revenue Trend
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 50 }}>
          <XAxis 
            dataKey="month" 
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
          <Tooltip formatter={(v) => [`$${v.toLocaleString()}`, 'Revenue']} />
          <Line 
            type="monotone" 
            dataKey="revenue" 
            stroke="#22c55e" 
            strokeWidth={2.5}
            dot={{ r: 4, fill: '#22c55e', stroke: '#ffffff', strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

### Horizontal Bar (Recharts)

```tsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LabelList } from 'recharts';

const data = [
  { product: 'Enterprise Suite', revenue: 890000 },
  { product: 'Professional', revenue: 650000 },
  { product: 'Starter', revenue: 480000 },
  { product: 'Add-ons', revenue: 430000 },
];

function ProductRanking() {
  return (
    <div>
      <h3 style={{ fontSize: 16, fontWeight: 600, color: '#1a1a1a', marginBottom: 16 }}>
        Revenue by Product
      </h3>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart 
          data={data} 
          layout="vertical"
          margin={{ top: 10, right: 60, bottom: 10, left: 120 }}
        >
          <XAxis type="number" hide />
          <YAxis 
            type="category" 
            dataKey="product" 
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 12, fill: '#333333' }}
            width={110}
          />
          <Tooltip formatter={(v) => [`$${v.toLocaleString()}`, 'Revenue']} />
          <Bar dataKey="revenue" fill="#3b82f6" radius={[0, 4, 4, 0]} barSize={28}>
            <LabelList 
              dataKey="revenue" 
              position="right"
              formatter={(v) => `$${(v / 1000).toFixed(0)}K`}
              style={{ fontSize: 11, fontWeight: 500, fill: '#1a1a1a' }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

---

## Final Result

The dashboard shows:

1. **KPI Card**: $2.45M revenue with +12.4% growth indicator (green, positive sentiment)
2. **Line Chart**: Upward trend from Oct→Dec (green line, minimal gridlines)
3. **Horizontal Bar**: Products ranked by revenue, largest at top

All visualizations follow the classification system with appropriate prominence and sentiment.
