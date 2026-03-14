---
type: worked-example
example-id: financial-bridge
scenario: Revenue bridge analysis
charts: [waterfall_chart]
tags: [example, walkthrough, financial, bridge, waterfall]
---

# Worked Example: Financial Bridge Analysis

A walkthrough for revenue bridge visualization using a waterfall chart.

## Scenario

**User Request**: "Can you show me what drove the change in revenue from Q3 to Q4? I need to present this to the board and explain each factor."

**Data Available**:
```json
{
  "bridge": [
    { "label": "Q3 Revenue", "value": 8500000, "type": "start" },
    { "label": "New Customers", "value": 1200000, "type": "increase" },
    { "label": "Expansion (Existing)", "value": 650000, "type": "increase" },
    { "label": "Price Increase", "value": 180000, "type": "increase" },
    { "label": "Churn", "value": -780000, "type": "decrease" },
    { "label": "Downgrades", "value": -320000, "type": "decrease" },
    { "label": "One-time Credits", "value": -150000, "type": "decrease" },
    { "label": "Q4 Revenue", "value": 9280000, "type": "end" }
  ]
}
```

---

## Step 1: Selection

### Analysis

| Data Characteristic | Observation |
|---------------------|-------------|
| Structure | Sequential steps with start and end |
| Values | Mix of positive and negative changes |
| Story | "How did we get from A to B?" |
| Intent | Explain cumulative change |

**Recommendation**: **Waterfall Chart**

The data perfectly fits the waterfall pattern: starting value, a series of positive/negative changes, and ending total.

### Selection Output

```json
{
  "selection": {
    "id": "revenue-bridge",
    "chartType": "waterfall_chart",
    "rationale": "Sequential cumulative changes from start to end value - classic bridge/waterfall use case",
    "mapping": {
      "category": "label",
      "value": "value",
      "type": "type"
    }
  }
}
```

---

## Step 2: Refinement

### Element Classification

```json
{
  "chartId": "revenue-bridge",
  "elementClassifications": {
    "chartBorder": { "prominence": "hide", "purpose": "structural" },
    "gridlines": { "prominence": "background", "purpose": "structural" },
    "xAxisLine": { "prominence": "baseline", "purpose": "structural" },
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
    },
    "title": { "prominence": "primary", "purpose": "navigational" }
  }
}
```

### Structural Corrections

```json
{
  "structuralCorrections": [
    {
      "element": "xAxisLabels",
      "issue": "long-labels",
      "correction": "rotate-45-degrees",
      "rationale": "Category labels are too long to fit horizontally"
    }
  ]
}
```

### Gestalt Applications

1. **Connection**: Connector lines link each bar to the next, showing the running total flow
2. **Similarity**: Same color for all increases (green), all decreases (red)
3. **Enclosure**: Start and end bars are neutral gray, enclosing the "change story"

---

## Step 3: Formatting

### Formatted Specification

```json
{
  "chartId": "revenue-bridge",
  "formattedSpec": {
    "elements": {
      "bars_start": {
        "fill": "#6b7280",
        "radius": [4, 4, 0, 0]
      },
      "bars_increase": {
        "fill": "#22c55e",
        "radius": [4, 4, 0, 0]
      },
      "bars_decrease": {
        "fill": "#ef4444",
        "radius": [4, 4, 0, 0]
      },
      "bars_end": {
        "fill": "#6b7280",
        "radius": [4, 4, 0, 0]
      },
      "connectorLines": {
        "stroke": "#9ca3af",
        "strokeWidth": 1,
        "strokeDasharray": "3 3"
      },
      "valueLabels": {
        "fontSize": 11,
        "fontWeight": 500,
        "fill": "#1a1a1a"
      },
      "xAxisLabels": {
        "fontSize": 11,
        "fill": "#666666",
        "rotation": -45
      },
      "title": {
        "fontSize": 18,
        "fontWeight": 600,
        "fill": "#1a1a1a"
      }
    },
    "layout": {
      "margin": { "top": 50, "right": 30, "bottom": 80, "left": 70 },
      "barPadding": 0.3
    }
  }
}
```

---

## Step 4: Implementation

### Waterfall Chart (D3 + React)

