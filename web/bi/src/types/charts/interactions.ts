export interface ChartDataPoint {
  label?: string;
  name?: string;
  value: number;
  [key: string]: unknown;
}

export type ChartInteractionType =
  | "click"
  | "doubleclick"
  | "hover"
  | "rightclick"
  | "keypress";

export interface ChartInteractionEvent {
  type: ChartInteractionType;
  data: ChartDataPoint;
  index: number;
  position: { x: number; y: number };
  actions: string[];
}

export type ChartModificationType =
  | "filter"
  | "transform"
  | "highlight"
  | "annotate"
  | "sort"
  | "aggregate";

export interface ChartModification {
  type: ChartModificationType;
  targetIndex?: number;
  parameters: Record<string, unknown>;
}

export interface ChartAnalysisRequest {
  chartType:
    | "bar_chart_vertical"
    | "line_chart"
    | "area_chart"
    | "pie_chart"
    | "donut_chart"
    | "funnel_chart";
  selectedData: ChartDataPoint;
  fullDataset: ChartDataPoint[];
  context: string;
  action: "explain" | "compare" | "trend" | "insight";
}

export interface ChartAnalysisResponse {
  analysis: string;
  summary: string;
  suggestions: string[];
  insights?: string[];
  recommendations?: string[];
  modifications?: {
    highlightIndices?: number[];
    annotations?: Array<{
      x: number;
      y: number;
      label: string;
    }>;
  };
  visualization?: {
    type: string;
    data: ChartDataPoint[];
  };
}

export interface ChartModificationRequest {
  currentChart: {
    type: string;
    data: ChartDataPoint[];
    config: Record<string, unknown>;
  };
  userRequest: string;
  context: string;
}

export interface ChartModificationResponse {
  modifiedChart: {
    type: string;
    data: ChartDataPoint[];
    config: Record<string, unknown>;
  };
  explanation: string;
  transitionAnimation: "fade" | "slide" | "morph";
}
