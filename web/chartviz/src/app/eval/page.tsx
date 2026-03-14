"use client";

import { useState, useCallback, useRef, useMemo } from "react";
import Link from "next/link";
import yaml from "js-yaml";
import { initializeChartRegistry } from "@/components/charts";
import { ChartWithInsights } from "@/components/ChartWithInsights";
import {
  createVisualization,
  type VisualizationCreateResponse,
} from "@/lib/api-client";
import {
  calculateScore,
  computeSummary,
  type TestResult,
  type SummaryStats,
  type MatchType,
} from "@/lib/scoring";
import type { ChartSpec, ChartDataSlice } from "@/lib/charts/factory";
import type { Highlight, Insight } from "@/types/insights";
import { HighlightFns, InsightFns } from "@/types/insights";

// Ensure chart components are registered
initializeChartRegistry();

// ---------------------------------------------------------------------------
// YAML Test Case types
// ---------------------------------------------------------------------------

interface TestCaseField {
  name: string;
  type: string;
  role: string;
  context: string;
}

interface TestCaseSchema {
  id: string;
  version: number;
  fields: TestCaseField[];
  primary_key: string[];
  schema_version: number;
}

interface TestCase {
  id: string;
  nlp_query: string;
  expected_chart: {
    id: string;
    title: string;
    chart_type: string;
    dimensions: { field: string; type: string }[];
    filters: { field: string; operator: string; value: string }[];
    version: number;
    schema_version: number;
  };
  output_schema: TestCaseSchema;
  materialized_data: {
    schema_id: string;
    rows: Record<string, unknown>[];
  };
}

// ---------------------------------------------------------------------------
// Per-test-case evaluation result
// ---------------------------------------------------------------------------

interface EvalResult {
  testCase: TestCase;
  response?: VisualizationCreateResponse;
  error?: string;
  testResult?: TestResult;
  status: "pending" | "running" | "done" | "error";
}

// =============================================================================
// Helper Components
// =============================================================================

function MatchBadge({ matchType }: { matchType: MatchType }) {
  const config: Record<MatchType, { label: string; className: string }> = {
    full: {
      label: "Full Match",
      className:
        "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
    },
    alternative: {
      label: "Alt Match",
      className: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
    },
    none: {
      label: "Miss",
      className: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
    },
  };
  const { label, className } = config[matchType];
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${className}`}
    >
      {matchType === "full" && "✓ "}
      {matchType === "alternative" && "~ "}
      {matchType === "none" && "✗ "}
      {label}
    </span>
  );
}

function ChartTypeBadge({
  type,
  variant = "default",
}: {
  type: string;
  variant?: "default" | "expected" | "selected";
}) {
  const colors = {
    default: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
    expected: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300",
    selected:
      "bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-300",
  };
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${colors[variant]}`}
    >
      {type}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Summary Section
// ---------------------------------------------------------------------------

