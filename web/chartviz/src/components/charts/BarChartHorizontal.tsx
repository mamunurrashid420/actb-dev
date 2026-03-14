"use client";

import { useEffect, useRef, useMemo } from "react";
import * as d3 from "d3";
import {
  BaseChartProps,
  createInsightColorMap,
  getHighlightColor,
  HighlightType,
} from "@/lib/charts/registry";
import { getSentimentColor, getProminenceOpacity } from "@/lib/charts/style-guide";

interface BarChartHorizontalProps extends BaseChartProps {
  showValues?: boolean;
  barPadding?: number;
  colorScheme?: string[];
}

export function BarChartHorizontal({
  data,
  dimensions,
  dataMapping,
  dataSeries,
  title,
  width = 600,
  height = 400,
  highlights = [],
  showValues = false,
  barPadding = 0.2,
  colorScheme = ["#4F46E5"],
}: BarChartHorizontalProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  // Use dataMapping if available (for horizontal, xAxis is numeric, yAxis is category)
  const categoryField = useMemo(
    () => dataMapping?.yAxis || dimensions.find((d) => d.type === "category")?.field,
    [dataMapping, dimensions],
  );
  const numericField = useMemo(
    () => dataMapping?.xAxis || dimensions.find((d) => d.type === "numeric")?.field,
    [dataMapping, dimensions],
  );

  // Get series config for styling
  const seriesConfig = useMemo(() => {
    if (!dataSeries || dataSeries.length === 0) {
      return { color: colorScheme[0], opacity: 0.8 };
    }
    const config = dataSeries.find((s) => s.field === numericField) || dataSeries[0];
    return {
      color: getSentimentColor(config.sentiment),
      opacity: getProminenceOpacity(config.prominence),
    };
  }, [dataSeries, numericField, colorScheme]);

  useEffect(() => {
    if (!svgRef.current || !data.rows.length) return;

    d3.select(svgRef.current).selectAll("*").remove();

    if (!categoryField || !numericField) return;

    const margin = { top: 40, right: 30, bottom: 60, left: 120 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const svg = d3.select(svgRef.current).attr("width", width).attr("height", height);

    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Y scale for categories (vertical axis)
    const yScale = d3
      .scaleBand()
      .domain(data.rows.map((d) => d[categoryField]))
      .range([0, innerHeight])
      .padding(barPadding);

    // X scale for values (horizontal axis)
    const xExtent = [0, d3.max(data.rows, (d) => d[numericField]) || 0];
    const xScale = d3.scaleLinear().domain(xExtent).nice().range([0, innerWidth]);

    // Color scale
    const colorScale = d3
      .scaleOrdinal<string>()
      .domain(data.rows.map((d) => d[categoryField]))
      .range(
        colorScheme.length > 1
          ? colorScheme
          : Array(data.rows.length).fill(colorScheme[0]),
      );

    // Draw bars
    g.selectAll(".bar")
      .data(data.rows)
      .join("rect")
      .attr("class", "bar")
      .attr("y", (d) => yScale(d[categoryField]) || 0)
      .attr("x", 0)
      .attr("height", yScale.bandwidth())
      .attr("width", (d) => xScale(d[numericField]))
      .attr(
        "fill",
        colorScheme.length > 1
          ? (d: any) => colorScale(d[categoryField])
          : seriesConfig.color,
      )
      .attr("opacity", seriesConfig.opacity)
      .style("cursor", "pointer")
      .on("mouseenter", function () {
        d3.select(this).attr("opacity", Math.min(seriesConfig.opacity + 0.2, 1));
      })
      .on("mouseleave", function () {
        d3.select(this).attr("opacity", seriesConfig.opacity);
      });

    // Show values if enabled
    if (showValues) {
      g.selectAll(".bar-label")
        .data(data.rows)
        .join("text")
        .attr("class", "bar-label")
        .attr("y", (d) => (yScale(d[categoryField]) || 0) + yScale.bandwidth() / 2)
        .attr("x", (d) => xScale(d[numericField]) + 5)
        .attr("dy", "0.35em")
        .style("font-size", "12px")
        .style("fill", "currentColor")
        .text((d) => d[numericField].toLocaleString());
    }

    // Apply highlights
    if (highlights.length > 0) {
      const insightColorMap = createInsightColorMap(highlights);

      highlights.forEach((highlight) => {
        const color = getHighlightColor(highlight.insightId, insightColorMap);

        if (
          (highlight.type === HighlightType.ROW ||
            highlight.type === HighlightType.POINT_SET) &&
          highlight.rowIds
        ) {
          highlight.rowIds.forEach((rowId) => {
            g.selectAll(".bar")
              .filter((d: any) => d.row_id === rowId)
              .attr("stroke", color)
              .attr("stroke-width", 3);
          });
        }

        if (
          highlight.type === HighlightType.THRESHOLD &&
          highlight.thresholdValue !== undefined
        ) {
          g.append("line")
            .attr("x1", xScale(highlight.thresholdValue))
            .attr("x2", xScale(highlight.thresholdValue))
            .attr("y1", 0)
            .attr("y2", innerHeight)
            .attr("stroke", color)
            .attr("stroke-width", 2)
            .attr("stroke-dasharray", "5,5");
        }
      });
    }

    // Axes
    g.append("g").call(d3.axisLeft(yScale));
    g.append("g")
      .attr("transform", `translate(0,${innerHeight})`)
      .call(d3.axisBottom(xScale));

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
    numericField,
    seriesConfig,
    title,
    width,
    height,
    highlights,
    showValues,
    barPadding,
    colorScheme,
  ]);

  return <svg ref={svgRef} />;
}
