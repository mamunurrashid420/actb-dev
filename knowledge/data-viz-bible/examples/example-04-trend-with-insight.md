---
type: worked-example
example-id: trend-with-insight
scenario: Marketing channel performance with insight callout
charts: [line_chart]
tags: [example, walkthrough, trend, multi-series, annotation, insight]
---

# Worked Example: Marketing Trend with Insight Callout

A walkthrough demonstrating the classification system for multi-series data with insight annotations.

## Scenario

**User Request**: "Show me our marketing channel performance over the last 6 months. I want to highlight that paid search overtook organic in October."

**Data Available**:
```json
{
  "channelData": [
    { "month": "Jul", "organic": 45000, "paid": 32000, "email": 18000 },
    { "month": "Aug", "organic": 48000, "paid": 38000, "email": 19000 },
    { "month": "Sep", "organic": 47000, "paid": 44000, "email": 20000 },
    { "month": "Oct", "organic": 46000, "paid": 52000, "email": 21000 },
    { "month": "Nov", "organic": 44000, "paid": 58000, "email": 22000 },
    { "month": "Dec", "organic": 43000, "paid": 65000, "email": 23000 }
  ],
  "insight": {
    "title": "Paid Search Overtakes Organic",
    "description": "October marked the crossover point where paid search became our #1 channel",
    "anchorPoint": { "month": "Oct", "series": "paid" }
  }
}
```

---

## Step 1: Selection

### Analysis

| Characteristic | Value |
|----------------|-------|
| Data type | Time series |
| Measures | 3 (organic, paid, email) |
| Intent | Show trends + highlight specific insight |
| Time points | 6 months |

**Recommendation**: **Line Chart** with multi-series and annotation

### Selection Output

```json
{
  "selection": {
    "id": "channel-performance",
    "chartType": "line_chart",
    "variant": "multi-series",
    "rationale": "Time series with multiple measures, need to show trends and crossover point",
    "mapping": {
      "x": "month",
      "lines": ["organic", "paid", "email"],
      "annotation": "insight"
    }
  }
}
```

---

## Step 2: Refinement

This is the most interesting step—we need to apply **hawk-in-pigeons** and **cognitive anchoring**.

### Classification Strategy

