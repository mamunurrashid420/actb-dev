import { ComponentType } from "react";

// Re-export Highlight from shared proto types
export { type Highlight, HighlightType } from "@actbi/shared/proto";
import type { Highlight } from "@actbi/shared/proto";

// =============================================================================
// Semantic Types for Agent Decisions (UI maps these to visual styles)
// =============================================================================

/**
 * Visual prominence - how much attention should this element receive?
 * UI maps this to opacity, stroke width, font weight, etc.
 */
export type Prominence =
  | "hide"
  | "background"
  | "baseline"
  | "secondary"
  | "primary"
  | "callout";

/**
 * Functional purpose - what role does this data series serve?
 * UI maps this to line styles (solid, dashed, dotted).
 */
export type Purpose = "data-focus" | "data-comparison" | "data-projection";

/**
 * Evaluative sentiment - what is the meaning of this data?
 * UI maps this to color palette (success, danger, neutral, warning).
 */
export type Sentiment = "positive" | "negative" | "neutral" | "warning";

/**
 * Data mapping from schema fields to chart dimensions.
 * Specifies how data fields are mapped to visual chart dimensions.
 * This is structural (positioning), not semantic (meaning).
 */
export interface DataMapping {
  // Axis mappings - which field goes where
  xAxis?: string; // Field for X-axis (time, category, or numeric)
  yAxis?: string; // Field for Y-axis (numeric, or category for horizontal bars)

  // Grouping - which field to group by to create series
  groupBy?: string; // Field that contains group identifiers (for long-format data)

  // Value encoding
  value?: string; // Primary value field (for KPI, pie, treemap)

  // Grid mapping (for heatmaps)
  row?: string; // Field for grid rows
  column?: string; // Field for grid columns
}

/**
 * Value range for value-based styling (heatmaps, choropleths, gauges).
 * Points within this range share the same styling.
 */
export interface ValueRange {
  min: number;
  max: number;
}

/**
 * Classification for a data series (agent decision).
 * Semantic metadata that the UI maps to visual styles.
 *
 * "Series" means: "A group of data points sharing the same styling rules"
 * Three ways to identify which data points belong to a series:
 * - field: column name (wide-format data)
 * - groupValue: value in groupBy field (long-format data)
 * - valueRange: numeric range (value-based styling)
 */
export interface DataSeriesClassification {
  // Identity
  seriesId: string; // Unique identifier for this series

  // Reference - HOW to identify this series in the data
  field?: string; // For wide-format data (column name, e.g., "revenue")
  groupValue?: string; // For long-format data (value in groupBy field, e.g., "Product A")
  valueRange?: ValueRange; // For value-based styling (heatmaps, choropleths)

  // Semantic classifications (agent decisions)
  prominence: Prominence; // hide | background | baseline | secondary | primary | callout
  purpose: Purpose; // data-focus | data-comparison | data-projection
  sentiment?: Sentiment; // positive | negative | neutral | warning

  // Display
  label?: string; // Human-readable label for legend/tooltip
}

// =============================================================================
// Core Types
// =============================================================================

// Highlight is imported from @actbi/shared/proto (see top of file)

export interface Dimension {
  field: string;
  type: "time" | "category" | "numeric";
}

export interface Filter {
  field: string;
  operator: string;
  value: string;
}

export interface ChartData {
  schema_id: string;
  rows: Array<Record<string, any>>;
}

// =============================================================================
// Base Chart Props
// =============================================================================

export interface BaseChartProps {
  data: ChartData;
  dimensions: Dimension[];
  filters?: Filter[];
  title?: string;
  width?: number;
  height?: number;
  highlights?: Highlight[];

  // Semantic metadata from agent - UI uses these to determine visual styling
  dataMapping?: DataMapping;
  dataSeries?: DataSeriesClassification[];
}

// =============================================================================
// Chart-Specific Props
// =============================================================================

