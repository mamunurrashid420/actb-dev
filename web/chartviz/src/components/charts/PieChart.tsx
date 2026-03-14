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

interface PieChartProps extends BaseChartProps {
  showLabels?: boolean;
  showPercentages?: boolean;
  colorScheme?: string[];
}

export function PieChart({
  data,
  dimensions,
  dataMapping,
  dataSeries,
  title,
  width = 600,
  height = 400,
  highlights = [],
  showLabels = true,
  showPercentages = true,
  colorScheme,
}: PieChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  // Use dataMapping if available - groupBy is the category field
  const categoryField = useMemo(
    () => dataMapping?.groupBy || dimensions.find((d) => d.type === "category")?.field,
    [dataMapping, dimensions],
  );
  const valueField = useMemo(
    () => dataMapping?.value || dimensions.find((d) => d.type === "numeric")?.field,
    [dataMapping, dimensions],
  );

  // Helper to get slice-specific styling from dataSeries
  const getSliceConfig = (
    categoryValue: string,
  ): { color?: string; opacity: number; label?: string } => {
    if (!dataSeries || dataSeries.length === 0) {
      return { opacity: 0.9 };
    }
    const config = dataSeries.find((s) => s.groupValue === categoryValue);
    if (!config) return { opacity: 0.9 };
    return {
      color: getSentimentColor(config.sentiment),
      opacity: getProminenceOpacity(config.prominence),
      label: config.label,
    };
  };

  useEffect(() => {
    if (!svgRef.current || !data.rows.length) return;

    d3.select(svgRef.current).selectAll("*").remove();

    if (!categoryField || !valueField) return;

    const margin = { top: 40, right: 100, bottom: 20, left: 20 };
    const radius =
      Math.min(
        width - margin.left - margin.right,
        height - margin.top - margin.bottom,
      ) / 2;

    const svg = d3.select(svgRef.current).attr("width", width).attr("height", height);

    const g = svg
      .append("g")
      .attr(
        "transform",
        `translate(${(width - margin.right + margin.left) / 2},${height / 2})`,
      );

    const pie = d3
      .pie<any>()
      .value((d) => d[valueField])
      .sort(null);

    const arc = d3.arc<any>().innerRadius(0).outerRadius(radius);

    const labelArc = d3
      .arc<any>()
      .innerRadius(radius * 0.6)
      .outerRadius(radius * 0.6);

    // Build color scale - use dataSeries colors if available
    const categories = data.rows.map((d) => d[categoryField]);
    const categoryColors = categories.map((cat) => {
      const config = getSliceConfig(cat);
      return config.color;
    });
    const fallbackColors = colorScheme || (d3.schemeSet2 as string[]);
    const colorScale = d3
      .scaleOrdinal<string>()
      .domain(categories)
      .range(
        categoryColors.some((c) => c !== undefined)
          ? categoryColors.map((c, i) => c || fallbackColors[i % fallbackColors.length])
          : fallbackColors,
      );

    const insightColorMap = createInsightColorMap(highlights);

    const arcs = g
      .selectAll(".arc")
      .data(pie(data.rows))
      .join("g")
      .attr("class", "arc");

    arcs
      .append("path")
      .attr("d", arc)
      .attr("fill", (d) => {
        // Check if this slice is highlighted
        const highlight = highlights.find(
          (h) =>
            (h.type === HighlightType.ROW || h.type === HighlightType.POINT_SET) &&
            h.rowIds?.includes(d.data.row_id),
        );
        if (highlight) {
          return getHighlightColor(highlight.insightId, insightColorMap);
        }
        return colorScale(d.data[categoryField]) as string;
      })
      .attr("stroke", "white")
      .attr("stroke-width", 2)
      .attr("opacity", (d) => getSliceConfig(d.data[categoryField]).opacity)
      .style("cursor", "pointer")
      .on("mouseenter", function (event, d) {
        const config = getSliceConfig(d.data[categoryField]);
        d3.select(this).attr("opacity", Math.min(config.opacity + 0.1, 1));
      })
      .on("mouseleave", function (event, d) {
        d3.select(this).attr("opacity", getSliceConfig(d.data[categoryField]).opacity);
      });

    // Labels
    if (showLabels || showPercentages) {
      arcs
        .append("text")
        .attr("transform", (d) => `translate(${labelArc.centroid(d)})`)
        .attr("text-anchor", "middle")
        .style("font-size", "12px")
        .style("fill", "white")
        .style("font-weight", "bold")
        .text((d) => {
          const percent = ((d.endAngle - d.startAngle) / (2 * Math.PI)) * 100;
          if (percent < 5) return ""; // Don't show label for small slices
          if (showPercentages) return `${percent.toFixed(1)}%`;
          return d.data[categoryField];
        });
    }

    // Legend - use labels from dataSeries if available
    const legend = svg.append("g").attr("transform", `translate(${width - 90}, 40)`);

    data.rows.forEach((row, i) => {
      const sliceConfig = getSliceConfig(row[categoryField]);
      const legendLabel = sliceConfig.label || row[categoryField];

      const legendRow = legend.append("g").attr("transform", `translate(0, ${i * 20})`);

      legendRow
        .append("rect")
        .attr("width", 12)
        .attr("height", 12)
        .attr("fill", colorScale(row[categoryField]) as string);

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
    valueField,
    dataSeries,
    title,
    width,
    height,
    highlights,
    showLabels,
    showPercentages,
    colorScheme,
  ]);

  return <svg ref={svgRef} />;
}
