"use client";

import { useEffect, useRef, useMemo } from "react";
import * as d3 from "d3";
import {
  BaseChartProps,
  createInsightColorMap,
  getHighlightColor,
  DataSeriesClassification,
  HighlightType,
} from "@/lib/charts/registry";
import { getSentimentColor, getProminenceOpacity } from "@/lib/charts/style-guide";

interface BarChartStackedProps extends BaseChartProps {
  barPadding?: number;
  colorScheme?: string[];
}

export function BarChartStacked({
  data,
  dimensions,
  dataMapping,
  dataSeries,
  title,
  width = 600,
  height = 400,
  highlights = [],
  barPadding = 0.2,
  colorScheme,
}: BarChartStackedProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  // Use dataMapping if available, otherwise fall back to dimension scanning
  const categoryField = useMemo(
    () =>
      dataMapping?.xAxis ||
      dimensions.find((d) => d.field.includes("category") || d.type === "category")
        ?.field,
    [dataMapping, dimensions],
  );
  const seriesField = useMemo(
    () =>
      dataMapping?.groupBy ||
      dimensions.find((d) => d.field.includes("series") || d.field.includes("group"))
        ?.field,
    [dataMapping, dimensions],
  );
  const valueField = useMemo(
    () =>
      dataMapping?.yAxis ||
      dataMapping?.value ||
      dimensions.find((d) => d.type === "numeric")?.field,
    [dataMapping, dimensions],
  );

  // Helper to get series-specific styling from dataSeries
  const getSeriesConfig = (seriesName: string): { color?: string; opacity: number } => {
    if (!dataSeries || dataSeries.length === 0) {
      return { opacity: 0.8 };
    }
    const config = dataSeries.find((s) => s.groupValue === seriesName);
    if (!config) return { opacity: 0.8 };
    return {
      color: getSentimentColor(config.sentiment),
      opacity: getProminenceOpacity(config.prominence),
    };
  };

  useEffect(() => {
    if (!svgRef.current || !data.rows.length) return;

    d3.select(svgRef.current).selectAll("*").remove();

    if (!categoryField || !seriesField || !valueField) return;

    const margin = { top: 40, right: 100, bottom: 60, left: 60 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const svg = d3.select(svgRef.current).attr("width", width).attr("height", height);

    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Pivot data for stacking
    const categories = Array.from(new Set(data.rows.map((d) => d[categoryField])));
    const series = Array.from(new Set(data.rows.map((d) => d[seriesField])));

    const stackData = categories.map((cat) => {
      const obj: any = { category: cat };
      series.forEach((ser) => {
        const row = data.rows.find(
          (r) => r[categoryField] === cat && r[seriesField] === ser,
        );
        obj[ser] = row ? row[valueField] : 0;
      });
      return obj;
    });

    // Stack generator
    const stack = d3.stack().keys(series);
    const stackedData = stack(stackData as any);

    // Scales
    const xScale = d3
      .scaleBand()
      .domain(categories)
      .range([0, innerWidth])
      .padding(barPadding);

    const yScale = d3
      .scaleLinear()
      .domain([0, d3.max(stackedData, (layer) => d3.max(layer, (d) => d[1])) || 0])
      .nice()
      .range([innerHeight, 0]);

    // Build color scale - use dataSeries colors if available, otherwise fallback to colorScheme
    const seriesColors = series.map((ser) => {
      const config = getSeriesConfig(ser);
      return config.color;
    });
    const fallbackColors = colorScheme || (d3.schemeSet2 as string[]);
    const colorScale = d3
      .scaleOrdinal<string>()
      .domain(series)
      .range(
        seriesColors.some((c) => c !== undefined)
          ? seriesColors.map((c, i) => c || fallbackColors[i % fallbackColors.length])
          : fallbackColors,
      );

    // Draw stacked bars
    g.selectAll(".layer")
      .data(stackedData)
      .join("g")
      .attr("class", "layer")
      .attr("fill", (d) => colorScale(d.key))
      .attr("opacity", (d) => getSeriesConfig(d.key).opacity)
      .selectAll("rect")
      .data((d) => d)
      .join("rect")
      .attr("x", (d: any) => xScale(d.data.category) || 0)
      .attr("y", (d) => yScale(d[1]))
      .attr("height", (d) => yScale(d[0]) - yScale(d[1]))
      .attr("width", xScale.bandwidth())
      .style("cursor", "pointer")
      .on("mouseenter", function (event) {
        const target = event.currentTarget as SVGRectElement;
        const parent = target.parentNode as SVGGElement | null;
        if (!parent) return;
        const parentOpacity = parseFloat(d3.select(parent).attr("opacity") || "0.8");
        d3.select(parent).attr("opacity", Math.min(parentOpacity + 0.2, 1));
      })
      .on("mouseleave", function (event) {
        const target = event.currentTarget as SVGRectElement;
        const parent = target.parentNode as SVGGElement | null;
        if (!parent) return;
        const layer = d3.select(parent);
        const seriesName = (layer.datum() as any).key;
        layer.attr("opacity", getSeriesConfig(seriesName).opacity);
      });

    // Apply highlights
    if (highlights.length > 0) {
      const insightColorMap = createInsightColorMap(highlights);

      highlights.forEach((highlight) => {
        const color = getHighlightColor(highlight.insightId, insightColorMap);

        if (
          highlight.type === HighlightType.THRESHOLD &&
          highlight.thresholdValue !== undefined
        ) {
          g.append("line")
            .attr("x1", 0)
            .attr("x2", innerWidth)
            .attr("y1", yScale(highlight.thresholdValue))
            .attr("y2", yScale(highlight.thresholdValue))
            .attr("stroke", color)
            .attr("stroke-width", 2)
            .attr("stroke-dasharray", "5,5");
        }
      });
    }

    // Axes
    g.append("g")
      .attr("transform", `translate(0,${innerHeight})`)
      .call(d3.axisBottom(xScale));

    g.append("g").call(d3.axisLeft(yScale));

    // Legend - use labels from dataSeries if available
    const legend = svg
      .append("g")
      .attr("transform", `translate(${width - 80}, ${margin.top})`);

    series.forEach((ser, i) => {
      const seriesConfig = dataSeries?.find((s) => s.groupValue === ser);
      const legendLabel = seriesConfig?.label || ser;

      const legendRow = legend.append("g").attr("transform", `translate(0, ${i * 20})`);

      legendRow
        .append("rect")
        .attr("width", 12)
        .attr("height", 12)
        .attr("fill", colorScale(ser));

      legendRow
        .append("text")
        .attr("x", 18)
        .attr("y", 10)
        .style("font-size", "12px")
        .style("fill", "currentColor")
        .text(legendLabel);
    });

    if (title) {
      svg
        .append("text")
        .attr("x", width / 2)
        .attr("y", 20)
        .attr("text-anchor", "middle")
        .style("font-size", "16px")
        .style("font-weight", "bold")
        .style("fill", "currentColor")
        .text(title);
    }
  }, [
    data,
    categoryField,
    seriesField,
    valueField,
    dataSeries,
    title,
    width,
    height,
    highlights,
    barPadding,
    colorScheme,
  ]);

  return <svg ref={svgRef} />;
}