```tsx
import * as d3 from 'd3';
import { useRef, useEffect } from 'react';

interface WaterfallItem {
  label: string;
  value: number;
  type: 'start' | 'increase' | 'decrease' | 'end';
}

const data: WaterfallItem[] = [
  { label: 'Q3 Revenue', value: 8500000, type: 'start' },
  { label: 'New Customers', value: 1200000, type: 'increase' },
  { label: 'Expansion', value: 650000, type: 'increase' },
  { label: 'Price Increase', value: 180000, type: 'increase' },
  { label: 'Churn', value: -780000, type: 'decrease' },
  { label: 'Downgrades', value: -320000, type: 'decrease' },
  { label: 'Credits', value: -150000, type: 'decrease' },
  { label: 'Q4 Revenue', value: 9280000, type: 'end' },
];

function RevenueBridgeChart() {
  const svgRef = useRef<SVGSVGElement>(null);
  
  useEffect(() => {
    if (!svgRef.current) return;
    
    const width = 800;
    const height = 450;
    const margin = { top: 50, right: 30, bottom: 100, left: 80 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;
    
    d3.select(svgRef.current).selectAll('*').remove();
    
    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);
    
    // Title
    svg.append('text')
      .attr('x', margin.left)
      .attr('y', 30)
      .attr('font-size', '18px')
      .attr('font-weight', '600')
      .attr('fill', '#1a1a1a')
      .text('Revenue Bridge: Q3 to Q4');
    
    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);
    
    // Process data for waterfall
    let runningTotal = 0;
    const processed = data.map((d, i) => {
      let y0: number, y1: number;
      
      if (d.type === 'start') {
        y0 = 0;
        y1 = d.value;
        runningTotal = d.value;
      } else if (d.type === 'end') {
        y0 = 0;
        y1 = runningTotal;
      } else {
        y0 = runningTotal;
        y1 = runningTotal + d.value;
        runningTotal = y1;
      }
      
      return { ...d, y0, y1, runningTotal };
    });
    
    // Scales
    const xScale = d3.scaleBand()
      .domain(data.map(d => d.label))
      .range([0, innerWidth])
      .padding(0.3);
    
    const yMax = d3.max(processed, d => Math.max(d.y0, d.y1)) || 1;
    const yScale = d3.scaleLinear()
      .domain([0, yMax * 1.1])
      .range([innerHeight, 0]);
    
    // Colors
    const getColor = (type: string) => {
      switch (type) {
        case 'increase': return '#22c55e';
        case 'decrease': return '#ef4444';
        default: return '#6b7280';
      }
    };
    
    // Connector lines
    for (let i = 0; i < processed.length - 1; i++) {
      const current = processed[i];
      const next = processed[i + 1];
      
      if (next.type !== 'end') {
        g.append('line')
          .attr('x1', (xScale(current.label) || 0) + xScale.bandwidth())
          .attr('x2', xScale(next.label) || 0)
          .attr('y1', yScale(current.y1))
          .attr('y2', yScale(current.y1))
          .attr('stroke', '#9ca3af')
          .attr('stroke-width', 1)
          .attr('stroke-dasharray', '3 3');
      }
    }
    
    // Bars
    processed.forEach(d => {
      const x = xScale(d.label) || 0;
      const y = yScale(Math.max(d.y0, d.y1));
      const barHeight = Math.abs(yScale(d.y0) - yScale(d.y1));
      
      g.append('rect')
        .attr('x', x)
        .attr('y', y)
        .attr('width', xScale.bandwidth())
        .attr('height', barHeight)
        .attr('fill', getColor(d.type))
        .attr('rx', 4)
        .attr('ry', 4);
      
      // Value label
      const labelValue = d.type === 'start' || d.type === 'end'
        ? `$${(d.value / 1000000).toFixed(1)}M`
        : `${d.value > 0 ? '+' : ''}$${(d.value / 1000000).toFixed(2)}M`;
      
      g.append('text')
        .attr('x', x + xScale.bandwidth() / 2)
        .attr('y', y - 8)
        .attr('text-anchor', 'middle')
        .attr('font-size', '11px')
        .attr('font-weight', '500')
        .attr('fill', '#1a1a1a')
        .text(labelValue);
    });
    
    // X axis
    g.append('g')
      .attr('transform', `translate(0,${innerHeight})`)
      .call(d3.axisBottom(xScale))
      .selectAll('text')
      .attr('transform', 'rotate(-45)')
      .style('text-anchor', 'end')
      .style('font-size', '11px')
      .style('fill', '#666666');
    
    // Y axis
    g.append('g')
      .call(d3.axisLeft(yScale).tickFormat(d => `$${(d as number) / 1000000}M`))
      .selectAll('text')
      .style('font-size', '11px')
      .style('fill', '#666666');
    
  }, []);
  
  return <svg ref={svgRef} />;
}

export default RevenueBridgeChart;
```

---

## Presentation Narrative

When presenting this waterfall to the board:

1. **Start**: "We began Q3 at $8.5M in revenue."

2. **Growth Drivers** (green bars):
   - "New customer acquisition added $1.2M"
   - "Expansion from existing customers contributed $650K"
   - "Our price increase in October added $180K"

3. **Headwinds** (red bars):
   - "We lost $780K to churn—this remains our biggest challenge"
   - "Downgrades cost us $320K"
   - "One-time credits reduced revenue by $150K"

4. **Result**: "Net result: Q4 revenue of $9.28M, up 9.2% from Q3."

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Gray for start/end | They're anchors, not changes |
| Green for increases | Positive sentiment, intuitive |
| Red for decreases | Negative sentiment, intuitive |
| Connector lines | Shows running total continuity |
| Rotated labels | Fits long category names |
| Value labels above bars | Easy to read exact amounts |