// KPI Card
export interface KPICardProps extends BaseChartProps {
  value?: number;
  label?: string;
  trend?: {
    value: number;
    direction: "up" | "down" | "neutral";
    label?: string;
  };
  format?: "number" | "currency" | "percentage";
}

// Data Table
export interface DataTableProps extends BaseChartProps {
  columns?: Array<{
    field: string;
    header: string;
    width?: number;
    align?: "left" | "center" | "right";
  }>;
  sortable?: boolean;
  paginated?: boolean;
  pageSize?: number;
}

// Bar Charts (Vertical/Horizontal/Stacked/Grouped)
export interface BarChartProps extends BaseChartProps {
  orientation?: "vertical" | "horizontal";
  stacked?: boolean;
  grouped?: boolean;
  barPadding?: number;
  showValues?: boolean;
  colorScheme?: string[];
}

// Line Chart
export interface LineChartProps extends BaseChartProps {
  curve?: "linear" | "monotone" | "step" | "cardinal";
  showDots?: boolean;
  strokeWidth?: number;
  smoothing?: number;
  showArea?: boolean; // for area chart variant
}

// Scatter Plot
export interface ScatterPlotProps extends BaseChartProps {
  sizeField?: string;
  colorField?: string;
  showTrendline?: boolean;
  dotSize?: number;
}

// Pie/Donut Chart
export interface PieChartProps extends BaseChartProps {
  donut?: boolean;
  innerRadius?: number;
  showLabels?: boolean;
  showPercentages?: boolean;
}

// Histogram
export interface HistogramProps extends BaseChartProps {
  bins?: number;
  binWidth?: number;
  showDistribution?: boolean;
  showMean?: boolean;
}

// Heatmap
export interface HeatmapProps extends BaseChartProps {
  colorScheme?: "sequential" | "diverging";
  showValues?: boolean;
  cellPadding?: number;
}

// Treemap
export interface TreemapProps extends BaseChartProps {
  colorField?: string;
  showLabels?: boolean;
  padding?: number;
}

// =============================================================================
// Chart Registry
// =============================================================================

export type ChartComponent = ComponentType<BaseChartProps>;

// Chart registry - maps chart_type to component
const chartRegistry: Record<string, ChartComponent> = {};

export function registerChart(type: string, component: ChartComponent): void {
  chartRegistry[type] = component;
}

export function getChartComponent(type: string): ChartComponent | undefined {
  return chartRegistry[type];
}

export function getAvailableChartTypes(): string[] {
  return Object.keys(chartRegistry);
}

// =============================================================================
// Highlight Color Utilities
// =============================================================================

// Default highlight color palette - can be customized per design system
export const HIGHLIGHT_COLORS = [
  "#3b82f6",
  "#f59e0b",
  "#8b5cf6",
  "#ec4899",
  "#10b981",
  "#ef4444",
];

// Light versions for backgrounds (e.g., table rows)
export const HIGHLIGHT_COLORS_LIGHT = [
  "#dbeafe",
  "#fed7aa",
  "#e9d5ff",
  "#fce7f3",
  "#d1fae5",
  "#fee2e2",
];

/**
 * Create a color map from insight IDs to colors.
 * Same insightId always gets the same color for consistency across charts.
 */
export function createInsightColorMap(highlights: Highlight[]): Map<string, string> {
  const colorMap = new Map<string, string>();
  const uniqueInsightIds = [...new Set(highlights.map((h) => h.insightId))];
  uniqueInsightIds.forEach((insightId, index) => {
    colorMap.set(insightId, HIGHLIGHT_COLORS[index % HIGHLIGHT_COLORS.length]);
  });
  return colorMap;
}

/**
 * Get highlight color for a specific insight, with fallback
 */
export function getHighlightColor(
  insightId: string,
  colorMap: Map<string, string>,
  fallback = "#6b7280",
): string {
  return colorMap.get(insightId) || fallback;
}
