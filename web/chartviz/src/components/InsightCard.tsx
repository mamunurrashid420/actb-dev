"use client";

import type { Insight, Recommendation } from "@/types/insights";

interface InsightCardProps {
  insight: Insight;
  index: number;
  color: string;
  isEmphasized: boolean;
  onHover: () => void;
  onLeave: () => void;
  onRecommendationClick?: (recommendation: Recommendation) => void;
}

/**
 * Individual insight card with numbered description and recommendation buttons.
 * Color-coded to match chart highlights via the insight's color from the color map.
 */
export function InsightCard({
  insight,
  index,
  color,
  isEmphasized,
  onHover,
  onLeave,
  onRecommendationClick,
}: InsightCardProps) {
  return (
    <div
      className="transition-all duration-200"
      onMouseEnter={onHover}
      onMouseLeave={onLeave}
      style={{
        opacity: isEmphasized ? 1 : 0.85,
        transform: isEmphasized ? "scale(1.01)" : "scale(1)",
      }}
    >
      {/* Insight Number and Summary */}
      <div className="flex gap-2">
        <span className="shrink-0 font-medium" style={{ color }}>
          {index + 1}.
        </span>
        <p className="text-foreground text-sm leading-relaxed">{insight.summary}</p>
      </div>

      {/* Confidence indicator */}
      {insight.confidence !== undefined && (
        <div className="mt-2 flex items-center gap-2 pl-5">
          <div className="bg-muted h-1.5 w-16 overflow-hidden rounded-full">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${insight.confidence * 100}%`,
                backgroundColor: color,
              }}
            />
          </div>
          <span className="text-muted-foreground text-xs">
            {Math.round(insight.confidence * 100)}% confident
          </span>
        </div>
      )}

      {/* Recommendations */}
      {insight.recommendations.length > 0 && (
        <div className="mt-3 pl-5">
          <p className="text-muted-foreground mb-2 text-xs font-medium uppercase tracking-wide">
            Recommended action
          </p>
          <div className="flex flex-col gap-2">
            {insight.recommendations.map((rec) => (
              <button
                key={rec.id}
                className="hover:bg-muted/50 bg-card text-foreground rounded-md border px-3 py-2 text-left text-sm transition-colors"
                style={{
                  borderLeftWidth: "3px",
                  borderLeftColor: color,
                }}
                onClick={() => onRecommendationClick?.(rec)}
              >
                {rec.summary}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
