// Time series data
export const timeSeriesData = [
  { date: "Jan", sales: 4000, revenue: 2400, profit: 2400 },
  { date: "Feb", sales: 3000, revenue: 1398, profit: 2210 },
  { date: "Mar", sales: 2000, revenue: 9800, profit: 2290 },
  { date: "Apr", sales: 2780, revenue: 3908, profit: 2000 },
  { date: "May", sales: 1890, revenue: 4800, profit: 2181 },
  { date: "Jun", sales: 2390, revenue: 3800, profit: 2500 },
  { date: "Jul", sales: 3490, revenue: 4300, profit: 2100 },
  { date: "Aug", sales: 3200, revenue: 3900, profit: 2350 },
  { date: "Sep", sales: 4100, revenue: 4200, profit: 2600 },
  { date: "Oct", sales: 3800, revenue: 3700, profit: 2400 },
  { date: "Nov", sales: 4300, revenue: 4500, profit: 2800 },
  { date: "Dec", sales: 5200, revenue: 5100, profit: 3200 },
];

// Category data
export const categoryData = [
  { category: "Electronics", value: 4500, count: 120 },
  { category: "Clothing", value: 3200, count: 280 },
  { category: "Food", value: 2800, count: 450 },
  { category: "Books", value: 1200, count: 180 },
  { category: "Toys", value: 1800, count: 95 },
  { category: "Sports", value: 2100, count: 110 },
];

// Stacked data
export const stackedData = [
  { month: "Jan", product_a: 400, product_b: 240, product_c: 100 },
  { month: "Feb", product_a: 300, product_b: 139, product_c: 220 },
  { month: "Mar", product_a: 200, product_b: 980, product_c: 150 },
  { month: "Apr", product_a: 278, product_b: 390, product_c: 180 },
  { month: "May", product_a: 189, product_b: 480, product_c: 210 },
  { month: "Jun", product_a: 239, product_b: 380, product_c: 250 },
];

// Multi-line data
export const multiLineData = [
  { time: "00:00", server_1: 45, server_2: 32, server_3: 28, server_4: 52 },
  { time: "04:00", server_1: 52, server_2: 38, server_3: 35, server_4: 48 },
  { time: "08:00", server_1: 78, server_2: 65, server_3: 58, server_4: 72 },
  { time: "12:00", server_1: 92, server_2: 88, server_3: 82, server_4: 95 },
  { time: "16:00", server_1: 85, server_2: 75, server_3: 70, server_4: 88 },
  { time: "20:00", server_1: 65, server_2: 58, server_3: 52, server_4: 68 },
];

// Scatter data
export const scatterData = [
  { x: 10, y: 30, z: 200 },
  { x: 30, y: 40, z: 260 },
  { x: 45, y: 25, z: 400 },
  { x: 60, y: 50, z: 280 },
  { x: 80, y: 20, z: 500 },
  { x: 25, y: 55, z: 320 },
  { x: 70, y: 35, z: 380 },
  { x: 50, y: 60, z: 420 },
];

// Pie/Donut data
export const pieData = [
  { name: "Desktop", value: 4200 },
  { name: "Mobile", value: 3800 },
  { name: "Tablet", value: 2400 },
  { name: "Other", value: 1200 },
];

// Radar data
export const radarData = [
  { metric: "Speed", score: 120, benchmark: 150 },
  { metric: "Reliability", score: 98, benchmark: 150 },
  { metric: "Comfort", score: 86, benchmark: 150 },
  { metric: "Safety", score: 99, benchmark: 150 },
  { metric: "Efficiency", score: 85, benchmark: 150 },
  { metric: "Cost", score: 65, benchmark: 150 },
];

// Treemap data
export const treemapData = {
  name: "root",
  children: [
    { name: "Region A", size: 1200 },
    { name: "Region B", size: 800 },
    { name: "Region C", size: 950 },
    { name: "Region D", size: 600 },
    { name: "Region E", size: 1100 },
    { name: "Region F", size: 450 },
  ],
};

// Funnel data
export const funnelData = [
  { stage: "Impressions", value: 24000 },
  { stage: "Clicks", value: 12000 },
  { stage: "Sign-ups", value: 6000 },
  { stage: "Active Users", value: 3000 },
  { stage: "Conversions", value: 1200 },
];

