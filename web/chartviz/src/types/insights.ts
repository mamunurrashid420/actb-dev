/**
 * Insight and Recommendation types for the ChartWithInsights composite component.
 *
 * Re-exports generated protobuf types from @actbi/shared/proto.
 * Color mapping is handled via createInsightColorMap() utility in registry.ts.
 */

// Re-export generated types from shared proto
export {
  type Insight,
  type Recommendation,
  type Highlight,
  type InsightTarget,
  Insight as InsightFns,
  Recommendation as RecommendationFns,
  Highlight as HighlightFns,
  InsightTarget as InsightTargetFns,
  InsightType,
  RecommendationType,
  HighlightType,
  insightTypeFromJSON,
  insightTypeToJSON,
  recommendationTypeFromJSON,
  recommendationTypeToJSON,
  highlightTypeFromJSON,
  highlightTypeToJSON,
} from "@actbi/shared/proto";
