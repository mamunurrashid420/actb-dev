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

interface ScatterPlotProps extends BaseChartProps {
  sizeField?: string;
  colorField?: string;
  showTrendline?: boolean;
  dotSize?: number;
}

export function ScatterPlot({
  data,
  dimensions,
  dataMapping,
  dataSeries,
  title,
  width = 600,
  height = 400,
  highlights = [],
  dotSize = 5,
}: ScatterPlotProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  // Use dataMapping if available
  const xField = useMemo(() => {
    if (dataMapping?.xAxis) return dataMapping.xAxis;
    const numericDims = dimensions.filter((d) => d.type === "numeric");
    return numericDims[0]?.field;
  }, [dataMapping, dimensions]);

  const yField = useMemo(() => {
    if (dataMapping?.yAxis) return dataMapping.yAxis;
    const numericDims = dimensions.filter((d) => d.type === "numeric");
    return numericDims[1]?.field;
  }, [dataMapping, dimensions]);

  const sizeField = useMemo(() => {
    // Third numeric dimension for size
    const numericDims = dimensions.filter((d) => d.type === "numeric");
    return numericDims[2]?.field;
  }, [dimensions]);

  const colorField = useMemo(
    () => dataMapping?.groupBy || dimensions.find((d) => d.type === "category")?.field,
    [dataMapping, dimensions],
  );

  // Get series config for styling
  const seriesConfig = useMemo(() => {
    if (!dataSeries || dataSeries.length === 0) {
      return { color: "#4F46E5", opacity: 0.7 };
    }
    const config = dataSeries[0];
    return {
      color: getSentimentColor(config.sentiment),
      opacity: getProminenceOpacity(config.prominence),
    };
  }, [dataSeries]);

  useEffect(() => {
    if (!svgRef.current || !data.rows.length) return;

    d3.select(svgRef.current).selectAll("*").remove();

    if (!xField || !yField) return;

    const margin = { top: 40, right: 100, bottom: 60, left: 60 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const svg = d3.select(svgRef.current).attr("width", width).attr("height", height);

    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Scales
    const xScale = d3
      .scaleLinear()
      .domain(d3.extent(data.rows, (d) => d[xField]) as [number, number])
      .nice()
      .range([0, innerWidth]);

    const yScale = d3
      .scaleLinear()
      .domain(d3.extent(data.rows, (d) => d[yField]) as [number, number])
      .nice()
      .range([innerHeight, 0]);

    const sizeScale = sizeField
      ? d3
          .scaleSqrt()
          .domain(d3.extent(data.rows, (d) => d[sizeField]) as [number, number])
          .range([3, 20])
      : null;

    const colorScale = colorField
      ? d3
          .scaleOrdinal(d3.schemeSet2)
          .domain(Array.from(new Set(data.rows.map((d) => d[colorField]))))
      : null;

    // Draw points
    g.selectAll(".dot")
      .data(data.rows)
      .join("circle")
      .attr("class", "dot")
      .attr("cx", (d) => xScale(d[xField]))
      .attr("cy", (d) => yScale(d[yField]))
      .attr("r", (d) => (sizeScale ? sizeScale(d[sizeField!]) : dotSize))
      .attr("fill", (d) =>
        colorScale && colorField
          ? (colorScale(d[colorField]) as string)
          : seriesConfig.color,
      )
      .attr("opacity", seriesConfig.opacity)
      .attr("stroke", "white")
      .attr("stroke-width", 1)
      .style("cursor", "pointer")
      .on("mouseenter", function () {
        d3.select(this)
          .attr("opacity", Math.min(seriesConfig.opacity + 0.3, 1))
          .attr("stroke-width", 2);
      })
      .on("mouseleave", function () {
        d3.select(this).attr("opacity", seriesConfig.opacity).attr("stroke-width", 1);
      });

    // Apply highlights
    if (highlights.length > 0) {
      const insightColorMap = createInsightColorMap(highlights);

      highlights.forEach((highlight) => {
        const color = getHighlightColor(highlight.insightId, insightColorMap);

        if (
          (highlight.type === HighlightType.POINT ||
            highlight.type === HighlightType.POINT_SET) &&
          highlight.rowIds
        ) {
          const rowIds = highlight.rowIds;
          g.selectAll(".dot")
            .filter((d: any) => rowIds.includes(d.row_id))
            .attr("fill", color)
            .attr(
              "r",
              (d: any) =>
                (sizeScale && sizeField ? sizeScale(d[sizeField]) : dotSize) * 1.5,
            )
            .attr("stroke", color)
            .attr("stroke-width", 3);
        }

        if (
          highlight.type === HighlightType.THRESHOLD &&
          highlight.thresholdValue !== undefined
        ) {
          const field = highlight.thresholdRangeField || yField;
          const scale = field === xField ? xScale : yScale;
          const isX = field === xField;

          g.append("line")
            .attr("x1", isX ? scale(highlight.thresholdValue) : 0)
            .attr("x2", isX ? scale(highlight.thresholdValue) : innerWidth)
            .attr("y1", isX ? 0 : scale(highlight.thresholdValue))
            .attr("y2", isX ? innerHeight : scale(highlight.thresholdValue))
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

    // Axis labels
    g.append("text")
      .attr("x", innerWidth / 2)
      .attr("y", innerHeight + 50)
      .attr("text-anchor", "middle")
      .style("font-size", "12px")
      .style("fill", "currentColor")
      .text(xField);

    g.append("text")
      .attr("transform", "rotate(-90)")
      .attr("x", -innerHeight / 2)
      .attr("y", -45)
      .attr("text-anchor", "middle")
      .style("font-size", "12px")
      .style("fill", "currentColor")
      .text(yField);

    // Legend for color field
    if (colorScale && colorField) {
      const categories = Array.from(new Set(data.rows.map((d) => d[colorField])));
      const legend = svg
        .append("g")
        .attr("transform", `translate(${width - 90}, ${margin.top})`);

      categories.forEach((cat, i) => {
        const legendRow = legend
          .append("g")
          .attr("transform", `translate(0, ${i * 20})`);

        legendRow
          .append("circle")
          .attr("cx", 6)
          .attr("cy", 6)
          .attr("r", 6)
          .attr("fill", colorScale(cat) as string);

        legendRow
          .append("text")
          .attr("x", 18)
          .attr("y", 10)
          .style("font-size", "12px")
          .style("fill", "currentColor")
          .text(cat);
      });
    }

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
    sizeField,
    colorField,
    seriesConfig,
    title,
    width,
    height,
    highlights,
    dotSize,
  ]);

  return <svg ref={svgRef} />;
}
