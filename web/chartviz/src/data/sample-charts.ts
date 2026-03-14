import type { ChartSpec, ChartDataSlice } from "@/lib/charts/factory";

/**
 * Sample chart definition - pairs a ChartSpec with its corresponding data
 */
export interface SampleChart {
  spec: ChartSpec;
  data: ChartDataSlice;
  /** Optional height override for specific charts */
  height?: number;
  /** Whether this chart should span full width (2 columns) */
  fullWidth?: boolean;
}

// =============================================================================
// KPI Card
// =============================================================================

const kpiSpec: ChartSpec = {
  id: "kpi-revenue",
  title: "Total Revenue",
  chart_type: "kpi_card",
  dimensions: [{ field: "revenue", type: "numeric" }],
  data_mapping: {
    value: "revenue",
  },
  data_series: [
    {
      seriesId: "revenue",
      field: "revenue",
      prominence: "primary",
      purpose: "data-focus",
      sentiment: "positive",
    },
  ],
};

const kpiData: ChartDataSlice = {
  schema_id: "kpi-schema",
  rows: [{ row_id: "r1", revenue: 1250000, trend: 12.5 }],
};

// =============================================================================
// Data Table
// =============================================================================

const dataTableSpec: ChartSpec = {
  id: "table-products",
  title: "Product Sales",
  chart_type: "data_table",
  dimensions: [
    { field: "product", type: "category" },
    { field: "category", type: "category" },
    { field: "sales", type: "numeric" },
    { field: "units", type: "numeric" },
  ],
  data_mapping: {},
  data_series: [
    {
      seriesId: "sales",
      field: "sales",
      prominence: "primary",
      purpose: "data-focus",
      sentiment: "neutral",
    },
    {
      seriesId: "units",
      field: "units",
      prominence: "secondary",
      purpose: "data-comparison",
      sentiment: "neutral",
    },
  ],
};

const dataTableData: ChartDataSlice = {
  schema_id: "table-schema",
  rows: [
    {
      row_id: "r1",
      product: "Widget A",
      category: "Electronics",
      sales: 45000,
      units: 1500,
    },
    {
      row_id: "r2",
      product: "Widget B",
      category: "Electronics",
      sales: 38000,
      units: 1200,
    },
    {
      row_id: "r3",
      product: "Gadget X",
      category: "Accessories",
      sales: 52000,
      units: 2600,
    },
    {
      row_id: "r4",
      product: "Gadget Y",
      category: "Accessories",
      sales: 31000,
      units: 1550,
    },
    { row_id: "r5", product: "Tool Pro", category: "Tools", sales: 67000, units: 3350 },
    {
      row_id: "r6",
      product: "Tool Basic",
      category: "Tools",
      sales: 28000,
      units: 1400,
    },
  ],
};

// =============================================================================
// Bar Chart Vertical
// =============================================================================

const barVerticalSpec: ChartSpec = {
  id: "bar-sales",
  title: "Sales by Category",
  chart_type: "bar_chart_vertical",
  dimensions: [
    { field: "category", type: "category" },
    { field: "sales", type: "numeric" },
  ],
  data_mapping: {
    xAxis: "category",
    yAxis: "sales",
  },
  data_series: [
    {
      seriesId: "sales",
      field: "sales",
      prominence: "primary",
      purpose: "data-focus",
      sentiment: "neutral",
    },
  ],
};

const barVerticalData: ChartDataSlice = {
  schema_id: "bar-schema",
  rows: [
    { row_id: "r1", category: "Electronics", sales: 120000 },
    { row_id: "r2", category: "Clothing", sales: 95000 },
    { row_id: "r3", category: "Home & Garden", sales: 67000 },
    { row_id: "r4", category: "Sports", sales: 54000 },
    { row_id: "r5", category: "Books", sales: 32000 },
  ],
};

// =============================================================================
// Bar Chart Horizontal
// =============================================================================

