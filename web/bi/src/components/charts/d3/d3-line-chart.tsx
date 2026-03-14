"use client";

import React, { useEffect, useRef } from "react";
import * as d3 from "d3";

interface D3LineChartProps {
  colors: readonly string[];
  showGrid?: boolean;
}

export const D3LineChart: React.FC<D3LineChartProps> = ({
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

    // Sample data
    const data = [
      { month: "Jan", value1: 30, value2: 20 },
      { month: "Feb", value1: 40, value2: 30 },
      { month: "Mar", value1: 35, value2: 25 },
      { month: "Apr", value1: 50, value2: 40 },
      { month: "May", value1: 49, value2: 39 },
      { month: "Jun", value1: 60, value2: 50 },
      { month: "Jul", value1: 70, value2: 60 },
    ];

    // Scales
    const x = d3
      .scaleBand()
      .domain(data.map((d) => d.month))
      .range([0, width])
      .padding(0.1);

    const y = d3
      .scaleLinear()
      .domain([0, d3.max(data, (d) => Math.max(d.value1, d.value2)) || 100])
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

    // Line generators
    const line1 = d3
      .line<(typeof data)[0]>()
      .x((d) => (x(d.month) || 0) + x.bandwidth() / 2)
      .y((d) => y(d.value1))
      .curve(d3.curveMonotoneX);

    const line2 = d3
      .line<(typeof data)[0]>()
      .x((d) => (x(d.month) || 0) + x.bandwidth() / 2)
      .y((d) => y(d.value2))
      .curve(d3.curveMonotoneX);

    // Draw lines
    g.append("path")
      .datum(data)
      .attr("fill", "none")
      .attr("stroke", colors[0])
      .attr("stroke-width", 2)
      .attr("d", line1)
      .style("transition", "all 0.3s ease");

    g.append("path")
      .datum(data)
      .attr("fill", "none")
      .attr("stroke", colors[1])
      .attr("stroke-width", 2)
      .attr("d", line2)
      .style("transition", "all 0.3s ease");

    // Add dots with hover effect
    [
      {
        values: data.map((d) => ({ ...d, value: d.value1 })),
        color: colors[0],
        index: 0,
      },
      {
        values: data.map((d) => ({ ...d, value: d.value2 })),
        color: colors[1],
        index: 1,
      },
    ].forEach((series) => {
      g.selectAll(`.dot-series-${series.index}`)
        .data(series.values)
        .join("circle")
        .attr("class", `dot-series-${series.index}`)
        .attr("cx", (d) => (x(d.month) || 0) + x.bandwidth() / 2)
        .attr("cy", (d) => y(d.value))
        .attr("r", 4)
        .attr("fill", series.color)
        .attr("stroke", "#ffffff")
        .attr("stroke-width", 2)
        .style("cursor", "pointer")
        .on("mouseenter", function () {
          d3.select(this).transition().duration(200).attr("r", 6);
        })
        .on("mouseleave", function () {
          d3.select(this).transition().duration(200).attr("r", 4);
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
  }, [colors, showGrid]);

  return (
    <div className="relative h-full w-full">
      <svg ref={svgRef} width="100%" height="300" />
    </div>
  );
};
