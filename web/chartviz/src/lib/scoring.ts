/**
 * Scoring logic for viz designer evaluation.
 *
 * Ported from notebooks/agents/viz_designer/viz_selector.ipynb
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type MatchType = "full" | "alternative" | "none";

export interface Alternative {
  chart_type: string;
  tradeoff?: string;
}

export interface TestResult {
  test_id: string;
  expected: string;
  selected: string;
  alternatives: string[];
  match_type: MatchType;
  score: number;
}

export interface SummaryStats {
  total: number;
  fullMatches: number;
  altMatches: number;
  misses: number;
  totalScore: number;
  averageScore: number;
}

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

/**
 * Calculate score based on chart type matching.
 *
 * - Full match  = 1.0
 * - Alternative = 0.8 / number_of_alternatives
 * - No match    = 0.0
 */
export function calculateScore(
  selectedChartType: string,
  expectedChartType: string,
  alternatives: Alternative[] = [],
): { score: number; matchType: MatchType } {
  if (selectedChartType === expectedChartType) {
    return { score: 1.0, matchType: "full" };
  }

  for (const alt of alternatives) {
    if (alt.chart_type === expectedChartType) {
      return {
        score: alternatives.length > 0 ? 0.8 / alternatives.length : 0,
        matchType: "alternative",
      };
    }
  }

  return { score: 0.0, matchType: "none" };
}

/**
 * Compute summary statistics from a list of test results.
 */
export function computeSummary(results: TestResult[]): SummaryStats {
  const total = results.length;
  const fullMatches = results.filter((r) => r.match_type === "full").length;
  const altMatches = results.filter((r) => r.match_type === "alternative").length;
  const misses = results.filter((r) => r.match_type === "none").length;
  const totalScore = results.reduce((sum, r) => sum + r.score, 0);

  return {
    total,
    fullMatches,
    altMatches,
    misses,
    totalScore,
    averageScore: total > 0 ? totalScore / total : 0,
  };
}
