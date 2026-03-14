import type { Insight, Highlight } from "@/types/insights";
import { HighlightType, InsightType, RecommendationType } from "@/types/insights";

/**
 * Sample insights and highlights for demonstrating the ChartWithInsights composite.
 * These are paired with charts from sample-charts.ts.
 *
 * Note: Uses generated proto types from @actbi/shared/proto via @/types/insights.
 */

// =============================================================================
// Line Chart Insights (Revenue Trend - id: "line-trend")
// =============================================================================

export const lineTrendHighlights: Highlight[] = [
  {
    id: "h-line-1",
    insightId: "insight-line-1",
    type: HighlightType.POINT_SET,
    description: "Q4 surge",
    rowIds: ["r10", "r11", "r12"], // Oct, Nov, Dec
    chartDataSliceId: "",
    fieldFilters: {},
    thresholdValue: 0,
    rangeMin: 0,
    rangeMax: 0,
    thresholdRangeField: "",
  },
  {
    id: "h-line-2",
    insightId: "insight-line-2",
    type: HighlightType.THRESHOLD,
    description: "Growth milestone",
    thresholdValue: 70000,
    thresholdRangeField: "revenue",
    chartDataSliceId: "",
    rowIds: [],
    fieldFilters: {},
    rangeMin: 0,
    rangeMax: 0,
  },
];

export const lineTrendInsights: Insight[] = [
  {
    id: "insight-line-1",
    type: InsightType.TREND,
    summary:
      "Q4 shows exceptional growth with revenue increasing 35% from October to December, driven by seasonal demand.",
    detail: "",
    target: { chartId: "line-trend" },
    highlightIds: ["h-line-1"],
    confidence: 0.92,
    recommendations: [
      {
        id: "rec-line-1a",
        type: RecommendationType.INVESTIGATION,
        summary: "Analyze Q4 marketing campaigns for replication",
        detail: "",
        priority: "high",
        actionParams: {},
      },
      {
        id: "rec-line-1b",
        type: RecommendationType.FYI,
        summary: "Prepare inventory for next year's Q4 surge",
        detail: "",
        priority: "medium",
        actionParams: {},
      },
    ],
    createdAt: undefined,
    schemaVersion: 1,
  },
  {
    id: "insight-line-2",
    type: InsightType.POSITIVE,
    summary:
      "Revenue crossed the $70K monthly threshold in July, indicating sustainable business growth.",
    detail: "",
    target: { chartId: "line-trend" },
    highlightIds: ["h-line-2"],
    confidence: 0.88,
    recommendations: [
      {
        id: "rec-line-2a",
        type: RecommendationType.SHARE,
        summary: "Share milestone achievement with stakeholders",
        detail: "",
        priority: "low",
        actionParams: {},
      },
    ],
    createdAt: undefined,
    schemaVersion: 1,
  },
];

// =============================================================================
// Bar Chart Insights (Sales by Category - id: "bar-sales")
// =============================================================================

export const barSalesHighlights: Highlight[] = [
  {
    id: "h-bar-1",
    insightId: "insight-bar-1",
    type: HighlightType.ROW,
    description: "Top performer",
    rowIds: ["r1"], // Electronics
    chartDataSliceId: "",
    fieldFilters: {},
    thresholdValue: 0,
    rangeMin: 0,
    rangeMax: 0,
    thresholdRangeField: "",
  },
  {
    id: "h-bar-2",
    insightId: "insight-bar-2",
    type: HighlightType.ROW,
    description: "Growth opportunity",
    rowIds: ["r5"], // Books
    chartDataSliceId: "",
    fieldFilters: {},
    thresholdValue: 0,
    rangeMin: 0,
    rangeMax: 0,
    thresholdRangeField: "",
  },
];

