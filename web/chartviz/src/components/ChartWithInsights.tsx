"use client";

import { useState, useMemo } from "react";
import { ResponsiveChartContainer } from "./ResponsiveChartContainer";
import { InsightsPanel } from "./InsightsPanel";
import { createInsightColorMap } from "@/lib/charts/registry";
import type { ChartSpec, ChartDataSlice } from "@/lib/charts/factory";
import type { Highlight } from "@/lib/charts/registry";
import type { Insight, Recommendation } from "@/types/insights";

interface ChartWithInsightsProps {
  /** Chart specification */
  spec: ChartSpec;
  /** Chart data */
  data: ChartDataSlice;
  /** Highlights linking to insights */
  highlights: Highlight[];
  /** Insights for this chart */
  insights: Insight[];
  /** Chart height */
  height?: number;
  /** Callback when a recommendation is clicked */
  onRecommendationClick?: (recommendation: Recommendation) => void;
  /** Whether to show the insights panel */
  showInsights?: boolean;
}

/**
 * Composite component combining a chart with its insights panel.
 * Manages bidirectional hover linking and color coordination between
 * chart highlights and insights via a shared color map.
 */
export function ChartWithInsights({
  spec,
  data,
  highlights,
  insights,
  height = 300,
  onRecommendationClick,
  showInsights = true,
}: ChartWithInsightsProps) {
  const [hoveredInsightId, setHoveredInsightId] = useState<string | null>(null);
  const [isPanelVisible, setIsPanelVisible] = useState(showInsights);

  // Filter insights relevant to this chart (by target.chartId)
  const chartInsights = useMemo(() => {
    return insights.filter((insight) => insight.target?.chartId === spec.id);
  }, [insights, spec.id]);

  // Create color map from highlights - kept separate for flexibility
  const colorMap = useMemo(() => createInsightColorMap(highlights), [highlights]);

  const hasInsights = chartInsights.length > 0;

  return (
    <div className="bg-card overflow-hidden rounded-lg border shadow-sm">
      {/* Header */}
      <div className="bg-muted/30 flex items-center justify-between border-b px-4 py-3">
        <h2 className="text-foreground font-semibold">{spec.title}</h2>
        {hasInsights && (
          <button
            className={`rounded-md p-1.5 text-lg transition-colors ${
              isPanelVisible
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-muted"
            }`}
            onClick={() => setIsPanelVisible(!isPanelVisible)}
            aria-label={isPanelVisible ? "Hide insights" : "Show insights"}
            title={isPanelVisible ? "Hide insights" : "Show insights"}
          >
            💡
          </button>
        )}
      </div>

      {/* Content: Chart + Insights Panel */}
      <div className="flex flex-col p-4 lg:flex-row lg:gap-6">
        {/* Chart Section */}
        <div className="min-w-0 flex-1">
          <ResponsiveChartContainer
            spec={spec}
            data={data}
            highlights={highlights}
            height={height}
          />
        </div>

        {/* Insights Panel */}
        {hasInsights && isPanelVisible && (
          <div className="mt-4 shrink-0 border-t pt-4 lg:mt-0 lg:w-80 lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0">
            <InsightsPanel
              insights={chartInsights}
              highlights={highlights}
              colorMap={colorMap}
              hoveredInsightId={hoveredInsightId}
              onInsightHover={setHoveredInsightId}
              onInsightLeave={() => setHoveredInsightId(null)}
              onRecommendationClick={onRecommendationClick}
            />
          </div>
        )}
      </div>
    </div>
  );
}