function SummaryPanel({
  stats,
  results,
}: {
  stats: SummaryStats;
  results: TestResult[];
}) {
  return (
    <div className="bg-card mb-8 rounded-lg border p-6">
      <h2 className="mb-4 text-xl font-semibold">Summary</h2>

      {/* Score overview */}
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-5">
        <div className="bg-muted/30 rounded-lg p-3 text-center">
          <div className="text-muted-foreground text-xs uppercase">Total</div>
          <div className="text-2xl font-bold">{stats.total}</div>
        </div>
        <div className="rounded-lg bg-emerald-50 p-3 text-center dark:bg-emerald-950/30">
          <div className="text-xs uppercase text-emerald-600 dark:text-emerald-400">
            Full
          </div>
          <div className="text-2xl font-bold text-emerald-700 dark:text-emerald-300">
            {stats.fullMatches}
          </div>
        </div>
        <div className="rounded-lg bg-amber-50 p-3 text-center dark:bg-amber-950/30">
          <div className="text-xs uppercase text-amber-600 dark:text-amber-400">
            Alt
          </div>
          <div className="text-2xl font-bold text-amber-700 dark:text-amber-300">
            {stats.altMatches}
          </div>
        </div>
        <div className="rounded-lg bg-red-50 p-3 text-center dark:bg-red-950/30">
          <div className="text-xs uppercase text-red-600 dark:text-red-400">Miss</div>
          <div className="text-2xl font-bold text-red-700 dark:text-red-300">
            {stats.misses}
          </div>
        </div>
        <div className="bg-muted/30 rounded-lg p-3 text-center">
          <div className="text-muted-foreground text-xs uppercase">Avg Score</div>
          <div className="text-2xl font-bold">{stats.averageScore.toFixed(2)}</div>
        </div>
      </div>

      {/* Score bar */}
      <div className="mb-4">
        <div className="text-muted-foreground mb-1 flex justify-between text-sm">
          <span>Total Score</span>
          <span>
            {stats.totalScore.toFixed(2)} / {stats.total.toFixed(2)}
          </span>
        </div>
        <div className="bg-muted h-3 overflow-hidden rounded-full">
          <div
            className="h-full rounded-full bg-emerald-500 transition-all"
            style={{
              width: `${stats.total > 0 ? (stats.totalScore / stats.total) * 100 : 0}%`,
            }}
          />
        </div>
      </div>

      {/* Results table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="text-muted-foreground border-b text-xs uppercase">
              <th className="px-3 py-2">Test ID</th>
              <th className="px-3 py-2">Expected</th>
              <th className="px-3 py-2">Selected</th>
              <th className="px-3 py-2">Match</th>
              <th className="px-3 py-2 text-right">Score</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => (
              <tr key={r.test_id} className="border-b last:border-0">
                <td className="px-3 py-2 font-mono text-xs">{r.test_id}</td>
                <td className="px-3 py-2">
                  <ChartTypeBadge type={r.expected} variant="expected" />
                </td>
                <td className="px-3 py-2">
                  <ChartTypeBadge type={r.selected} variant="selected" />
                </td>
                <td className="px-3 py-2">
                  <MatchBadge matchType={r.match_type} />
                </td>
                <td className="px-3 py-2 text-right font-mono">{r.score.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Data Preview Table
// ---------------------------------------------------------------------------

function DataPreview({
  schema,
  rows,
}: {
  schema: TestCaseSchema;
  rows: Record<string, unknown>[];
}) {
  const displayRows = rows.slice(0, 5);
  const fields = schema.fields;

  return (
    <div className="overflow-x-auto">
      {/* Schema info */}
      <div className="text-muted-foreground mb-2 text-xs">
        Schema: <code className="bg-muted rounded px-1">{schema.id}</code> |{" "}
        {fields.length} fields | {rows.length} rows (showing {displayRows.length})
      </div>

      <table className="w-full text-left text-xs">
        <thead>
          <tr className="border-b">
            {fields.map((f) => (
              <th key={f.name} className="px-2 py-1.5">
                <div className="font-semibold">{f.name}</div>
                <div className="text-muted-foreground font-normal">
                  {f.type} / {f.role}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {displayRows.map((row, i) => (
            <tr key={i} className="border-b last:border-0">
              {fields.map((f) => (
                <td key={f.name} className="px-2 py-1.5 font-mono">
                  {String(row[f.name] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > 5 && (
        <div className="text-muted-foreground mt-1 text-xs italic">
          ... and {rows.length - 5} more rows
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// API Response → Proto Type Mappers
// ---------------------------------------------------------------------------

/**
 * Map raw API highlights (snake_case) to typed proto Highlight objects.
 * Uses the generated Highlight.fromJSON() which handles both snake_case
 * and camelCase field names automatically.
 */
function mapHighlights(raw: Record<string, unknown>[]): Highlight[] {
  return raw.map((h) => HighlightFns.fromJSON(h));
}

/**
 * Map raw API insights (snake_case) to typed proto Insight objects.
 * Injects target.chartId so ChartWithInsights can filter by chart.
 * Uses the generated Insight.fromJSON() which handles both snake_case
 * and camelCase field names automatically.
 */
function mapInsights(raw: Record<string, unknown>[], chartId: string): Insight[] {
  return raw.map((ins) => {
    const insight = InsightFns.fromJSON(ins);
    // Ensure target.chartId is set so ChartWithInsights can filter
    if (!insight.target) {
      insight.target = { chartId, chartStackId: undefined, dashboardId: undefined };
    } else if (!insight.target.chartId) {
      insight.target.chartId = chartId;
    }
    return insight;
  });
}

// ---------------------------------------------------------------------------
// Agent Response Card
// ---------------------------------------------------------------------------

function AgentResponseCard({
  response,
  chartSpec,
}: {
  response: VisualizationCreateResponse;
  chartSpec: ChartSpec;
}) {
  // Extract useful info from the chart spec
  const dataMapping = chartSpec.data_mapping;
  const dataSeries = chartSpec.data_series;

  // Try to extract the data for rendering
  const chartData: ChartDataSlice = {
    schema_id: response.data_slice_id ?? "eval",
    rows: Array.isArray(response.data)
      ? (response.data as Record<string, unknown>[])
      : (((response.data as Record<string, unknown>)?.rows as
          | Record<string, unknown>[]
          | undefined) ?? []),
  };

  // Map API response highlights/insights to typed proto objects
  const highlights = useMemo(
    () => mapHighlights(response.highlights ?? []),
    [response.highlights],
  );
  const insights = useMemo(
    () => mapInsights(response.insights ?? [], chartSpec.id),
    [response.insights, chartSpec.id],
  );

  return (
    <div className="space-y-4">
      {/* Chart type & title */}
      <div>
        <div className="mb-1 text-sm font-medium">Selected Chart</div>
        <div className="flex items-center gap-2">
          <ChartTypeBadge type={chartSpec.chart_type} variant="selected" />
          <span className="text-muted-foreground text-sm">{chartSpec.title}</span>
        </div>
      </div>

      {/* Data mapping */}
      {dataMapping && (
        <div>
          <div className="mb-1 text-sm font-medium">Data Mapping</div>
          <div className="bg-muted/30 flex flex-wrap gap-2 rounded p-2 text-xs">
            {Object.entries(dataMapping)
              .filter(([, v]) => v != null)
              .map(([key, value]) => (
                <span key={key} className="bg-background rounded border px-2 py-0.5">
                  <span className="text-muted-foreground">{key}:</span> {String(value)}
                </span>
              ))}
          </div>
        </div>
      )}

      {/* Data series summary */}
      {dataSeries && dataSeries.length > 0 && (
        <div>
          <div className="mb-1 text-sm font-medium">
            Data Series ({dataSeries.length})
          </div>
          <div className="flex flex-wrap gap-1">
            {dataSeries.map((s, idx) => (
              <span
                key={s.seriesId ?? idx}
                className="bg-muted/50 rounded border px-2 py-0.5 text-xs"
              >
                {s.label ?? s.seriesId}: {s.prominence} / {s.purpose}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Chart with Highlights & Insights Panel */}
      {chartData.rows.length > 0 && (
        <ChartWithInsights
          spec={chartSpec}
          data={chartData}
          highlights={highlights}
          insights={insights}
          height={280}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Test Case Card
// ---------------------------------------------------------------------------

function TestCaseCard({ result }: { result: EvalResult }) {
  const { testCase, response, error, testResult, status } = result;

  // Parse the chart spec from API response
  const chartSpec: ChartSpec | null = response?.chart_spec
    ? {
        id: String(response.chart_spec.id ?? ""),
        title: String(response.chart_spec.title ?? ""),
        chart_type: String(response.chart_spec.chart_type ?? ""),
        dimensions: (response.chart_spec.dimensions as ChartSpec["dimensions"]) ?? [],
        filters: (response.chart_spec.filters as ChartSpec["filters"]) ?? [],
        data_mapping: response.chart_spec.data_mapping as ChartSpec["data_mapping"],
        data_series: response.chart_spec.data_series as ChartSpec["data_series"],
        chart_data_slice_ids:
          (response.chart_spec.chart_data_slice_ids as string[]) ?? undefined,
        version: Number(response.chart_spec.version ?? 1),
        schema_version: Number(response.chart_spec.schema_version ?? 1),
        sub_charts:
          (response.chart_spec.sub_charts as ChartSpec["sub_charts"]) ?? undefined,
      }
    : null;

  return (
    <div className="bg-card overflow-hidden rounded-lg border">
      {/* Header */}
      <div className="bg-muted/30 flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-3">
          <code className="text-sm font-semibold">{testCase.id}</code>
          <ChartTypeBadge
            type={testCase.expected_chart.chart_type}
            variant="expected"
          />
          {status === "running" && (
            <span className="text-muted-foreground animate-pulse text-xs">
              Running...
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {testResult && <MatchBadge matchType={testResult.match_type} />}
          {testResult && (
            <span className="bg-muted rounded px-2 py-0.5 font-mono text-xs">
              {testResult.score.toFixed(2)}
            </span>
          )}
        </div>
      </div>

      <div className="p-4">
        {/* NLP Query */}
        <div className="mb-4">
          <div className="text-muted-foreground mb-1 text-xs font-medium uppercase">
            Query
          </div>
          <div className="bg-muted/30 rounded-lg p-3 text-sm italic">
            &quot;{testCase.nlp_query}&quot;
          </div>
        </div>

        {/* Data Preview */}
        <div className="mb-4">
          <div className="text-muted-foreground mb-1 text-xs font-medium uppercase">
            Test Data
          </div>
          <div className="bg-muted/20 rounded-lg p-3">
            <DataPreview
              schema={testCase.output_schema}
              rows={testCase.materialized_data.rows}
            />
          </div>
        </div>

        {/* Agent Response */}
        {status === "done" && response && chartSpec && (
          <div>
            <div className="text-muted-foreground mb-1 text-xs font-medium uppercase">
              Agent Response
            </div>
            <div className="bg-muted/20 rounded-lg p-3">
              <AgentResponseCard response={response} chartSpec={chartSpec} />
            </div>
          </div>
        )}

        {/* Error */}
        {status === "error" && error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950/30 dark:text-red-300">
            <div className="mb-1 font-medium">Error</div>
            {error}
          </div>
        )}

        {/* Pending state */}
        {status === "pending" && (
          <div className="text-muted-foreground py-4 text-center text-sm">
            Waiting to run...
          </div>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function EvalPage() {
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [evalResults, setEvalResults] = useState<EvalResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [apiUrl, setApiUrl] = useState(
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  );
  const [modelOverride, setModelOverride] = useState("");
  const [fileName, setFileName] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef(false);

  // Computed summary
  const completedResults = evalResults
    .filter((r) => r.testResult)
    .map((r) => r.testResult!);
  const summary: SummaryStats | null =
    completedResults.length > 0 ? computeSummary(completedResults) : null;

  // -------------------------------------------------------------------------
  // File Upload Handler
  // -------------------------------------------------------------------------

  const handleFileUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setFileName(file.name);

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target?.result as string;
        const data = yaml.load(text) as { test_cases?: TestCase[] };
        const cases = data?.test_cases;
        if (!cases || !Array.isArray(cases)) {
          alert("Invalid YAML: no test_cases array found");
          return;
        }
        setTestCases(cases);
        setEvalResults(
          cases.map((tc) => ({
            testCase: tc,
            status: "pending" as const,
          })),
        );
      } catch (err) {
        alert(`YAML parse error: ${err instanceof Error ? err.message : String(err)}`);
      }
    };
    reader.readAsText(file);
  }, []);

  // -------------------------------------------------------------------------
  // Run All Test Cases
  // -------------------------------------------------------------------------

  const runAll = useCallback(async () => {
    if (testCases.length === 0) return;
    setIsRunning(true);
    abortRef.current = false;
    setProgress({ current: 0, total: testCases.length });

    // Reset results
    const freshResults: EvalResult[] = testCases.map((tc) => ({
      testCase: tc,
      status: "pending" as const,
    }));
    setEvalResults(freshResults);

    for (let i = 0; i < testCases.length; i++) {
      if (abortRef.current) break;

      const tc = testCases[i];

      // Mark running
      setEvalResults((prev) =>
        prev.map((r, idx) => (idx === i ? { ...r, status: "running" as const } : r)),
      );

      try {
        const response = await createVisualization(
          {
            nlp_query: tc.nlp_query,
            output_schema: { ...tc.output_schema },
            materialized_data: tc.materialized_data.rows,
            model: modelOverride || undefined,
          },
          apiUrl,
        );

        const selectedType = String(
          (response.chart_spec as Record<string, unknown>)?.chart_type ?? "",
        );
        const expectedType = tc.expected_chart.chart_type;

        // Extract alternatives from chart_spec if present (future-proofing)
        const alternatives =
          ((response.chart_spec as Record<string, unknown>)?.alternatives as
            | { chart_type: string; tradeoff?: string }[]
            | undefined) ?? [];

        const { score, matchType } = calculateScore(
          selectedType,
          expectedType,
          alternatives,
        );

        const testResult: TestResult = {
          test_id: tc.id,
          expected: expectedType,
          selected: selectedType,
          alternatives: alternatives.map((a) => a.chart_type),
          match_type: matchType,
          score,
        };

        setEvalResults((prev) =>
          prev.map((r, idx) =>
            idx === i ? { ...r, response, testResult, status: "done" as const } : r,
          ),
        );
      } catch (err) {
        setEvalResults((prev) =>
          prev.map((r, idx) =>
            idx === i
              ? {
                  ...r,
                  error: err instanceof Error ? err.message : String(err),
                  status: "error" as const,
                }
              : r,
          ),
        );
      }

      setProgress({ current: i + 1, total: testCases.length });
    }

    setIsRunning(false);
  }, [testCases, apiUrl, modelOverride]);

  const stopRun = useCallback(() => {
    abortRef.current = true;
  }, []);

  // =========================================================================
  // Render
  // =========================================================================

  return (
    <main className="bg-background min-h-screen p-4 md:p-8">
      <div className="mx-auto max-w-6xl">
        {/* Header */}
        <header className="mb-8">
          <div className="mb-2 flex items-center gap-3">
            <Link
              href="/"
              className="text-muted-foreground hover:text-foreground text-sm transition"
            >
              &larr; Home
            </Link>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">Viz Designer Eval</h1>
          <p className="text-muted-foreground mt-2">
            Upload YAML test cases, run them against the playground viz_designer API,
            and evaluate chart selection accuracy.
          </p>
        </header>

        {/* Controls */}
        <div className="bg-card mb-8 rounded-lg border p-6">
          <div className="grid gap-4 md:grid-cols-2">
            {/* File upload */}
            <div>
              <label className="text-muted-foreground mb-1 block text-xs font-medium uppercase">
                Test Data (YAML)
              </label>
              <div className="flex items-center gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".yaml,.yml"
                  onChange={handleFileUpload}
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="bg-muted hover:bg-muted/80 rounded-md border px-4 py-2 text-sm font-medium transition"
                >
                  Choose File
                </button>
                <span className="text-muted-foreground truncate text-sm">
                  {fileName || "No file selected"}
                </span>
              </div>
              {testCases.length > 0 && (
                <div className="text-muted-foreground mt-1 text-xs">
                  {testCases.length} test case{testCases.length !== 1 ? "s" : ""} loaded
                </div>
              )}
            </div>

            {/* API URL */}
            <div>
              <label className="text-muted-foreground mb-1 block text-xs font-medium uppercase">
                API Base URL
              </label>
              <input
                type="text"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                className="bg-background w-full rounded-md border px-3 py-2 font-mono text-sm"
                placeholder="http://localhost:8000"
              />
            </div>

            {/* Model override */}
            <div>
              <label className="text-muted-foreground mb-1 block text-xs font-medium uppercase">
                Model Override (optional)
              </label>
              <input
                type="text"
                value={modelOverride}
                onChange={(e) => setModelOverride(e.target.value)}
                className="bg-background w-full rounded-md border px-3 py-2 font-mono text-sm"
                placeholder="e.g. anthropic:claude-sonnet-4-20250514"
              />
            </div>

            {/* Run controls */}
            <div className="flex items-end gap-2">
              {!isRunning ? (
                <button
                  onClick={runAll}
                  disabled={testCases.length === 0}
                  className="bg-primary text-primary-foreground hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground rounded-md px-6 py-2 text-sm font-medium transition disabled:cursor-not-allowed"
                >
                  Run All ({testCases.length})
                </button>
              ) : (
                <button
                  onClick={stopRun}
                  className="rounded-md bg-red-600 px-6 py-2 text-sm font-medium text-white transition hover:bg-red-700"
                >
                  Stop
                </button>
              )}

              {isRunning && (
                <span className="text-muted-foreground text-sm">
                  {progress.current} / {progress.total}
                </span>
              )}
            </div>
          </div>

          {/* Progress bar */}
          {(isRunning || progress.total > 0) && (
            <div className="mt-4">
              <div className="bg-muted h-2 overflow-hidden rounded-full">
                <div
                  className="bg-primary h-full rounded-full transition-all duration-300"
                  style={{
                    width: `${progress.total > 0 ? (progress.current / progress.total) * 100 : 0}%`,
                  }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Summary (shown when we have results) */}
        {summary && <SummaryPanel stats={summary} results={completedResults} />}

        {/* Test Case Results */}
        {evalResults.length > 0 && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold">Test Cases ({evalResults.length})</h2>
            {evalResults.map((result) => (
              <TestCaseCard key={result.testCase.id} result={result} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
