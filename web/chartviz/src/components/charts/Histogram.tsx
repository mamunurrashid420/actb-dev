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

interface HistogramProps extends BaseChartProps {
  bins?: number;
  showMean?: boolean;
}

export function Histogram({
  data,
  dimensions,
  dataMapping,
  dataSeries,
  title,
  width = 600,
  height = 400,
  highlights = [],
  bins = 20,
  showMean = false,
}: HistogramProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  // Use dataMapping if available
  const valueField = useMemo(
    () =>
      dataMapping?.xAxis ||
      dataMapping?.value ||
      dimensions.find((d) => d.type === "numeric")?.field,
    [dataMapping, dimensions],
  );

  // Get series config for styling
  const seriesConfig = useMemo(() => {
    if (!dataSeries || dataSeries.length === 0) {
      return { color: "#4F46E5", opacity: 0.8 };
    }
    const config = dataSeries.find((s) => s.field === valueField) || dataSeries[0];
    return {
      color: getSentimentColor(config.sentiment),
      opacity: getProminenceOpacity(config.prominence),
    };
  }, [dataSeries, valueField]);

  useEffect(() => {
    if (!svgRef.current || !data.rows.length) return;

    d3.select(svgRef.current).selectAll("*").remove();

    if (!valueField) return;

    const margin = { top: 40, right: 30, bottom: 60, left: 60 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const svg = d3.select(svgRef.current).attr("width", width).attr("height", height);

    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    const values = data.rows.map((d) => d[valueField]);

    // Create bins
    const xScale = d3
      .scaleLinear()
      .domain(d3.extent(values) as [number, number])
      .nice()
      .range([0, innerWidth]);

    const histogram = d3
      .bin()
      .domain(xScale.domain() as [number, number])
      .thresholds(xScale.ticks(bins));

    const binnedData = histogram(values);

    const yScale = d3
      .scaleLinear()
      .domain([0, d3.max(binnedData, (d) => d.length) || 0])
      .nice()
      .range([innerHeight, 0]);

    // Draw bars
    g.selectAll(".bar")
      .data(binnedData)
      .join("rect")
      .attr("class", "bar")
      .attr("x", (d) => xScale(d.x0 || 0) + 1)
      .attr("y", (d) => yScale(d.length))
      .attr("width", (d) => Math.max(0, xScale(d.x1 || 0) - xScale(d.x0 || 0) - 1))
      .attr("height", (d) => innerHeight - yScale(d.length))
      .attr("fill", seriesConfig.color)
      .attr("opacity", seriesConfig.opacity)
      .style("cursor", "pointer")
      .on("mouseenter", function () {
        d3.select(this).attr("opacity", Math.min(seriesConfig.opacity + 0.2, 1));
      })
      .on("mouseleave", function () {
        d3.select(this).attr("opacity", seriesConfig.opacity);
      });

    // Show mean line if enabled
    if (showMean) {
      const mean = d3.mean(values) || 0;
      g.append("line")
        .attr("x1", xScale(mean))
        .attr("x2", xScale(mean))
        .attr("y1", 0)
        .attr("y2", innerHeight)
        .attr("stroke", "#ef4444")
        .attr("stroke-width", 2)
        .attr("stroke-dasharray", "5,5");

      g.append("text")
        .attr("x", xScale(mean) + 5)
        .attr("y", 15)
        .style("font-size", "12px")
        .style("fill", "#ef4444")
        .text(`Mean: ${mean.toFixed(1)}`);
    }

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
            .attr("x1", xScale(highlight.thresholdValue))
            .attr("x2", xScale(highlight.thresholdValue))
            .attr("y1", 0)
            .attr("y2", innerHeight)
            .attr("stroke", color)
            .attr("stroke-width", 2)
            .attr("stroke-dasharray", "5,5");
        }

        if (
          highlight.type === HighlightType.RANGE &&
          highlight.rangeMin !== undefined &&
          highlight.rangeMax !== undefined
        ) {
          g.append("rect")
            .attr("x", xScale(highlight.rangeMin))
            .attr("y", 0)
            .attr("width", xScale(highlight.rangeMax) - xScale(highlight.rangeMin))
            .attr("height", innerHeight)
            .attr("fill", color)
            .attr("opacity", 0.2);
        }
      });
    }

    // Axes
    g.append("g")
      .attr("transform", `translate(0,${innerHeight})`)
      .call(d3.axisBottom(xScale));

    g.append("g").call(d3.axisLeft(yScale));

    // Axis labels
    g.append("text")
      .attr("x", innerWidth / 2)
      .attr("y", innerHeight + 50)
      .attr("text-anchor", "middle")
      .style("font-size", "12px")
      .style("fill", "currentColor")
      .text(valueField);

    g.append("text")
      .attr("transform", "rotate(-90)")
      .attr("x", -innerHeight / 2)
      .attr("y", -45)
      .attr("text-anchor", "middle")
      .style("font-size", "12px")
      .style("fill", "currentColor")
      .text("Frequency");

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
    valueField,
    seriesConfig,
    title,
    width,
    height,
    highlights,
    bins,
    showMean,
  ]);

  return <svg ref={svgRef} />;
}
