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

interface BarChartVerticalProps extends BaseChartProps {
  showValues?: boolean;
  barPadding?: number;
  colorScheme?: string[];
}

export function BarChartVertical({
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
}: BarChartVerticalProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  // Use dataMapping if available, otherwise fall back to dimension scanning
  const categoryField = useMemo(
    () => dataMapping?.xAxis || dimensions.find((d) => d.type === "category")?.field,
    [dataMapping, dimensions],
  );
  const numericField = useMemo(
    () => dataMapping?.yAxis || dimensions.find((d) => d.type === "numeric")?.field,
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

    // Clear previous render
    d3.select(svgRef.current).selectAll("*").remove();

    if (!categoryField || !numericField) return;

    // Set up margins and dimensions
    const margin = { top: 40, right: 30, bottom: 60, left: 60 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const svg = d3.select(svgRef.current).attr("width", width).attr("height", height);

    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // X scale (categories)
    const xScale = d3
      .scaleBand()
      .domain(data.rows.map((d) => d[categoryField]))
      .range([0, innerWidth])
      .padding(barPadding);

    // Y scale (numeric values)
    const yExtent = [0, d3.max(data.rows, (d) => d[numericField]) || 0] as [
      number,
      number,
    ];
    const yScale = d3.scaleLinear().domain(yExtent).nice().range([innerHeight, 0]);

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
      .attr("x", (d) => xScale(d[categoryField]) || 0)
      .attr("y", (d) => yScale(d[numericField]))
      .attr("width", xScale.bandwidth())
      .attr("height", (d) => innerHeight - yScale(d[numericField]))
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

    // Show values on bars if enabled
    if (showValues) {
      g.selectAll(".bar-label")
        .data(data.rows)
        .join("text")
        .attr("class", "bar-label")
        .attr("x", (d) => (xScale(d[categoryField]) || 0) + xScale.bandwidth() / 2)
        .attr("y", (d) => yScale(d[numericField]) - 5)
        .attr("text-anchor", "middle")
        .style("font-size", "12px")
        .style("fill", "currentColor")
        .text((d) => d[numericField].toLocaleString());
    }

    // Apply highlights with UI-controlled colors
    if (highlights.length > 0) {
      const insightColorMap = createInsightColorMap(highlights);

      highlights.forEach((highlight) => {
        const highlightColor = getHighlightColor(highlight.insightId, insightColorMap);

        if (
          (highlight.type === HighlightType.ROW ||
            highlight.type === HighlightType.POINT_SET) &&
          highlight.rowIds
        ) {
          highlight.rowIds.forEach((rowId) => {
            g.selectAll(".bar")
              .filter((d: any) => d.row_id === rowId)
              .attr("stroke", highlightColor)
              .attr("stroke-width", 3);
          });
        }

        if (
          highlight.type === HighlightType.THRESHOLD &&
          highlight.thresholdValue !== undefined
        ) {
          g.append("line")
            .attr("x1", 0)
            .attr("x2", innerWidth)
            .attr("y1", yScale(highlight.thresholdValue))
            .attr("y2", yScale(highlight.thresholdValue))
            .attr("stroke", highlightColor)
            .attr("stroke-width", 2)
            .attr("stroke-dasharray", "5,5");
        }
      });
    }

    // X Axis
    g.append("g")
      .attr("transform", `translate(0,${innerHeight})`)
      .call(d3.axisBottom(xScale))
      .selectAll("text")
      .attr("transform", "rotate(-45)")
      .style("text-anchor", "end");

    // Y Axis
    g.append("g").call(d3.axisLeft(yScale));

    // Title
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
