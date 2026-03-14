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

interface AreaChartProps extends BaseChartProps {
  curve?: "linear" | "monotone" | "step" | "cardinal";
  showLine?: boolean;
  strokeWidth?: number;
}

export function AreaChart({
  data,
  dimensions,
  dataMapping,
  dataSeries,
  title,
  width = 600,
  height = 400,
  highlights = [],
  curve = "monotone",
  showLine = true,
  strokeWidth = 2,
}: AreaChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  // Use dataMapping if available
  const xField = useMemo(
    () =>
      dataMapping?.xAxis ||
      dimensions.find((d) => d.type === "time" || d.type === "category")?.field,
    [dataMapping, dimensions],
  );
  const yField = useMemo(
    () => dataMapping?.yAxis || dimensions.find((d) => d.type === "numeric")?.field,
    [dataMapping, dimensions],
  );

  // Get series config for styling
  const seriesConfig = useMemo(() => {
    if (!dataSeries || dataSeries.length === 0) {
      return { color: "#4F46E5", opacity: 0.6 };
    }
    const config = dataSeries.find((s) => s.field === yField) || dataSeries[0];
    return {
      color: getSentimentColor(config.sentiment),
      opacity: getProminenceOpacity(config.prominence) * 0.7, // Slightly more transparent for area
    };
  }, [dataSeries, yField]);

  useEffect(() => {
    if (!svgRef.current || !data.rows.length) return;

    d3.select(svgRef.current).selectAll("*").remove();

    if (!xField || !yField) return;

    const margin = { top: 40, right: 30, bottom: 60, left: 60 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const svg = d3.select(svgRef.current).attr("width", width).attr("height", height);

    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    const parseTime = d3.timeParse("%Y-%m-%d");
    const isTimeSeries = dimensions.find((d) => d.field === xField)?.type === "time";

    const processedData = data.rows.map((d) => ({
      ...d,
      [xField]: isTimeSeries ? parseTime(d[xField]) : d[xField],
    }));

    const xScale = isTimeSeries
      ? d3
          .scaleTime()
          .domain(d3.extent(processedData, (d) => d[xField]) as [Date, Date])
          .range([0, innerWidth])
      : d3
          .scalePoint()
          .domain(processedData.map((d) => d[xField]))
          .range([0, innerWidth])
          .padding(0.5);

    const yScale = d3
      .scaleLinear()
      .domain([0, d3.max(processedData, (d) => d[yField]) || 0])
      .nice()
      .range([innerHeight, 0]);

    // Curve functions
    const curveMap = {
      linear: d3.curveLinear,
      monotone: d3.curveMonotoneX,
      step: d3.curveStep,
      cardinal: d3.curveCardinal,
    };

    // Area generator
    const area = d3
      .area<any>()
      .x((d) => (xScale as any)(d[xField]))
      .y0(innerHeight)
      .y1((d) => yScale(d[yField]))
      .curve(curveMap[curve]);

    // Draw area
    g.append("path")
      .datum(processedData)
      .attr("fill", seriesConfig.color)
      .attr("opacity", seriesConfig.opacity)
      .attr("d", area);

    // Draw line on top if enabled
    if (showLine) {
      const line = d3
        .line<any>()
        .x((d) => (xScale as any)(d[xField]))
        .y((d) => yScale(d[yField]))
        .curve(curveMap[curve]);

      g.append("path")
        .datum(processedData)
        .attr("fill", "none")
        .attr("stroke", seriesConfig.color)
        .attr("stroke-width", strokeWidth)
        .attr("d", line);
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
            .attr("x1", 0)
            .attr("x2", innerWidth)
            .attr("y1", yScale(highlight.thresholdValue))
            .attr("y2", yScale(highlight.thresholdValue))
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
            .attr("x", 0)
            .attr("y", yScale(highlight.rangeMax))
            .attr("width", innerWidth)
            .attr("height", yScale(highlight.rangeMin) - yScale(highlight.rangeMax))
            .attr("fill", color)
            .attr("opacity", 0.2);
        }
      });
    }

    // Axes
    g.append("g")
      .attr("transform", `translate(0,${innerHeight})`)
      .call(
        isTimeSeries
          ? d3.axisBottom(xScale as d3.ScaleTime<number, number>).ticks(6)
          : d3.axisBottom(xScale as d3.ScalePoint<string>),
      )
      .selectAll("text")
      .attr("transform", "rotate(-45)")
      .style("text-anchor", "end");

    g.append("g").call(d3.axisLeft(yScale));

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
    xField,
    yField,
    seriesConfig,
    title,
    width,
    height,
    highlights,
    curve,
    showLine,
    strokeWidth,
  ]);

  return <svg ref={svgRef} />;
}
