import { registerChart } from "@/lib/charts/registry";
import { registerTransformer } from "@/lib/charts/factory";

// Import all MVP chart components
import { KPICard } from "./KPICard";
import { DataTable } from "./DataTable";
import { BarChartVertical } from "./BarChartVertical";
import { BarChartHorizontal } from "./BarChartHorizontal";
import { BarChartStacked } from "./BarChartStacked";
import { BarChartGrouped } from "./BarChartGrouped";
import { LineChart } from "./LineChart";
import { AreaChart } from "./AreaChart";
import { ScatterPlot } from "./ScatterPlot";
import { PieChart } from "./PieChart";
import { DonutChart } from "./DonutChart";
import { Histogram } from "./Histogram";
import { Heatmap } from "./Heatmap";
import { Treemap } from "./Treemap";
import { ComboLayout } from "./ComboLayout";

/**
 * Initialize the chart registry with all MVP chart types.
 * Call this once at app startup (e.g., in app/layout.tsx or a provider).
 */
export function initializeChartRegistry() {
  // P0 — Core: KPI and Data components
  registerChart("kpi_card", KPICard);
  registerChart("data_table", DataTable);

  // P0 — Core: Bar chart variants
  registerChart("bar_chart_vertical", BarChartVertical);
  registerChart("bar_chart_horizontal", BarChartHorizontal);

  // P0 — Core: Line and Area charts
  registerChart("line_chart", LineChart);
  registerChart("area_chart", AreaChart);

  // P0 — Core: Scatter, Pie, Donut
  registerChart("scatter_plot", ScatterPlot);
  registerChart("pie_chart", PieChart);
  registerChart("donut_chart", DonutChart);

  // P1 — Extended
  registerChart("bar_chart_stacked", BarChartStacked);
  registerChart("bar_chart_grouped", BarChartGrouped);
  registerChart("histogram", Histogram);
  registerChart("heatmap", Heatmap);
  registerChart("treemap", Treemap);

  // P2 — Combo (layout component, not a D3 chart)
  registerChart("combo", ComboLayout as any);
  // Custom transformer that passes the full spec so ComboLayout can
  // access sub_charts (the default transformer does not forward it).
  registerTransformer(
    "combo",
    (spec, data, highlights) =>
      ({
        data,
        dimensions: spec.dimensions,
        filters: spec.filters,
        title: spec.title,
        highlights,
        dataMapping: spec.data_mapping,
        dataSeries: spec.data_series,
        // Forward the full spec so ComboLayout can read sub_charts
        spec,
      }) as any,
  );
}

// Export all chart components for direct use if needed
export {
  KPICard,
  DataTable,
  BarChartVertical,
  BarChartHorizontal,
  BarChartStacked,
  BarChartGrouped,
  LineChart,
  AreaChart,
  ScatterPlot,
  PieChart,
  DonutChart,
  Histogram,
  Heatmap,
  Treemap,
  ComboLayout,
};
