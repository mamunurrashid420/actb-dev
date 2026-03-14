/**
 * UI Style Guide - Defaults for chart rendering
 *
 * This module defines the UI-side defaults that the agent does NOT output.
 * The agent outputs semantic classifications (prominence, purpose, sentiment);
 * this module maps those to structural configuration and element settings.
 *
 * Design reference: Slate-blue dashboard with Inter typography.
 * - Chart palette: sequential slate-blue (#2E3F5C → #A4BAD4)
 * - Sentiment: emerald/red/amber/slate
 * - Typography: Inter, semibold titles, regular body, light labels
 */

import type { Prominence, Purpose, Sentiment } from "./factory";

// =============================================================================
// Chart Sequential Palette
// =============================================================================

/**
 * Slate-blue sequential palette for non-sentiment data series.
 * Derived from the design snapshot — dark navy to light blue-gray.
 * Use index 0 (darkest) for primary/focus series, higher for secondary.
 */
export const CHART_PALETTE = [
  "#2E3F5C", // chart-1: darkest navy
  "#3B4F72", // chart-2: dark steel blue
  "#5B7299", // chart-3: medium slate
  "#7D97B8", // chart-4: light steel
  "#A4BAD4", // chart-5: lightest blue-gray
] as const;

/**
 * Get a color from the sequential palette by index (wraps around).
 */
export function getChartColor(index: number): string {
  return CHART_PALETTE[index % CHART_PALETTE.length];
}

// =============================================================================
// Color Derivation from Sentiment
// =============================================================================

/**
 * Base colors for sentiment mapping.
 * Matched to the design snapshot:
 * - positive: emerald green (#16A34A) — upward arrows, good KPIs
 * - negative: red (#DC2626) — downward triangles, declining KPIs
 * - neutral: slate (#64748B) — default, non-evaluative data
 * - warning: amber (#D97706) — alert triangles, cost warnings
 */
export const SENTIMENT_COLORS: Record<Sentiment, string> = {
  positive: "#16a34a", // emerald-600
  negative: "#dc2626", // red-600
  neutral: "#64748b", // slate-500
  warning: "#d97706", // amber-600
};

/**
 * Light background tints for sentiment areas/fills.
 */
export const SENTIMENT_COLORS_LIGHT: Record<Sentiment, string> = {
  positive: "#dcfce7",
  negative: "#fee2e2",
  neutral: "#f1f5f9",
  warning: "#fef3c7",
};

/**
 * Get color from sentiment classification.
 */
export function getSentimentColor(sentiment?: Sentiment): string {
  return sentiment ? SENTIMENT_COLORS[sentiment] : SENTIMENT_COLORS.neutral;
}

/**
 * Get light background color from sentiment classification.
 */
export function getSentimentColorLight(sentiment?: Sentiment): string {
  return sentiment ? SENTIMENT_COLORS_LIGHT[sentiment] : SENTIMENT_COLORS_LIGHT.neutral;
}

// =============================================================================
// Opacity/Weight from Prominence
// =============================================================================

/**
 * Get opacity from prominence classification.
 * Tuned to match the design snapshot's visual weight hierarchy.
 */
export function getProminenceOpacity(prominence: Prominence): number {
  switch (prominence) {
    case "hide":
      return 0;
    case "background":
      return 0.25;
    case "baseline":
      return 0.55;
    case "secondary":
      return 0.8;
    case "primary":
      return 1.0;
    case "callout":
      return 1.0;
  }
}

/**
 * Get stroke width multiplier from prominence classification.
 */
export function getProminenceStrokeWidth(
  prominence: Prominence,
  baseWidth: number = 2,
): number {
  switch (prominence) {
    case "hide":
      return 0;
    case "background":
      return baseWidth * 0.5;
    case "baseline":
      return baseWidth * 0.75;
    case "secondary":
      return baseWidth;
    case "primary":
      return baseWidth * 1.5;
    case "callout":
      return baseWidth * 2;
  }
}

// =============================================================================
// Stroke Dash Array from Purpose
// =============================================================================

/**
 * Get SVG stroke-dasharray from purpose classification.
 */
export function getStrokeDashArray(purpose: Purpose): string {
  switch (purpose) {
    case "data-focus":
      return "none";
    case "data-comparison":
      return "6 3";
    case "data-projection":
      return "3 3";
  }
}

// =============================================================================
// Line Style Derivation
// =============================================================================

/**
 * UI derives lineStyle from purpose.
 * Agent outputs purpose; UI determines visual representation.
 */
export function getLineStyle(purpose: Purpose): "solid" | "dashed" | "dotted" {
  switch (purpose) {
    case "data-focus":
      return "solid";
    case "data-comparison":
      return "dashed";
    case "data-projection":
      return "dotted";
  }
}

// =============================================================================
// Structural Config Types
// =============================================================================