const barHorizontalSpec: ChartSpec = {
  id: "bar-horizontal-regions",
  title: "Revenue by Region",
  chart_type: "bar_chart_horizontal",
  dimensions: [
    { field: "region", type: "category" },
    { field: "revenue", type: "numeric" },
  ],
  data_mapping: {
    xAxis: "revenue",
    yAxis: "region",
  },
  data_series: [
    {
      seriesId: "revenue",
      field: "revenue",
      prominence: "primary",
      purpose: "data-focus",
      sentiment: "positive",
    },
  ],
};

const barHorizontalData: ChartDataSlice = {
  schema_id: "bar-h-schema",
  rows: [
    { row_id: "r1", region: "North America", revenue: 450000 },
    { row_id: "r2", region: "Europe", revenue: 380000 },
    { row_id: "r3", region: "Asia Pacific", revenue: 290000 },
    { row_id: "r4", region: "Latin America", revenue: 120000 },
    { row_id: "r5", region: "Middle East", revenue: 85000 },
  ],
};

// =============================================================================
// Bar Chart Stacked
// =============================================================================

const barStackedSpec: ChartSpec = {
  id: "bar-stacked-quarterly",
  title: "Quarterly Sales by Product",
  chart_type: "bar_chart_stacked",
  dimensions: [
    { field: "category", type: "category" },
    { field: "series", type: "category" },
    { field: "value", type: "numeric" },
  ],
  data_mapping: {
    xAxis: "category",
    yAxis: "value",
    groupBy: "series",
  },
  data_series: [
    {
      seriesId: "product_a",
      groupValue: "Product A",
      prominence: "primary",
      purpose: "data-focus",
      sentiment: "neutral",
      label: "Product A",
    },
    {
      seriesId: "product_b",
      groupValue: "Product B",
      prominence: "secondary",
      purpose: "data-comparison",
      sentiment: "neutral",
      label: "Product B",
    },
    {
      seriesId: "product_c",
      groupValue: "Product C",
      prominence: "secondary",
      purpose: "data-comparison",
      sentiment: "neutral",
      label: "Product C",
    },
  ],
};

const barStackedData: ChartDataSlice = {
  schema_id: "stacked-schema",
  rows: [
    { row_id: "r1", category: "Q1", series: "Product A", value: 40000 },
    { row_id: "r2", category: "Q1", series: "Product B", value: 30000 },
    { row_id: "r3", category: "Q1", series: "Product C", value: 25000 },
    { row_id: "r4", category: "Q2", series: "Product A", value: 45000 },
    { row_id: "r5", category: "Q2", series: "Product B", value: 35000 },
    { row_id: "r6", category: "Q2", series: "Product C", value: 28000 },
    { row_id: "r7", category: "Q3", series: "Product A", value: 55000 },
    { row_id: "r8", category: "Q3", series: "Product B", value: 42000 },
    { row_id: "r9", category: "Q3", series: "Product C", value: 32000 },
    { row_id: "r10", category: "Q4", series: "Product A", value: 65000 },
    { row_id: "r11", category: "Q4", series: "Product B", value: 48000 },
    { row_id: "r12", category: "Q4", series: "Product C", value: 38000 },
  ],
};

// =============================================================================
// Bar Chart Grouped
// =============================================================================

const barGroupedSpec: ChartSpec = {
  id: "bar-grouped-channels",
  title: "Sales by Channel (Grouped)",
  chart_type: "bar_chart_grouped",
  dimensions: [
    { field: "category", type: "category" },
    { field: "group", type: "category" },
    { field: "value", type: "numeric" },
  ],
  data_mapping: {
    xAxis: "category",
    yAxis: "value",
    groupBy: "group",
  },
  data_series: [
    {
      seriesId: "online",
      groupValue: "Online",
      prominence: "primary",
      purpose: "data-focus",
      sentiment: "positive",
      label: "Online",
    },
    {
      seriesId: "retail",
      groupValue: "Retail",
      prominence: "secondary",
      purpose: "data-comparison",
      sentiment: "neutral",
      label: "Retail",
    },
  ],
};