export const barSalesInsights: Insight[] = [
  {
    id: "insight-bar-1",
    type: InsightType.NEUTRAL,
    summary:
      "Electronics leads with $120K in sales, representing 33% of total category sales and outperforming the next category by 26%.",
    detail: "",
    target: { chartId: "bar-sales" },
    highlightIds: ["h-bar-1"],
    confidence: 0.95,
    recommendations: [
      {
        id: "rec-bar-1a",
        type: RecommendationType.EXPERIMENT,
        summary: "Increase Electronics inventory and SKU variety",
        detail: "",
        priority: "high",
        actionParams: {},
      },
    ],
    createdAt: undefined,
    schemaVersion: 1,
  },
  {
    id: "insight-bar-2",
    type: InsightType.LIGHTBULB,
    summary:
      "Books has the lowest sales at $32K but may have untapped potential given market trends toward reading and education.",
    detail: "",
    target: { chartId: "bar-sales" },
    highlightIds: ["h-bar-2"],
    confidence: 0.72,
    recommendations: [
      {
        id: "rec-bar-2a",
        type: RecommendationType.INVESTIGATION,
        summary: "Research competitor book sales and pricing",
        detail: "",
        priority: "medium",
        actionParams: {},
      },
      {
        id: "rec-bar-2b",
        type: RecommendationType.EXPERIMENT,
        summary: "Test book bundles or subscription model",
        detail: "",
        priority: "medium",
        actionParams: {},
      },
    ],
    createdAt: undefined,
    schemaVersion: 1,
  },
];

// =============================================================================
// Scatter Plot Insights (Price vs Sales - id: "scatter-correlation")
// =============================================================================

export const scatterHighlights: Highlight[] = [
  {
    id: "h-scatter-1",
    insightId: "insight-scatter-1",
    type: HighlightType.ANNOTATION,
    description: "Sweet spot",
    fieldFilters: { category: "A" },
    chartDataSliceId: "",
    rowIds: [],
    thresholdValue: 0,
    rangeMin: 0,
    rangeMax: 0,
    thresholdRangeField: "",
  },
  {
    id: "h-scatter-2",
    insightId: "insight-scatter-2",
    type: HighlightType.THRESHOLD,
    description: "Price ceiling",
    thresholdValue: 75,
    thresholdRangeField: "price",
    chartDataSliceId: "",
    rowIds: [],
    fieldFilters: {},
    rangeMin: 0,
    rangeMax: 0,
  },
];

export const scatterInsights: Insight[] = [
  {
    id: "insight-scatter-1",
    type: InsightType.COMPARISON,
    summary:
      "Category A products show the best price-to-sales ratio, maintaining strong sales even at higher price points.",
    detail: "",
    target: { chartId: "scatter-correlation" },
    highlightIds: ["h-scatter-1"],
    confidence: 0.85,
    recommendations: [
      {
        id: "rec-scatter-1a",
        type: RecommendationType.FYI,
        summary: "Apply Category A pricing strategy to other categories",
        detail: "",
        priority: "high",
        actionParams: {},
      },
    ],
    createdAt: undefined,
    schemaVersion: 1,
  },
  {
    id: "insight-scatter-2",
    type: InsightType.NEUTRAL,
    summary:
      "Sales drop significantly above $75 price point, suggesting a psychological price ceiling for this market.",
    detail: "",
    target: { chartId: "scatter-correlation" },
    highlightIds: ["h-scatter-2"],
    confidence: 0.78,
    recommendations: [
      {
        id: "rec-scatter-2a",
        type: RecommendationType.FYI,
        summary: "Keep new product launches under $75 initially",
        detail: "",
        priority: "medium",
        actionParams: {},
      },
    ],
    createdAt: undefined,
    schemaVersion: 1,
  },
];

// =============================================================================
// Combined exports for easy use in test page
// =============================================================================

export interface ChartInsightsData {
  chartId: string;
  highlights: Highlight[];
  insights: Insight[];
}

export const sampleInsightsData: ChartInsightsData[] = [
  {
    chartId: "line-trend",
    highlights: lineTrendHighlights,
    insights: lineTrendInsights,
  },
  {
    chartId: "bar-sales",
    highlights: barSalesHighlights,
    insights: barSalesInsights,
  },
  {
    chartId: "scatter-correlation",
    highlights: scatterHighlights,
    insights: scatterInsights,
  },
];

/**
 * Get insights data for a specific chart by ID
 */
export function getInsightsForChart(chartId: string): ChartInsightsData | undefined {
  return sampleInsightsData.find((data) => data.chartId === chartId);
}
