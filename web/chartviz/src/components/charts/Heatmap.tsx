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
import { SENTIMENT_COLORS } from "@/lib/charts/style-guide";

interface HeatmapProps extends BaseChartProps {
  showValues?: boolean;
  cellPadding?: number;
}

export function Heatmap({
  data,
  dimensions,
  dataMapping,
  dataSeries,
  title,
  width = 600,
  height = 400,
  highlights = [],
  showValues = false,
  cellPadding = 0.05,
}: HeatmapProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  // Use dataMapping if available - column for x, row for y
  const xField = useMemo(() => {
    if (dataMapping?.column) return dataMapping.column;
    const categoryDims = dimensions.filter((d) => d.type === "category");
    return (
      categoryDims[0]?.field ||
      dimensions.find((d) => d.field.includes("x") || d.field === "date")?.field
    );
  }, [dataMapping, dimensions]);

  const yField = useMemo(() => {
    if (dataMapping?.row) return dataMapping.row;
    const categoryDims = dimensions.filter((d) => d.type === "category");
    return (
      categoryDims[1]?.field || dimensions.find((d) => d.field.includes("y"))?.field
    );
  }, [dataMapping, dimensions]);

  const valueField = useMemo(
    () => dataMapping?.value || dimensions.find((d) => d.type === "numeric")?.field,
    [dataMapping, dimensions],
  );

  // Check if dataSeries has valueRange classifications for semantic coloring
  const valueRangeClassifications = useMemo(() => {
    if (!dataSeries) return null;
    const withRanges = dataSeries.filter((s) => s.valueRange);
    return withRanges.length > 0 ? withRanges : null;
  }, [dataSeries]);

  // Get color based on value using valueRange classifications or fallback to sequential scale
  const getValueColor = (
    value: number,
    colorScale: d3.ScaleSequential<string, never>,
  ): string => {
    if (valueRangeClassifications) {
      // Find matching classification by value range
      const match = valueRangeClassifications.find((s) => {
        if (!s.valueRange) return false;
        const min = s.valueRange.min;
        const max = s.valueRange.max === Infinity ? Number.MAX_VALUE : s.valueRange.max;
        return value >= min && value < max;
      });
      if (match && match.sentiment) {
        return SENTIMENT_COLORS[match.sentiment];
      }
    }
    return colorScale(value);
  };

  useEffect(() => {
    if (!svgRef.current || !data.rows.length) return;

    d3.select(svgRef.current).selectAll("*").remove();

    if (!xField || !yField || !valueField) return;

    const margin = { top: 40, right: 100, bottom: 80, left: 100 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const svg = d3.select(svgRef.current).attr("width", width).attr("height", height);

    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Get unique x and y values
    const xValues = Array.from(new Set(data.rows.map((d) => d[xField])));
    const yValues = Array.from(new Set(data.rows.map((d) => d[yField])));

    // Scales
    const xScale = d3
      .scaleBand()
      .domain(xValues)
      .range([0, innerWidth])
      .padding(cellPadding);

    const yScale = d3
      .scaleBand()
      .domain(yValues)
      .range([0, innerHeight])
      .padding(cellPadding);

    const colorScale = d3
      .scaleSequential()
      .domain(d3.extent(data.rows, (d) => d[valueField]) as [number, number])
      .interpolator(d3.interpolateYlOrRd);

    const insightColorMap = createInsightColorMap(highlights);

    // Draw cells
    g.selectAll(".cell")
      .data(data.rows)
      .join("rect")
      .attr("class", "cell")
      .attr("x", (d) => xScale(d[xField]) || 0)
      .attr("y", (d) => yScale(d[yField]) || 0)
      .attr("width", xScale.bandwidth())
      .attr("height", yScale.bandwidth())
      .attr("fill", (d) => {
        const highlight = highlights.find(
          (h) =>
            (h.type === HighlightType.ROW || h.type === HighlightType.POINT_SET) &&
            h.rowIds?.includes(d.row_id),
        );
        if (highlight) {
          return getHighlightColor(highlight.insightId, insightColorMap);
        }
        return getValueColor(d[valueField], colorScale);
      })
      .attr("stroke", (d) => {
        const highlight = highlights.find(
          (h) =>
            (h.type === HighlightType.ROW || h.type === HighlightType.POINT_SET) &&
            h.rowIds?.includes(d.row_id),
        );
        return highlight
          ? getHighlightColor(highlight.insightId, insightColorMap)
          : "white";
      })
      .attr("stroke-width", (d) => {
        const highlight = highlights.find(
          (h) =>
            (h.type === HighlightType.ROW || h.type === HighlightType.POINT_SET) &&
            h.rowIds?.includes(d.row_id),
        );
        return highlight ? 3 : 1;
      })
      .style("cursor", "pointer")
      .on("mouseenter", function () {
        d3.select(this).attr("opacity", 0.8);
      })
      .on("mouseleave", function () {
        d3.select(this).attr("opacity", 1);
      });

    // Show values in cells if enabled
    if (showValues) {
      g.selectAll(".cell-text")
        .data(data.rows)
        .join("text")
        .attr("class", "cell-text")
        .attr("x", (d) => (xScale(d[xField]) || 0) + xScale.bandwidth() / 2)
        .attr("y", (d) => (yScale(d[yField]) || 0) + yScale.bandwidth() / 2)
        .attr("text-anchor", "middle")
        .attr("dy", "0.35em")
        .style("font-size", "10px")
        .style("fill", (d) => {
          // Use white text on dark cells
          const value = d[valueField];
          const [min, max] = d3.extent(data.rows, (d) => d[valueField]) as [
            number,
            number,
          ];
          const normalized = (value - min) / (max - min);
          return normalized > 0.5 ? "white" : "black";
        })
        .text((d) => d[valueField].toFixed(1));
    }

    // Axes
    g.append("g")
      .attr("transform", `translate(0,${innerHeight})`)
      .call(d3.axisBottom(xScale))
      .selectAll("text")
      .attr("transform", "rotate(-45)")
      .style("text-anchor", "end");

    g.append("g").call(d3.axisLeft(yScale));

    // Color legend
    const legendWidth = 20;
    const legendHeight = innerHeight;
    const legendScale = d3
      .scaleLinear()
      .domain(colorScale.domain())
      .range([legendHeight, 0]);

    const legend = svg
      .append("g")
      .attr("transform", `translate(${width - 60}, ${margin.top})`);

    const legendAxis = d3.axisRight(legendScale).ticks(5);

    // Gradient for legend
    const defs = svg.append("defs");
    const gradient = defs
      .append("linearGradient")
      .attr("id", "heatmap-gradient")
      .attr("x1", "0%")
      .attr("y1", "100%")
      .attr("x2", "0%")
      .attr("y2", "0%");

    const [minVal, maxVal] = colorScale.domain();
    gradient
      .selectAll("stop")
      .data(d3.range(0, 1.01, 0.1))
      .join("stop")
      .attr("offset", (d) => `${d * 100}%`)
      .attr("stop-color", (d) => colorScale(minVal + d * (maxVal - minVal)));

    legend
      .append("rect")
      .attr("width", legendWidth)
      .attr("height", legendHeight)
      .style("fill", "url(#heatmap-gradient)");

    legend
      .append("g")
      .attr("transform", `translate(${legendWidth}, 0)`)
      .call(legendAxis);

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
    valueField,
    valueRangeClassifications,
    title,
    width,
    height,
    highlights,
    showValues,
    cellPadding,
  ]);

  return <svg ref={svgRef} />;
}