const barGroupedData: ChartDataSlice = {
  schema_id: "grouped-schema",
  rows: [
    { row_id: "r1", category: "Jan", group: "Online", value: 35000 },
    { row_id: "r2", category: "Jan", group: "Retail", value: 28000 },
    { row_id: "r3", category: "Feb", group: "Online", value: 42000 },
    { row_id: "r4", category: "Feb", group: "Retail", value: 31000 },
    { row_id: "r5", category: "Mar", group: "Online", value: 48000 },
    { row_id: "r6", category: "Mar", group: "Retail", value: 35000 },
    { row_id: "r7", category: "Apr", group: "Online", value: 52000 },
    { row_id: "r8", category: "Apr", group: "Retail", value: 38000 },
  ],
};

// =============================================================================
// Line Chart
// =============================================================================

const lineSpec: ChartSpec = {
  id: "line-trend",
  title: "Revenue Trend",
  chart_type: "line_chart",
  dimensions: [
    { field: "date", type: "time" },
    { field: "revenue", type: "numeric" },
  ],
  data_mapping: {
    xAxis: "date",
    yAxis: "revenue",
  },
  data_series: [
    {
      seriesId: "revenue",
      field: "revenue",
      prominence: "primary",
      purpose: "data-focus",
      sentiment: "positive",
      label: "Revenue",
    },
  ],
};

const lineData: ChartDataSlice = {
  schema_id: "line-schema",
  rows: [
    { row_id: "r1", date: "2024-01-01", revenue: 45000 },
    { row_id: "r2", date: "2024-02-01", revenue: 52000 },
    { row_id: "r3", date: "2024-03-01", revenue: 48000 },
    { row_id: "r4", date: "2024-04-01", revenue: 61000 },
    { row_id: "r5", date: "2024-05-01", revenue: 55000 },
    { row_id: "r6", date: "2024-06-01", revenue: 67000 },
    { row_id: "r7", date: "2024-07-01", revenue: 72000 },
    { row_id: "r8", date: "2024-08-01", revenue: 68000 },
    { row_id: "r9", date: "2024-09-01", revenue: 78000 },
    { row_id: "r10", date: "2024-10-01", revenue: 85000 },
    { row_id: "r11", date: "2024-11-01", revenue: 92000 },
    { row_id: "r12", date: "2024-12-01", revenue: 105000 },
  ],
};

// =============================================================================
// Area Chart
// =============================================================================

const areaSpec: ChartSpec = {
  id: "area-visitors",
  title: "Website Visitors",
  chart_type: "area_chart",
  dimensions: [
    { field: "date", type: "time" },
    { field: "visitors", type: "numeric" },
  ],
  data_mapping: {
    xAxis: "date",
    yAxis: "visitors",
  },
  data_series: [
    {
      seriesId: "visitors",
      field: "visitors",
      prominence: "primary",
      purpose: "data-focus",
      sentiment: "positive",
      label: "Visitors",
    },
  ],
};

const areaData: ChartDataSlice = {
  schema_id: "area-schema",
  rows: [
    { row_id: "r1", date: "2024-01-01", visitors: 12000 },
    { row_id: "r2", date: "2024-02-01", visitors: 15000 },
    { row_id: "r3", date: "2024-03-01", visitors: 18000 },
    { row_id: "r4", date: "2024-04-01", visitors: 22000 },
    { row_id: "r5", date: "2024-05-01", visitors: 28000 },
    { row_id: "r6", date: "2024-06-01", visitors: 25000 },
    { row_id: "r7", date: "2024-07-01", visitors: 32000 },
    { row_id: "r8", date: "2024-08-01", visitors: 35000 },
  ],
};

// =============================================================================
// Scatter Plot
// =============================================================================

const scatterSpec: ChartSpec = {
  id: "scatter-correlation",
  title: "Price vs Sales Correlation",
  chart_type: "scatter_plot",
  dimensions: [
    { field: "price", type: "numeric" },
    { field: "sales", type: "numeric" },
    { field: "category", type: "category" },
  ],
  data_mapping: {
    xAxis: "price",
    yAxis: "sales",
    groupBy: "category",
  },
  data_series: [
    {
      seriesId: "price_sales",
      field: "sales",
      prominence: "primary",
      purpose: "data-focus",
      sentiment: "neutral",
      label: "Price vs Sales",
    },
  ],
};