export interface StructuralConfig {
  // Common
  showGridlines?: boolean;
  showLegend?: boolean;
  titleAlignment?: "left" | "center" | "right";
  labelPosition?: "direct" | "outside" | "inside";

  // Line/Area charts
  showDots?: boolean;
  showArea?: boolean;
  curve?: "linear" | "monotone" | "step" | "cardinal";

  // Bar charts
  barPadding?: number;
  showValues?: boolean;
  radius?: [number, number, number, number];

  // Pie/Donut charts
  innerRadius?: number;
  showLabels?: boolean;
  showPercentages?: boolean;

  // Tables
  sortable?: boolean;
  paginated?: boolean;
  pageSize?: number;
  striped?: boolean;
}

// =============================================================================
// Structural Defaults per Chart Type
// =============================================================================

/**
 * Default structural configuration per chart type.
 * These are UI decisions, not agent decisions.
 */
export const STRUCTURAL_DEFAULTS: Record<string, StructuralConfig> = {
  line: {
    showDots: false,
    showArea: false,
    curve: "monotone",
    showLegend: false,
    labelPosition: "direct",
    showGridlines: false,
    titleAlignment: "left",
  },
  area: {
    showDots: false,
    showArea: true,
    curve: "monotone",
    showLegend: false,
    labelPosition: "direct",
    showGridlines: false,
    titleAlignment: "left",
  },
  bar_vertical: {
    barPadding: 0.2,
    showGridlines: false,
    showValues: false,
    showLegend: false,
    titleAlignment: "left",
    radius: [4, 4, 0, 0],
  },
  bar_horizontal: {
    barPadding: 0.2,
    showGridlines: false,
    showValues: false,
    showLegend: false,
    titleAlignment: "left",
    radius: [0, 4, 4, 0],
  },
  bar_stacked: {
    barPadding: 0.2,
    showGridlines: false,
    showValues: false,
    showLegend: true,
    titleAlignment: "left",
  },
  bar_grouped: {
    barPadding: 0.2,
    showGridlines: false,
    showValues: false,
    showLegend: true,
    titleAlignment: "left",
  },
  pie: {
    innerRadius: 0,
    showLabels: true,
    labelPosition: "outside",
    showPercentages: true,
    showLegend: false,
    titleAlignment: "left",
  },
  donut: {
    innerRadius: 0.5,
    showLabels: true,
    labelPosition: "outside",
    showPercentages: true,
    showLegend: false,
    titleAlignment: "left",
  },
  scatter: {
    showGridlines: false,
    showLegend: false,
    titleAlignment: "left",
  },
  histogram: {
    barPadding: 0.05,
    showGridlines: false,
    showValues: false,
    titleAlignment: "left",
  },
  heatmap: {
    showValues: false,
    showLegend: true,
    titleAlignment: "left",
  },
  treemap: {
    showLabels: true,
    showLegend: false,
    titleAlignment: "left",
  },
  kpi_card: {
    titleAlignment: "left",
  },
  data_table: {
    sortable: true,
    paginated: true,
    pageSize: 10,
    striped: false,
    titleAlignment: "left",
  },
  combo: {
    showLegend: true,
    titleAlignment: "left",
  },
};

/**
 * Get structural config for a chart type, with fallback to empty object.
 */
export function getStructuralConfig(chartType: string): StructuralConfig {
  return STRUCTURAL_DEFAULTS[chartType] || {};
}

// =============================================================================
// Element Classification Types
// =============================================================================

export interface ElementClassification {
  prominence: Prominence;
  purpose: string;
}

// =============================================================================
// Element Defaults (consistent across all charts)
// =============================================================================

/**
 * Default classifications for structural elements.
 * These are consistent across all chart types - UI style guide decisions.
 */
export const ELEMENT_DEFAULTS: Record<string, ElementClassification> = {
  chartBorder: { prominence: "hide", purpose: "structural" },
  gridlines: { prominence: "hide", purpose: "structural" },
  xAxisLine: { prominence: "baseline", purpose: "structural" },
  yAxisLine: { prominence: "hide", purpose: "structural" },
  xAxisLabels: { prominence: "baseline", purpose: "navigational" },
  yAxisLabels: { prominence: "baseline", purpose: "navigational" },
  xAxisTitle: { prominence: "baseline", purpose: "navigational" },
  yAxisTitle: { prominence: "baseline", purpose: "navigational" },
  title: { prominence: "primary", purpose: "navigational" },
  subtitle: { prominence: "secondary", purpose: "navigational" },
  legend: { prominence: "hide", purpose: "navigational" },
};

/**
 * Get element classification, with fallback to baseline/structural.
 */
export function getElementClassification(elementId: string): ElementClassification {
  return (
    ELEMENT_DEFAULTS[elementId] || { prominence: "baseline", purpose: "structural" }
  );
}
