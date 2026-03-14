"use client";

import React, { useEffect, useRef } from "react";
import * as d3 from "d3";

interface D3PieChartProps {
  colors: readonly string[];
}

export const D3PieChart: React.FC<D3PieChartProps> = ({ colors }) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const width = svgRef.current.clientWidth;
    const height = 300;
    const radius = Math.min(width, height) / 2 - 40;

    const g = svg
      .append("g")
      .attr("transform", `translate(${width / 2},${height / 2})`);

    // Sample data
    const data = [
      { label: "A", value: 44 },
      { label: "B", value: 55 },
      { label: "C", value: 13 },
      { label: "D", value: 43 },
      { label: "E", value: 22 },
    ];

    // Pie generator
    const pie = d3
      .pie<(typeof data)[0]>()
      .value((d) => d.value)
      .sort(null);

    // Arc generator
    const arc = d3
      .arc<d3.PieArcDatum<(typeof data)[0]>>()
      .innerRadius(0)
      .outerRadius(radius);

    const arcHover = d3
      .arc<d3.PieArcDatum<(typeof data)[0]>>()
      .innerRadius(0)
      .outerRadius(radius + 10);

    // Draw slices
    const slices = g
      .selectAll(".slice")
      .data(pie(data))
      .join("path")
      .attr("class", "slice")
      .attr("d", arc)
      .attr("fill", (d, i) => colors[i % colors.length])
      .attr("stroke", "#ffffff")
      .attr("stroke-width", 2)
      .style("cursor", "pointer")
      .on("mouseenter", function (event, d) {
        d3.select(this)
          .transition()
          .duration(200)
          .attrTween("d", function () {
            return function () {
              return arcHover(d) || "";
            };
          });
      })
      .on("mouseleave", function (event, d) {
        d3.select(this)
          .transition()
          .duration(200)
          .attrTween("d", function () {
            return function () {
              return arc(d) || "";
            };
          });
      });

    // Animate slices
    slices
      .transition()
      .duration(800)
      .attrTween("d", function (d) {
        const interpolate = d3.interpolate({ startAngle: 0, endAngle: 0 }, d);
        return function (t) {
          return arc(interpolate(t)) || "";
        };
      });

    // Add labels
    g.selectAll(".label")
      .data(pie(data))
      .join("text")
      .attr("class", "label")
      .attr("transform", (d) => `translate(${arc.centroid(d)})`)
      .attr("text-anchor", "middle")
      .attr("font-size", "11px")
      .attr("font-family", "Inter, sans-serif")
      .attr("fill", "#ffffff")
      .attr("font-weight", "500")
      .text((d) => d.data.label)
      .style("opacity", 0)
      .transition()
      .delay(800)
      .duration(400)
      .style("opacity", 1);
  }, [colors]);

  return (
    <div className="relative h-full w-full">
      <svg ref={svgRef} width="100%" height="300" />
    </div>
  );
};
