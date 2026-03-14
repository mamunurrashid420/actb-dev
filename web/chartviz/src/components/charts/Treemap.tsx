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

interface TreemapProps extends BaseChartProps {
  showLabels?: boolean;
  padding?: number;
  colorScheme?: string[];
}

export function Treemap({
  data,
  dimensions,
  dataMapping,
  dataSeries,
  title,
  width = 600,
  height = 400,
  highlights = [],
  showLabels = true,
  padding = 2,
  colorScheme,
}: TreemapProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  // Use dataMapping if available - groupBy for category, value for size
  const labelField = useMemo(
    () => dataMapping?.groupBy || dimensions.find((d) => d.type === "category")?.field,
    [dataMapping, dimensions],
  );
  const valueField = useMemo(
    () => dataMapping?.value || dimensions.find((d) => d.type === "numeric")?.field,
    [dataMapping, dimensions],
  );

  // Helper to get cell-specific styling from dataSeries
  const getCellConfig = (
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

    if (!labelField || !valueField) return;

    const margin = { top: 40, right: 10, bottom: 10, left: 10 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const svg = d3.select(svgRef.current).attr("width", width).attr("height", height);

    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Build hierarchy
    const root = d3
      .hierarchy({ children: data.rows } as any)
      .sum((d: any) => d[valueField] || 0)
      .sort((a, b) => (b.value || 0) - (a.value || 0));

    // Treemap layout
    const treemap = d3
      .treemap<any>()
      .size([innerWidth, innerHeight])
      .padding(padding)
      .round(true);

    treemap(root);

    // Build color scale - use dataSeries colors if available
    const categories = data.rows.map((d) => d[labelField]);
    const categoryColors = categories.map((cat) => {
      const config = getCellConfig(cat);
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

    // Type assertion for treemap layout results
    type TreemapNode = d3.HierarchyRectangularNode<any>;

    const cells = g
      .selectAll(".cell")
      .data(root.leaves() as TreemapNode[])
      .join("g")
      .attr("class", "cell")
      .attr("transform", (d) => `translate(${d.x0},${d.y0})`);

    cells
      .append("rect")
      .attr("width", (d) => d.x1 - d.x0)
      .attr("height", (d) => d.y1 - d.y0)
      .attr("fill", (d) => {
        const highlight = highlights.find(
          (h) =>
            (h.type === HighlightType.ROW || h.type === HighlightType.POINT_SET) &&
            h.rowIds?.includes(d.data.row_id),
        );
        if (highlight) {
          return getHighlightColor(highlight.insightId, insightColorMap);
        }
        return colorScale(d.data[labelField]);
      })
      .attr("stroke", (d) => {
        const highlight = highlights.find(
          (h) =>
            (h.type === HighlightType.ROW || h.type === HighlightType.POINT_SET) &&
            h.rowIds?.includes(d.data.row_id),
        );
        return highlight
          ? getHighlightColor(highlight.insightId, insightColorMap)
          : "white";
      })
      .attr("stroke-width", (d) => {
        const highlight = highlights.find(
          (h) =>
            (h.type === HighlightType.ROW || h.type === HighlightType.POINT_SET) &&
            h.rowIds?.includes(d.data.row_id),
        );
        return highlight ? 3 : 2;
      })
      .attr("opacity", (d) => getCellConfig(d.data[labelField]).opacity)
      .style("cursor", "pointer")
      .on("mouseenter", function (event, d) {
        const config = getCellConfig(d.data[labelField]);
        d3.select(this).attr("opacity", Math.min(config.opacity + 0.1, 1));
      })
      .on("mouseleave", function (event, d) {
        d3.select(this).attr("opacity", getCellConfig(d.data[labelField]).opacity);
      });

    // Labels - use labels from dataSeries if available
    if (showLabels) {
      cells
        .append("text")
        .attr("x", 5)
        .attr("y", 18)
        .style("font-size", (d) => {
          const cellWidth = d.x1 - d.x0;
          return cellWidth > 60 ? "12px" : "10px";
        })
        .style("font-weight", "bold")
        .style("fill", "white")
        .style("text-shadow", "1px 1px 2px rgba(0,0,0,0.5)")
        .text((d) => {
          const cellWidth = d.x1 - d.x0;
          const cellConfig = getCellConfig(d.data[labelField]);
          const label = cellConfig.label || d.data[labelField];
          if (cellWidth < 40) return "";
          if (cellWidth < 80 && label.length > 8) return label.substring(0, 6) + "...";
          return label;
        });

      cells
        .append("text")
        .attr("x", 5)
        .attr("y", 33)
        .style("font-size", "11px")
        .style("fill", "white")
        .style("opacity", 0.9)
        .style("text-shadow", "1px 1px 2px rgba(0,0,0,0.5)")
        .text((d) => {
          const cellWidth = d.x1 - d.x0;
          if (cellWidth < 50) return "";
          return d.value?.toLocaleString() || "";
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
    labelField,
    valueField,
    dataSeries,
    title,
    width,
    height,
    highlights,
    showLabels,
    padding,
    colorScheme,
  ]);

  return <svg ref={svgRef} />;
}
