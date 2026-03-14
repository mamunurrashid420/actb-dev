"use client";

import React, { useEffect, useRef, useState } from "react";
import * as d3 from "d3";

interface D3ViolinPlotProps {
  colors: readonly string[];
  showGrid?: boolean;
}

export const D3ViolinPlot: React.FC<D3ViolinPlotProps> = ({
  colors,
  showGrid = false,
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoveredGroup, setHoveredGroup] = useState<string | null>(null);

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const margin = { top: 20, right: 30, bottom: 40, left: 50 };
    const width = svgRef.current.clientWidth - margin.left - margin.right;
    const height = 300 - margin.top - margin.bottom;

    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Generate sample data for violin plot
    const groups = ["Group A", "Group B", "Group C"];
    const data = groups.map((group) => ({
      group,
      values: d3.range(100).map(() => d3.randomNormal(50, 15)()),
    }));

    // Scales
    const x = d3.scaleBand().domain(groups).range([0, width]).padding(0.3);

    const y = d3.scaleLinear().domain([0, 100]).range([height, 0]);

    // Grid
    if (showGrid) {
      g.append("g")
        .attr("class", "grid")
        .attr("opacity", 0.1)
        .call(
          d3
            .axisLeft(y)
            .tickSize(-width)
            .tickFormat(() => ""),
        );
    }

    // Compute kernel density estimation
    const kde = (
      kernel: (v: number) => number,
      thresholds: number[],
      data: number[],
    ) => {
      return thresholds.map((t) => [t, d3.mean(data, (d) => kernel(t - d)) || 0]);
    };

    const epanechnikov = (bandwidth: number) => {
      return (v: number) =>
        Math.abs((v /= bandwidth)) <= 1 ? (0.75 * (1 - v * v)) / bandwidth : 0;
    };

    // Draw violins
    data.forEach((d, i) => {
      const density = kde(epanechnikov(7), y.ticks(50), d.values);
      const maxDensity = d3.max(density, (d) => d[1]) || 1;

      const xScale = d3
        .scaleLinear()
        .domain([0, maxDensity])
        .range([0, x.bandwidth() / 2]);

      const area = d3
        .area<[number, number]>()
        .x0((point) => (x(d.group) || 0) + x.bandwidth() / 2 - xScale(point[1]))
        .x1((point) => (x(d.group) || 0) + x.bandwidth() / 2 + xScale(point[1]))
        .y((point) => y(point[0]))
        .curve(d3.curveCatmullRom);

      const violin = g
        .append("path")
        .datum(density as [number, number][])
        .attr("d", area)
        .attr("fill", colors[i % colors.length])
        .attr("opacity", hoveredGroup === d.group ? 0.9 : 0.7)
        .attr("stroke", colors[i % colors.length])
        .attr("stroke-width", 1)
        .style("cursor", "pointer")
        .style("transition", "all 0.3s ease");

      violin
        .on("mouseenter", function () {
          setHoveredGroup(d.group);
          d3.select(this)
            .transition()
            .duration(200)
            .attr("opacity", 0.9)
            .attr("stroke-width", 2);
        })
        .on("mouseleave", function () {
          setHoveredGroup(null);
          d3.select(this)
            .transition()
            .duration(200)
            .attr("opacity", 0.7)
            .attr("stroke-width", 1);
        });
    });

    // Axes
    g.append("g")
      .attr("transform", `translate(0,${height})`)
      .call(d3.axisBottom(x))
      .selectAll("text")
      .style("font-size", "11px")
      .style("font-family", "Inter, sans-serif")
      .style("fill", "#6b7280");

    g.append("g")
      .call(d3.axisLeft(y).ticks(5))
      .selectAll("text")
      .style("font-size", "11px")
      .style("font-family", "Inter, sans-serif")
      .style("fill", "#6b7280");

    // Remove domain lines
    g.selectAll(".domain").remove();
    g.selectAll(".tick line").remove();
  }, [colors, showGrid, hoveredGroup]);

  return (
    <div className="relative h-full w-full">
      <svg ref={svgRef} width="100%" height="300" />
    </div>
  );
};