// Heatmap-style data (2D grid)
export const heatmapData = [
  { day: "Mon", hour: "00", value: 12 },
  { day: "Mon", hour: "04", value: 8 },
  { day: "Mon", hour: "08", value: 45 },
  { day: "Mon", hour: "12", value: 78 },
  { day: "Mon", hour: "16", value: 65 },
  { day: "Mon", hour: "20", value: 32 },
  { day: "Tue", hour: "00", value: 10 },
  { day: "Tue", hour: "04", value: 7 },
  { day: "Tue", hour: "08", value: 50 },
  { day: "Tue", hour: "12", value: 82 },
  { day: "Tue", hour: "16", value: 70 },
  { day: "Tue", hour: "20", value: 38 },
  { day: "Wed", hour: "00", value: 15 },
  { day: "Wed", hour: "04", value: 9 },
  { day: "Wed", hour: "08", value: 55 },
  { day: "Wed", hour: "12", value: 88 },
  { day: "Wed", hour: "16", value: 72 },
  { day: "Wed", hour: "20", value: 40 },
  { day: "Thu", hour: "00", value: 11 },
  { day: "Thu", hour: "04", value: 8 },
  { day: "Thu", hour: "08", value: 48 },
  { day: "Thu", hour: "12", value: 85 },
  { day: "Thu", hour: "16", value: 68 },
  { day: "Thu", hour: "20", value: 35 },
  { day: "Fri", hour: "00", value: 14 },
  { day: "Fri", hour: "04", value: 10 },
  { day: "Fri", hour: "08", value: 60 },
  { day: "Fri", hour: "12", value: 95 },
  { day: "Fri", hour: "16", value: 80 },
  { day: "Fri", hour: "20", value: 45 },
];

// Gauge/Progress data
export const gaugeData = [
  { name: "Completion", value: 72, max: 100 },
  { name: "Performance", value: 85, max: 100 },
  { name: "Quality", value: 68, max: 100 },
];

// Horizontal bar data
export const horizontalBarData = [
  { label: "Product A", value: 4800 },
  { label: "Product B", value: 3200 },
  { label: "Product C", value: 2800 },
  { label: "Product D", value: 1900 },
  { label: "Product E", value: 1200 },
];

// Waterfall-style data
export const waterfallData = [
  { stage: "Initial", value: 10000, start: 0 },
  { stage: "Q1", value: 12000, start: 10000 },
  { stage: "Q2", value: 13500, start: 12000 },
  { stage: "Q3", value: 12800, start: 13500 },
  { stage: "Q4", value: 15000, start: 12800 },
];

// Bubble chart data
export const bubbleData = [
  { x: 10, y: 20, z: 300 },
  { x: 20, y: 35, z: 450 },
  { x: 30, y: 28, z: 600 },
  { x: 40, y: 50, z: 380 },
  { x: 50, y: 42, z: 520 },
  { x: 60, y: 55, z: 700 },
];

// Combo data for mixed charts
export const comboData = [
  { period: "Q1", revenue: 12000, cost: 8000, margin: 33 },
  { period: "Q2", revenue: 15000, cost: 9500, margin: 37 },
  { period: "Q3", revenue: 13500, cost: 8800, margin: 35 },
  { period: "Q4", revenue: 18000, cost: 11000, margin: 39 },
];

// Distribution data
export const distributionData = [
  { range: "0-10", frequency: 5 },
  { range: "10-20", frequency: 12 },
  { range: "20-30", frequency: 28 },
  { range: "30-40", frequency: 42 },
  { range: "40-50", frequency: 38 },
  { range: "50-60", frequency: 25 },
  { range: "60-70", frequency: 15 },
  { range: "70-80", frequency: 8 },
  { range: "80-90", frequency: 4 },
  { range: "90-100", frequency: 2 },
];

// Performance metrics
export const performanceData = [
  { metric: "CPU", current: 68, target: 80 },
  { metric: "Memory", current: 75, target: 85 },
  { metric: "Disk", current: 45, target: 70 },
  { metric: "Network", current: 82, target: 90 },
];
