"use client";

import React, { useEffect, useRef } from "react";
import * as d3 from "d3";

interface D3BarChartProps {
  colors: readonly string[];
  showGrid?: boolean;
}

export const D3BarChart: React.FC<D3BarChartProps> = ({ colors, showGrid = false }) => {
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

    // Sample data
    const data = [
      { category: "A", value: 44 },
      { category: "B", value: 55 },
      { category: "C", value: 57 },
      { category: "D", value: 56 },
      { category: "E", value: 61 },
      { category: "F", value: 58 },
    ];

    // Scales
    const x = d3
      .scaleBand()
      .domain(data.map((d) => d.category))
      .range([0, width])
      .padding(0.3);

    const y = d3
      .scaleLinear()
      .domain([0, d3.max(data, (d) => d.value) || 100])
      .nice()
      .range([height, 0]);

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

    // Bars
    g.selectAll(".bar")
      .data(data)
      .join("rect")
      .attr("class", "bar")
      .attr("x", (d) => x(d.category) || 0)
      .attr("y", height)
      .attr("width", x.bandwidth())
      .attr("height", 0)
      .attr("fill", colors[0])
      .attr("rx", 4)
      .style("cursor", "pointer")
      .on("mouseenter", function () {
        d3.select(this)
          .transition()
          .duration(200)
          .attr("fill", colors[1])
          .attr("transform", "translateY(-2px)");
      })
      .on("mouseleave", function () {
        d3.select(this)
          .transition()
          .duration(200)
          .attr("fill", colors[0])
          .attr("transform", "translateY(0)");
      })
      .transition()
      .duration(800)
      .delay((d, i) => i * 100)
      .attr("y", (d) => y(d.value))
      .attr("height", (d) => height - y(d.value));

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
  }, [colors, showGrid]);

  return (
    <div className="relative h-full w-full">
      <svg ref={svgRef} width="100%" height="300" />
    </div>
  );
};
