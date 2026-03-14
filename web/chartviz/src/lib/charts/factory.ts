import { createElement } from "react";
import {
  getChartComponent,
  getAvailableChartTypes,
  BaseChartProps,
  Dimension,
  Filter,
  Highlight,
  // Semantic types - re-export for convenience
  DataMapping,
  DataSeriesClassification,
  ValueRange,
  Prominence,
  Purpose,
  Sentiment,
} from "./registry";

// Re-export semantic types for consumers
export type {
  DataMapping,
  DataSeriesClassification,
  ValueRange,
  Prominence,
  Purpose,
  Sentiment,
};

// =============================================================================
// API Response Types (matching protobuf structure)
// =============================================================================

export interface ChartSpec {
  id: string;
  title: string;
  chart_type: string;
  dimensions: Dimension[];
  filters?: Filter[];
  chart_data_slice_ids?: string[];

  // Semantic metadata from agent
  data_mapping?: DataMapping;
  data_series?: DataSeriesClassification[];
  highlights?: Highlight[];

  version?: number;
  schema_version?: number;

  // For combo charts: child chart specs, each rendered independently.
  // Sub-charts inherit parent's chart_data_slice_ids if their own is empty.
  sub_charts?: ChartSpec[];
}

export interface ChartDataSlice {
  schema_id: string;
  rows: Array<Record<string, any>>;
}

// =============================================================================
// Props Transformer
// =============================================================================

/**
 * Transforms API spec + data into component props.
 * Can be customized per chart type for complex transformations.
 */
export interface PropsTransformer {
  (spec: ChartSpec, data: ChartDataSlice, highlights?: Highlight[]): BaseChartProps;
}

// Default transformer - works for most chart types
const defaultTransformer: PropsTransformer = (spec, data, highlights) => ({
  data,
  dimensions: spec.dimensions,
  filters: spec.filters,
  title: spec.title,
  highlights,
  // Pass semantic metadata from agent to UI components
  dataMapping: spec.data_mapping,
  dataSeries: spec.data_series,
});

// Chart-specific transformers registry
const transformers: Record<string, PropsTransformer> = {
  default: defaultTransformer,
};

/**
 * Register a custom props transformer for a chart type.
 * Useful for charts that need special data transformations.
 */
export function registerTransformer(
  chartType: string,
  transformer: PropsTransformer,
): void {
  transformers[chartType] = transformer;
}

/**
 * Get transformer for a chart type, falls back to default
 */
export function getTransformer(chartType: string): PropsTransformer {
  return transformers[chartType] || transformers.default;
}

// =============================================================================
// Chart Factory
// =============================================================================

/**
 * Fallback chart type used when the requested type has no registered component.
 * data_table can render any data, so it's a safe universal fallback.
 */
const FALLBACK_CHART_TYPE = "data_table";

/**
 * Create a chart element from a spec and data.
 * This is the main factory function used by dashboards/pages.
 *
 * If the requested chart_type has no registered component, falls back to
 * data_table rendering (since the protobuf ChartType enum is the source of
 * truth and may contain types not yet implemented in the frontend).
 *
 * @param spec - Chart specification from API
 * @param data - Data slice for the chart
 * @param highlights - Optional highlights for insights
 * @param additionalProps - Additional props to merge (width, height, etc.)
 * @returns React element
 */
export function createChart(
  spec: ChartSpec,
  data: ChartDataSlice,
  highlights?: Highlight[],
  additionalProps?: Partial<BaseChartProps>,
) {
  let Component = getChartComponent(spec.chart_type);
  let effectiveChartType = spec.chart_type;

  if (!Component) {
    console.warn(
      `Chart type "${spec.chart_type}" not yet implemented. Falling back to ${FALLBACK_CHART_TYPE}. ` +
        `Available types: ${getAvailableChartTypesForError()}`,
    );
    Component = getChartComponent(FALLBACK_CHART_TYPE);
    effectiveChartType = FALLBACK_CHART_TYPE;

    if (!Component) {
      throw new Error(
        `Fallback chart type "${FALLBACK_CHART_TYPE}" is not registered. ` +
          `Ensure initializeChartRegistry() has been called.`,
      );
    }
  }

  // Get transformer for this chart type or use default
  const transformer = getTransformer(effectiveChartType);

  // Transform spec + data into props
  const props = transformer(spec, data, highlights);

  // Merge with any additional props
  const finalProps = { ...props, ...additionalProps };

  return createElement(Component, finalProps);
}

/**
 * Safely create a chart, returning null on error instead of throwing
 */
export function createChartSafe(
  spec: ChartSpec,
  data: ChartDataSlice,
  highlights?: Highlight[],
  additionalProps?: Partial<BaseChartProps>,
): React.ReactElement | null {
  try {
    return createChart(spec, data, highlights, additionalProps);
  } catch (error) {
    console.error("Failed to create chart:", error);
    return null;
  }
}

// Helper to get available chart types for error messages
function getAvailableChartTypesForError(): string {
  return getAvailableChartTypes().join(", ") || "none registered";
}

// =============================================================================
// Utility Types for Dashboard Integration
// =============================================================================

export interface ChartWithData {
  spec: ChartSpec;
  data: ChartDataSlice;
  highlights?: Highlight[];
}

/**
 * Create multiple charts from an array of chart+data objects
 */
export function createCharts(
  charts: ChartWithData[],
  additionalProps?: Partial<BaseChartProps>,
): (React.ReactElement | null)[] {
  return charts.map(({ spec, data, highlights }) =>
    createChartSafe(spec, data, highlights, additionalProps),
  );
}
