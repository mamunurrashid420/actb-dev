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

interface BarChartGroupedProps extends BaseChartProps {
  barPadding?: number;
  colorScheme?: string[];
}

export function BarChartGrouped({
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
}: BarChartGroupedProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  // Use dataMapping if available, otherwise fall back to dimension scanning
  const categoryField = useMemo(
    () =>
      dataMapping?.xAxis ||
      dimensions.find((d) => d.field.includes("category") || d.type === "category")
        ?.field,
    [dataMapping, dimensions],
  );
  const groupField = useMemo(
    () =>
      dataMapping?.groupBy ||
      dimensions.find((d) => d.field.includes("group") || d.field.includes("series"))
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
  const getSeriesConfig = (groupName: string): { color?: string; opacity: number } => {
    if (!dataSeries || dataSeries.length === 0) {
      return { opacity: 0.8 };
    }
    const config = dataSeries.find((s) => s.groupValue === groupName);
    if (!config) return { opacity: 0.8 };
    return {
      color: getSentimentColor(config.sentiment),
      opacity: getProminenceOpacity(config.prominence),
    };
  };

  useEffect(() => {
    if (!svgRef.current || !data.rows.length) return;

    d3.select(svgRef.current).selectAll("*").remove();

    if (!categoryField || !groupField || !valueField) return;

    const margin = { top: 40, right: 100, bottom: 60, left: 60 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const svg = d3.select(svgRef.current).attr("width", width).attr("height", height);

    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    const categories = Array.from(new Set(data.rows.map((d) => d[categoryField])));
    const groups = Array.from(new Set(data.rows.map((d) => d[groupField])));

    // Outer scale: categories
    const x0 = d3
      .scaleBand()
      .domain(categories)
      .range([0, innerWidth])
      .padding(barPadding);

    // Inner scale: groups within each category
    const x1 = d3.scaleBand().domain(groups).range([0, x0.bandwidth()]).padding(0.05);

    const yScale = d3
      .scaleLinear()
      .domain([0, d3.max(data.rows, (d) => d[valueField]) || 0])
      .nice()
      .range([innerHeight, 0]);

    // Build color scale - use dataSeries colors if available, otherwise fallback to colorScheme
    const groupColors = groups.map((grp) => {
      const config = getSeriesConfig(grp);
      return config.color;
    });
    const fallbackColors = colorScheme || (d3.schemeSet2 as string[]);
    const colorScale = d3
      .scaleOrdinal<string>()
      .domain(groups)
      .range(
        groupColors.some((c) => c !== undefined)
          ? groupColors.map((c, i) => c || fallbackColors[i % fallbackColors.length])
          : fallbackColors,
      );

    // Draw grouped bars
    const categoryGroups = g
      .selectAll(".category-group")
      .data(categories)
      .join("g")
      .attr("class", "category-group")
      .attr("transform", (cat) => `translate(${x0(cat)},0)`);

    categoryGroups
      .selectAll("rect")
      .data((cat) =>
        groups.map((grp) => {
          const row = data.rows.find(
            (r) => r[categoryField] === cat && r[groupField] === grp,
          );
          return { group: grp, value: row ? row[valueField] : 0, row_id: row?.row_id };
        }),
      )
      .join("rect")
      .attr("x", (d) => x1(d.group) || 0)
      .attr("y", (d) => yScale(d.value))
      .attr("width", x1.bandwidth())
      .attr("height", (d) => innerHeight - yScale(d.value))
      .attr("fill", (d) => colorScale(d.group))
      .attr("opacity", (d) => getSeriesConfig(d.group).opacity)
      .style("cursor", "pointer")
      .on("mouseenter", function (event, d) {
        const config = getSeriesConfig(d.group);
        d3.select(this).attr("opacity", Math.min(config.opacity + 0.2, 1));
      })
      .on("mouseleave", function (event, d) {
        d3.select(this).attr("opacity", getSeriesConfig(d.group).opacity);
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
      .call(d3.axisBottom(x0));

    g.append("g").call(d3.axisLeft(yScale));

    // Legend - use labels from dataSeries if available
    const legend = svg
      .append("g")
      .attr("transform", `translate(${width - 80}, ${margin.top})`);

    groups.forEach((grp, i) => {
      const groupConfig = dataSeries?.find((s) => s.groupValue === grp);
      const legendLabel = groupConfig?.label || grp;

      const legendRow = legend.append("g").attr("transform", `translate(0, ${i * 20})`);

      legendRow
        .append("rect")
        .attr("width", 12)
        .attr("height", 12)
        .attr("fill", colorScale(grp));

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
    groupField,
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