const scatterData: ChartDataSlice = {
  schema_id: "scatter-schema",
  rows: [
    { row_id: "r1", price: 25, sales: 450, category: "A" },
    { row_id: "r2", price: 35, sales: 380, category: "A" },
    { row_id: "r3", price: 45, sales: 320, category: "B" },
    { row_id: "r4", price: 55, sales: 290, category: "B" },
    { row_id: "r5", price: 65, sales: 250, category: "A" },
    { row_id: "r6", price: 75, sales: 220, category: "C" },
    { row_id: "r7", price: 85, sales: 180, category: "C" },
    { row_id: "r8", price: 95, sales: 150, category: "B" },
    { row_id: "r9", price: 30, sales: 420, category: "A" },
    { row_id: "r10", price: 50, sales: 350, category: "C" },
    { row_id: "r11", price: 70, sales: 280, category: "B" },
    { row_id: "r12", price: 90, sales: 190, category: "A" },
  ],
};

// =============================================================================
// Pie Chart
// =============================================================================

const pieSpec: ChartSpec = {
  id: "pie-market-share",
  title: "Market Share",
  chart_type: "pie_chart",
  dimensions: [
    { field: "company", type: "category" },
    { field: "share", type: "numeric" },
  ],
  data_mapping: {
    value: "share",
    groupBy: "company",
  },
  data_series: [
    {
      seriesId: "share",
      field: "share",
      prominence: "primary",
      purpose: "data-focus",
      sentiment: "neutral",
      label: "Market Share",
    },
  ],
};

const pieData: ChartDataSlice = {
  schema_id: "pie-schema",
  rows: [
    { row_id: "r1", company: "Company A", share: 35 },
    { row_id: "r2", company: "Company B", share: 28 },
    { row_id: "r3", company: "Company C", share: 20 },
    { row_id: "r4", company: "Company D", share: 12 },
    { row_id: "r5", company: "Others", share: 5 },
  ],
};

// =============================================================================
// Donut Chart
// =============================================================================

const donutSpec: ChartSpec = {
  id: "donut-expenses",
  title: "Expense Breakdown",
  chart_type: "donut_chart",
  dimensions: [
    { field: "category", type: "category" },
    { field: "amount", type: "numeric" },
  ],
  data_mapping: {
    value: "amount",
    groupBy: "category",
  },
  data_series: [
    {
      seriesId: "amount",
      field: "amount",
      prominence: "primary",
      purpose: "data-focus",
      sentiment: "neutral",
      label: "Expense Amount",
    },
  ],
};

const donutData: ChartDataSlice = {
  schema_id: "donut-schema",
  rows: [
    { row_id: "r1", category: "Salaries", amount: 450000 },
    { row_id: "r2", category: "Marketing", amount: 120000 },
    { row_id: "r3", category: "Operations", amount: 180000 },
    { row_id: "r4", category: "R&D", amount: 250000 },
    { row_id: "r5", category: "Other", amount: 75000 },
  ],
};

// =============================================================================
// Histogram
// =============================================================================

const histogramSpec: ChartSpec = {
  id: "histogram-distribution",
  title: "Order Value Distribution",
  chart_type: "histogram",
  dimensions: [{ field: "order_value", type: "numeric" }],
  data_mapping: {
    xAxis: "order_value",
  },
  data_series: [
    {
      seriesId: "order_value",
      field: "order_value",
      prominence: "primary",
      purpose: "data-focus",
      sentiment: "neutral",
      label: "Order Value",
    },
  ],
};

