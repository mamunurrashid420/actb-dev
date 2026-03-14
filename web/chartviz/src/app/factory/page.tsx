"use client";

import { initializeChartRegistry } from "@/components/charts";
import { ResponsiveChartContainer } from "@/components/ResponsiveChartContainer";
import { ChartWithInsights } from "@/components/ChartWithInsights";
import { sampleCharts, getChartTypeDisplayName } from "@/data/sample-charts";
import { sampleInsightsData } from "@/data/sample-insights";
import type { Recommendation } from "@/types/insights";

// Ensure registry is initialized
initializeChartRegistry();

// Charts that have insights data
const chartsWithInsightsIds = new Set(sampleInsightsData.map((d) => d.chartId));

// =============================================================================
// Chart Card Component
// =============================================================================

function ChartCard({
  chartType,
  title,
  children,
  className = "",
}: {
  chartType: string;
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  const displayName = getChartTypeDisplayName(chartType);

  return (
    <div className={`bg-card overflow-hidden rounded-lg border shadow-sm ${className}`}>
      {/* Header */}
      <div className="bg-muted/30 border-b px-4 py-3">
        <div className="flex items-center justify-between">
          <div>
            <span className="bg-primary/10 text-primary inline-flex items-center rounded-md px-2 py-1 text-xs font-medium">
              {displayName}
            </span>
          </div>
          <code className="text-muted-foreground text-xs">{chartType}</code>
        </div>
        <h3 className="text-foreground mt-2 font-semibold">{title}</h3>
      </div>
      {/* Chart Content */}
      <div className="p-4">
        <div className="w-full overflow-x-auto">{children}</div>
      </div>
    </div>
  );
}

// =============================================================================
// Factory Page Component
// =============================================================================

export default function FactoryPage() {
  const defaultHeight = 300;

  // Handler for recommendation clicks
  const handleRecommendationClick = (rec: Recommendation) => {
    console.log("Recommendation clicked:", rec);
    alert(
      `Recommendation: ${rec.summary}\nType: ${rec.type}\nPriority: ${rec.priority || "N/A"}`,
    );
  };

  // Get charts that have insights
  const chartsWithInsights = sampleCharts.filter((chart) =>
    chartsWithInsightsIds.has(chart.spec.id),
  );

  return (
    <main className="bg-background min-h-screen p-4 md:p-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Chart Factory</h1>
          <p className="text-muted-foreground mt-2">
            All {sampleCharts.length} MVP chart components rendered using{" "}
            <code className="bg-muted rounded px-1.5 py-0.5 text-sm">
              createChart(spec, data)
            </code>{" "}
            factory
          </p>
        </header>

        {/* Charts with Insights Section */}
        <section className="mb-12">
          <h2 className="mb-4 text-xl font-semibold">Charts with Insights</h2>
          <p className="text-muted-foreground mb-6">
            Composite components combining charts with insights panels. Hover over
            insights to see bidirectional linking. Click the 💡 button to toggle the
            insights panel.
          </p>
          <div className="flex flex-col gap-6">
            {chartsWithInsights.map((chart) => {
              const insightsData = sampleInsightsData.find(
                (d) => d.chartId === chart.spec.id,
              );
              return (
                <ChartWithInsights
                  key={chart.spec.id}
                  spec={chart.spec}
                  data={chart.data}
                  highlights={insightsData?.highlights || []}
                  insights={insightsData?.insights || []}
                  height={chart.height ?? defaultHeight}
                  onRecommendationClick={handleRecommendationClick}
                />
              );
            })}
          </div>
        </section>

        {/* Divider */}
        <hr className="border-border mb-8" />

        {/* All Charts Grid Section */}
        <section>
          <h2 className="mb-4 text-xl font-semibold">All Chart Types</h2>
          <p className="text-muted-foreground mb-6">
            Individual chart components without insights panels.
          </p>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 lg:gap-6">
            {sampleCharts.map((chart) => (
              <ChartCard
                key={chart.spec.id}
                chartType={chart.spec.chart_type}
                title={chart.spec.title}
                className={chart.fullWidth ? "lg:col-span-2" : ""}
              >
                <ResponsiveChartContainer
                  spec={chart.spec}
                  data={chart.data}
                  height={chart.height ?? defaultHeight}
                />
              </ChartCard>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
