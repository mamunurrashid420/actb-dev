"use client";

import React, { useEffect, useRef } from "react";
import * as d3 from "d3";

interface D3ScatterPlotProps {
  colors: readonly string[];
  showGrid?: boolean;
}

export const D3ScatterPlot: React.FC<D3ScatterPlotProps> = ({
  colors,
  showGrid = false,
}) => {
  const svgRef = useRef<SVGSVGElement>(null);

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

    // Generate sample data
    const data1 = d3.range(30).map(() => ({
      x: Math.random() * 100,
      y: Math.random() * 100,
      group: "A",
    }));

    const data2 = d3.range(30).map(() => ({
      x: Math.random() * 100,
      y: Math.random() * 100,
      group: "B",
    }));

    const data = [...data1, ...data2];

    // Scales
    const x = d3.scaleLinear().domain([0, 100]).range([0, width]);

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

      g.append("g")
        .attr("class", "grid")
        .attr("opacity", 0.1)
        .attr("transform", `translate(0,${height})`)
        .call(
          d3
            .axisBottom(x)
            .tickSize(-height)
            .tickFormat(() => ""),
        );
    }

    // Draw dots
    g.selectAll(".dot")
      .data(data)
      .join("circle")
      .attr("class", "dot")
      .attr("cx", (d) => x(d.x))
      .attr("cy", (d) => y(d.y))
      .attr("r", 0)
      .attr("fill", (d) => (d.group === "A" ? colors[0] : colors[1]))
      .attr("stroke", "#ffffff")
      .attr("stroke-width", 1)
      .attr("opacity", 0.7)
      .style("cursor", "pointer")
      .on("mouseenter", function () {
        d3.select(this)
          .transition()
          .duration(200)
          .attr("r", 8)
          .attr("opacity", 1)
          .attr("stroke-width", 2);
      })
      .on("mouseleave", function () {
        d3.select(this)
          .transition()
          .duration(200)
          .attr("r", 5)
          .attr("opacity", 0.7)
          .attr("stroke-width", 1);
      })
      .transition()
      .duration(600)
      .delay((d, i) => i * 10)
      .attr("r", 5);

    // Axes
    g.append("g")
      .attr("transform", `translate(0,${height})`)
      .call(d3.axisBottom(x).ticks(5))
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
  }, [colors, showGrid]);

  return (
    <div className="relative h-full w-full">
      <svg ref={svgRef} width="100%" height="300" />
    </div>
  );
};