// Generate deterministic histogram data (seeded random)
function seededRandom(seed: number) {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

const histogramData: ChartDataSlice = {
  schema_id: "histogram-schema",
  rows: Array.from({ length: 100 }, (_, i) => ({
    row_id: `r${i}`,
    order_value: Math.round(
      50 + seededRandom(i * 17) * 200 + (seededRandom(i * 31) > 0.7 ? 100 : 0),
    ),
  })),
};

// =============================================================================
// Heatmap
// =============================================================================

const heatmapSpec: ChartSpec = {
  id: "heatmap-activity",
  title: "User Activity Heatmap",
  chart_type: "heatmap",
  dimensions: [
    { field: "day", type: "category" },
    { field: "hour", type: "category" },
    { field: "activity", type: "numeric" },
  ],
  data_mapping: {
    column: "hour",
    row: "day",
    value: "activity",
  },
  data_series: [
    {
      seriesId: "activity",
      field: "activity",
      prominence: "primary",
      purpose: "data-focus",
      sentiment: "neutral",
      label: "Activity Level",
    },
  ],
};

const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const hours = ["9AM", "10AM", "11AM", "12PM", "1PM", "2PM", "3PM", "4PM", "5PM"];

const heatmapData: ChartDataSlice = {
  schema_id: "heatmap-schema",
  rows: days.flatMap((day, di) =>
    hours.map((hour, hi) => ({
      row_id: `r${di}-${hi}`,
      day,
      hour,
      activity: Math.round(
        20 +
          seededRandom(di * 100 + hi * 7) * 80 +
          (di < 5 && hi >= 2 && hi <= 6 ? 30 : 0),
      ),
    })),
  ),
};

// =============================================================================
// Treemap
// =============================================================================

const treemapSpec: ChartSpec = {
  id: "treemap-budget",
  title: "Budget Allocation",
  chart_type: "treemap",
  dimensions: [
    { field: "department", type: "category" },
    { field: "budget", type: "numeric" },
  ],
  data_mapping: {
    value: "budget",
    groupBy: "department",
  },
  data_series: [
    {
      seriesId: "budget",
      field: "budget",
      prominence: "primary",
      purpose: "data-focus",
      sentiment: "neutral",
      label: "Budget",
    },
  ],
};

const treemapData: ChartDataSlice = {
  schema_id: "treemap-schema",
  rows: [
    { row_id: "r1", department: "Engineering", budget: 850000 },
    { row_id: "r2", department: "Sales", budget: 620000 },
    { row_id: "r3", department: "Marketing", budget: 450000 },
    { row_id: "r4", department: "Operations", budget: 380000 },
    { row_id: "r5", department: "HR", budget: 220000 },
    { row_id: "r6", department: "Finance", budget: 180000 },
    { row_id: "r7", department: "Legal", budget: 150000 },
    { row_id: "r8", department: "Support", budget: 120000 },
  ],
};

// =============================================================================
// Export all sample charts as an array
// =============================================================================

export const sampleCharts: SampleChart[] = [
  { spec: kpiSpec, data: kpiData, height: 120 },
  { spec: dataTableSpec, data: dataTableData, height: 280, fullWidth: true },
  { spec: barVerticalSpec, data: barVerticalData },
  { spec: barHorizontalSpec, data: barHorizontalData },
  { spec: barStackedSpec, data: barStackedData },
  { spec: barGroupedSpec, data: barGroupedData },
  { spec: lineSpec, data: lineData },
  { spec: areaSpec, data: areaData },
  { spec: scatterSpec, data: scatterData },
  { spec: pieSpec, data: pieData },
  { spec: donutSpec, data: donutData },
  { spec: histogramSpec, data: histogramData },
  { spec: heatmapSpec, data: heatmapData, fullWidth: true },
  { spec: treemapSpec, data: treemapData, fullWidth: true },
];

/**
 * Get chart type display name from chart_type
 */
export function getChartTypeDisplayName(chartType: string): string {
  const names: Record<string, string> = {
    kpi_card: "KPI Card",
    data_table: "Data Table",
    bar_chart_vertical: "Bar Chart (Vertical)",
    bar_chart_horizontal: "Bar Chart (Horizontal)",
    bar_chart_stacked: "Bar Chart (Stacked)",
    bar_chart_grouped: "Bar Chart (Grouped)",
    line_chart: "Line Chart",
    area_chart: "Area Chart",
    scatter_plot: "Scatter Plot",
    pie_chart: "Pie Chart",
    donut_chart: "Donut Chart",
    histogram: "Histogram",
    heatmap: "Heatmap",
    treemap: "Treemap",
  };
  return names[chartType] || chartType;
}
