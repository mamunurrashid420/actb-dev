"use client";

import { InsightCard } from "./InsightCard";
import { getHighlightColor } from "@/lib/charts/registry";
import type { Insight, Recommendation } from "@/types/insights";
import type { Highlight } from "@/lib/charts/registry";

interface InsightsPanelProps {
  insights: Insight[];
  highlights: Highlight[];
  colorMap: Map<string, string>;
  hoveredInsightId: string | null;
  onInsightHover: (insightId: string) => void;
  onInsightLeave: () => void;
  onRecommendationClick?: (recommendation: Recommendation) => void;
}

/**
 * Panel displaying insights and recommendations for a chart.
 * Coordinates with the chart via hover state and color map.
 */
export function InsightsPanel({
  insights,
  highlights,
  colorMap,
  hoveredInsightId,
  onInsightHover,
  onInsightLeave,
  onRecommendationClick,
}: InsightsPanelProps) {
  if (insights.length === 0) {
    return null;
  }

  // Get color for an insight by finding its associated highlight
  const getInsightColor = (insightId: string): string => {
    const highlight = highlights.find((h) => h.insightId === insightId);
    if (highlight) {
      return getHighlightColor(highlight.insightId, colorMap);
    }
    return getHighlightColor(insightId, colorMap);
  };

  return (
    <div className="flex flex-col">
      {/* Header */}
      <div className="mb-4 flex items-center gap-2">
        <span className="text-base">💡</span>
        <h3 className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">
          Insights and Recommendations
        </h3>
      </div>

      {/* Insights List */}
      <div className="flex flex-col gap-4">
        {insights.map((insight, index) => (
          <InsightCard
            key={insight.id}
            insight={insight}
            index={index}
            color={getInsightColor(insight.id)}
            isEmphasized={hoveredInsightId === insight.id}
            onHover={() => onInsightHover(insight.id)}
            onLeave={onInsightLeave}
            onRecommendationClick={onRecommendationClick}
          />
        ))}
      </div>
    </div>
  );
}