The user wants to highlight paid search. This means:
- **Paid search**: Primary focus (callout at insight point)
- **Organic**: Secondary comparison (it's part of the story)
- **Email**: Baseline context (not part of the main narrative)

### Element Classification

```json
{
  "chartId": "channel-performance",
  "elementClassifications": {
    "chartBorder": { "prominence": "hide", "purpose": "structural" },
    "gridlines": { "prominence": "hide", "purpose": "structural" },
    "xAxisLine": { "prominence": "baseline", "purpose": "structural" },
    "yAxisLine": { "prominence": "hide", "purpose": "structural" },
    "xAxisLabels": { "prominence": "baseline", "purpose": "navigational" },
    "yAxisLabels": { "prominence": "baseline", "purpose": "navigational" },
    "line_paid": { 
      "prominence": "primary", 
      "purpose": "data-focus", 
      "sentiment": "positive"
    },
    "line_organic": { 
      "prominence": "secondary", 
      "purpose": "data-comparison", 
      "sentiment": "neutral"
    },
    "line_email": { 
      "prominence": "baseline", 
      "purpose": "data-comparison", 
      "sentiment": "neutral"
    },
    "marker_crossover": { 
      "prominence": "callout", 
      "purpose": "data-focus", 
      "sentiment": "positive"
    },
    "annotation_insight": { 
      "prominence": "callout", 
      "purpose": "annotation", 
      "sentiment": "positive"
    },
    "directLabel_paid": { 
      "prominence": "primary", 
      "purpose": "annotation" 
    },
    "directLabel_organic": { 
      "prominence": "secondary", 
      "purpose": "annotation" 
    },
    "directLabel_email": { 
      "prominence": "baseline", 
      "purpose": "annotation" 
    },
    "title": { "prominence": "primary", "purpose": "navigational" }
  },
  "anchorMappings": [
    {
      "insight": "annotation_insight",
      "dataRegion": "marker_crossover"
    }
  ]
}
```

### Gestalt Applications

1. **Similarity**: Paid line is green (positive), others are neutral grays
2. **Connection**: Lines create continuity, showing trends
3. **Proximity**: Annotation callout placed near the crossover point
4. **Contrast**: Only paid line has strong color (hawk in pigeons)

---

## Step 3: Formatting

### Formatted Specification

```json
{
  "chartId": "channel-performance",
  "formattedSpec": {
    "elements": {
      "line_paid": {
        "stroke": "#22c55e",
        "strokeWidth": 2.5,
        "opacity": 1
      },
      "line_organic": {
        "stroke": "#9ca3af",
        "strokeWidth": 1.5,
        "opacity": 0.7,
        "strokeDasharray": "4 2"
      },
      "line_email": {
        "stroke": "#d1d5db",
        "strokeWidth": 1,
        "opacity": 0.5
      },
      "marker_crossover": {
        "r": 8,
        "fill": "#22c55e",
        "stroke": "#ffffff",
        "strokeWidth": 3
      },
      "annotation_insight": {
        "backgroundColor": "#f0fdf4",
        "borderColor": "#22c55e",
        "borderWidth": 1,
        "borderRadius": 6,
        "padding": 12,
        "titleFontSize": 12,
        "titleFontWeight": 600,
        "titleColor": "#166534",
        "textFontSize": 11,
        "textColor": "#333333"
      },
      "directLabel_paid": {
        "fontSize": 12,
        "fontWeight": 600,
        "fill": "#22c55e"
      },
      "directLabel_organic": {
        "fontSize": 11,
        "fontWeight": 400,
        "fill": "#6b7280"
      },
      "directLabel_email": {
        "fontSize": 10,
        "fontWeight": 400,
        "fill": "#9ca3af"
      },
      "xAxisLine": {
        "stroke": "#d1d5db",
        "strokeWidth": 1
      }
    },
    "layout": {
      "margin": { "top": 20, "right": 100, "bottom": 40, "left": 50 }
    }
  }
}
```

---

## Step 4: Implementation

### Line Chart with Annotation (Recharts + Custom)

```tsx
import { 
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceDot
} from 'recharts';

const data = [
  { month: 'Jul', organic: 45000, paid: 32000, email: 18000 },
  { month: 'Aug', organic: 48000, paid: 38000, email: 19000 },
  { month: 'Sep', organic: 47000, paid: 44000, email: 20000 },
  { month: 'Oct', organic: 46000, paid: 52000, email: 21000 },
  { month: 'Nov', organic: 44000, paid: 58000, email: 22000 },
  { month: 'Dec', organic: 43000, paid: 65000, email: 23000 },
];

// Custom annotation component
const InsightAnnotation = ({ viewBox }: any) => {
  const { x, y } = viewBox;
  return (
    <g>
      {/* Connector line */}
      <line
        x1={x}
        y1={y - 10}
        x2={x + 20}
        y2={y - 50}
        stroke="#22c55e"
        strokeWidth={1}
      />
      {/* Annotation box */}
      <foreignObject x={x + 25} y={y - 90} width={150} height={70}>
        <div style={{
          backgroundColor: '#f0fdf4',
          border: '1px solid #22c55e',
          borderRadius: 6,
          padding: 8,
        }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#166534' }}>
            Paid Overtakes Organic
          </div>
          <div style={{ fontSize: 10, color: '#333333', marginTop: 4 }}>
            October marked the crossover point
          </div>
        </div>
      </foreignObject>
    </g>
  );
};

function ChannelPerformanceChart() {
  return (
    <div>
      <h3 style={{ fontSize: 18, fontWeight: 600, color: '#1a1a1a', marginBottom: 16 }}>
        Marketing Channel Performance
      </h3>
      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={data} margin={{ top: 20, right: 100, bottom: 20, left: 50 }}>
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
            tickFormatter={(v) => `${v / 1000}K`}
          />
          <Tooltip 
            formatter={(value: number, name: string) => [
              `$${value.toLocaleString()}`,
              name.charAt(0).toUpperCase() + name.slice(1)
            ]}
          />
          
          {/* Email - baseline */}
          <Line
            type="monotone"
            dataKey="email"
            stroke="#d1d5db"
            strokeWidth={1}
            opacity={0.5}
            dot={false}
          />
          
          {/* Organic - secondary comparison */}
          <Line
            type="monotone"
            dataKey="organic"
            stroke="#9ca3af"
            strokeWidth={1.5}
            strokeDasharray="4 2"
            opacity={0.7}
            dot={false}
          />
          
          {/* Paid - primary focus */}
          <Line
            type="monotone"
            dataKey="paid"
            stroke="#22c55e"
            strokeWidth={2.5}
            dot={false}
          />
          
          {/* Crossover marker */}
          <ReferenceDot
            x="Oct"
            y={52000}
            r={8}
            fill="#22c55e"
            stroke="#ffffff"
            strokeWidth={3}
            label={<InsightAnnotation />}
          />
        </LineChart>
      </ResponsiveContainer>
      
      {/* Direct labels (right side) */}
      <div style={{ 
        position: 'relative', 
        marginTop: -180, 
        marginLeft: 'calc(100% - 90px)',
        fontSize: 12
      }}>
        <div style={{ color: '#22c55e', fontWeight: 600 }}>Paid Search</div>
        <div style={{ color: '#6b7280', marginTop: 30 }}>Organic</div>
        <div style={{ color: '#9ca3af', marginTop: 55, fontSize: 10 }}>Email</div>
      </div>
    </div>
  );
}

export default ChannelPerformanceChart;
```

---

## Classification Breakdown

### Why these classifications?

| Element | Prominence | Rationale |
|---------|------------|-----------|
| `line_paid` | Primary | The story is about paid search growth |
| `line_organic` | Secondary | Part of comparison (the "vs") |
| `line_email` | Baseline | Context only, not central to story |
| `marker_crossover` | Callout | The key insight moment |
| `annotation` | Callout | Explains the insight |

### Cognitive Anchoring Applied

The annotation follows the **1:1 mapping rule**:
- One insight → One visual callout
- Annotation is proximate to the data point (October/Paid)
- Visual pointer (line) connects annotation to marker

### Contrast Budget

Only **one callout** in this chart (the crossover marker), following the hawk-in-pigeons principle. All other elements use secondary or baseline prominence.

---

## Final Result

The chart clearly tells the story:
1. **Eye first goes to**: Green paid search line (primary)
2. **Then notices**: The callout marker in October
3. **Reads**: The annotation explaining the crossover
4. **Context from**: Gray organic line showing the comparison
5. **Background**: Email line provides full context

This follows the cognitive load principles: strategic contrast, not overwhelming detail.
