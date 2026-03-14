"use client";

import React, { useEffect, useRef } from "react";
import * as d3 from "d3";

interface D3BoxPlotProps {
  colors: readonly string[];
  showGrid?: boolean;
}

interface BoxPlotData {
  group: string;
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
  outliers?: number[];
}

export const D3BoxPlot: React.FC<D3BoxPlotProps> = ({ colors, showGrid = false }) => {
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

    // Sample box plot data
    const data: BoxPlotData[] = [
      {
        group: "Q1 2024",
        min: 54,
        q1: 66,
        median: 69,
        q3: 75,
        max: 88,
        outliers: [45, 92],
      },
      { group: "Q2 2024", min: 43, q1: 65, median: 69, q3: 76, max: 81 },
      {
        group: "Q3 2024",
        min: 31,
        q1: 39,
        median: 45,
        q3: 51,
        max: 59,
        outliers: [25],
      },
      { group: "Q4 2024", min: 39, q1: 46, median: 55, q3: 65, max: 71 },
    ];

    // Scales
    const x = d3
      .scaleBand()
      .domain(data.map((d) => d.group))
      .range([0, width])
      .padding(0.3);

    const y = d3
      .scaleLinear()
      .domain([0, d3.max(data, (d) => Math.max(d.max, ...(d.outliers || []))) || 100])
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

    const boxWidth = x.bandwidth();

    // Draw box plots
    data.forEach((d, i) => {
      const center = (x(d.group) || 0) + boxWidth / 2;
      const boxG = g.append("g").attr("class", `box-${i}`);

      // Vertical line (min to max)
      boxG
        .append("line")
        .attr("x1", center)
        .attr("x2", center)
        .attr("y1", y(d.min))
        .attr("y2", y(d.max))
        .attr("stroke", colors[0])
        .attr("stroke-width", 0.5)
        .style("opacity", 0)
        .transition()
        .delay(i * 100)
        .duration(600)
        .style("opacity", 0.7);

      // Box (Q1 to Q3)
      const box = boxG
        .append("rect")
        .attr("x", center - boxWidth / 3)
        .attr("y", y(d.q3))
        .attr("width", (boxWidth * 2) / 3)
        .attr("height", 0)
        .attr("fill", colors[0])
        .attr("fill-opacity", 0.3)
        .attr("stroke", colors[0])
        .attr("stroke-width", 1)
        .attr("rx", 1)
        .style("cursor", "pointer");

      box
        .transition()
        .delay(i * 100)
        .duration(600)
        .attr("height", y(d.q1) - y(d.q3));

      box
        .on("mouseenter", function () {
          d3.select(this)
            .transition()
            .duration(200)
            .attr("fill-opacity", 0.5)
            .attr("stroke-width", 1.5);
        })
        .on("mouseleave", function () {
          d3.select(this)
            .transition()
            .duration(200)
            .attr("fill-opacity", 0.3)
            .attr("stroke-width", 1);
        });

      // Median line
      boxG
        .append("line")
        .attr("x1", center - boxWidth / 3)
        .attr("x2", center + boxWidth / 3)
        .attr("y1", y(d.median))
        .attr("y2", y(d.median))
        .attr("stroke", colors[0])
        .attr("stroke-width", 1.5)
        .style("opacity", 0)
        .transition()
        .delay(i * 100 + 300)
        .duration(400)
        .style("opacity", 1);

      // Min whisker
      boxG
        .append("line")
        .attr("x1", center - boxWidth / 6)
        .attr("x2", center + boxWidth / 6)
        .attr("y1", y(d.min))
        .attr("y2", y(d.min))
        .attr("stroke", colors[0])
        .attr("stroke-width", 0.5)
        .style("opacity", 0)
        .transition()
        .delay(i * 100)
        .duration(600)
        .style("opacity", 0.7);

      // Max whisker
      boxG
        .append("line")
        .attr("x1", center - boxWidth / 6)
        .attr("x2", center + boxWidth / 6)
        .attr("y1", y(d.max))
        .attr("y2", y(d.max))
        .attr("stroke", colors[0])
        .attr("stroke-width", 0.5)
        .style("opacity", 0)
        .transition()
        .delay(i * 100)
        .duration(600)
        .style("opacity", 0.7);

      // Outliers
      if (d.outliers) {
        d.outliers.forEach((outlier) => {
          boxG
            .append("circle")
            .attr("cx", center)
            .attr("cy", y(outlier))
            .attr("r", 0)
            .attr("fill", "none")
            .attr("stroke", colors[0])
            .attr("stroke-width", 1)
            .style("cursor", "pointer")
            .transition()
            .delay(i * 100 + 600)
            .duration(400)
            .attr("r", 3)
            .on("end", function () {
              d3.select(this)
                .on("mouseenter", function () {
                  d3.select(this)
                    .transition()
                    .duration(200)
                    .attr("r", 4)
                    .attr("fill", colors[0])
                    .attr("fill-opacity", 0.3);
                })
                .on("mouseleave", function () {
                  d3.select(this)
                    .transition()
                    .duration(200)
                    .attr("r", 3)
                    .attr("fill", "none");
                });
            });
        });
      }
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
