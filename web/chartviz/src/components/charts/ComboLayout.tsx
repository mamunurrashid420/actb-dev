"use client";

import { createChart } from "@/lib/charts/factory";
import type { ChartSpec, ChartDataSlice } from "@/lib/charts/factory";
import type { BaseChartProps, Highlight } from "@/lib/charts/registry";

/**
 * ComboLayout — a layout component (not a D3 chart) that renders
 * each sub-chart independently using the existing chart factory.
 *
 * A combo chart is a parent ChartSpec whose `sub_charts` array contains
 * fully self-contained child ChartSpecs.  Each child is rendered by the
 * existing chart factory (BarChartVertical, LineChart, etc.) and
 * arranged in a responsive flex/grid container.
 *
 * Sub-charts inherit the parent's data slice if they don't specify
 * their own `chart_data_slice_ids`.
 */
export function ComboLayout({
  data,
  dimensions,
  title,
  width,
  height,
  highlights = [],
  // These come via the spec passed through the transformer — we need
  // the original spec for sub_charts, so we accept it as a rest prop.
  ...rest
}: BaseChartProps & { spec?: ChartSpec }) {
  // The factory's default transformer doesn't forward the full spec,
  // so the ComboLayout also accepts the spec directly.  If spec is not
  // available we fall back to rendering the data as a table via the
  // parent's own data (handled by the factory's fallback path).
  const spec = rest.spec;
  const subCharts = spec?.sub_charts;

  if (!subCharts || subCharts.length === 0) {
    // No sub-charts — nothing to compose.  The factory fallback
    // (data_table) will handle this case before we get here, but
    // guard defensively.
    return (
      <div className="text-muted-foreground p-4 text-sm">
        Combo chart has no sub-charts defined.
      </div>
    );
  }

  // Determine per-sub-chart width.  Divide available space evenly,
  // but cap at a sensible minimum so charts remain readable.
  const chartWidth = width
    ? Math.max(300, Math.floor(width / subCharts.length) - 16)
    : undefined;

  return (
    <div>
      {/* Parent title */}
      {title && <h3 className="mb-2 text-base font-semibold">{title}</h3>}

      {/* Sub-charts in a responsive flex row that wraps */}
      <div className="flex flex-wrap gap-4">
        {subCharts.map((subSpec) => {
          // Inherit parent's data slice ids if the sub-chart has none
          const resolvedSpec: ChartSpec = {
            ...subSpec,
            dimensions: subSpec.dimensions?.length ? subSpec.dimensions : dimensions,
            chart_data_slice_ids: subSpec.chart_data_slice_ids?.length
              ? subSpec.chart_data_slice_ids
              : spec.chart_data_slice_ids,
          };

          // Each sub-chart shares the same data slice (parent's data)
          const element = createChart(resolvedSpec, data, highlights, {
            width: chartWidth,
            height: height,
          });

          return (
            <div key={subSpec.id} className="min-w-[300px] flex-1">
              {element}
            </div>
          );
        })}
      </div>
    </div>
  );
}
