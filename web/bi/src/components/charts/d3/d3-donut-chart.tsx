"use client";

import React, { useEffect, useRef } from "react";
import * as d3 from "d3";

interface D3DonutChartProps {
  colors: readonly string[];
}

export const D3DonutChart: React.FC<D3DonutChartProps> = ({ colors }) => {
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
      { label: "Product A", value: 44 },
      { label: "Product B", value: 55 },
      { label: "Product C", value: 41 },
      { label: "Product D", value: 17 },
      { label: "Product E", value: 15 },
    ];

    const total = d3.sum(data, (d) => d.value);

    // Pie generator
    const pie = d3
      .pie<(typeof data)[0]>()
      .value((d) => d.value)
      .sort(null);

    // Arc generator
    const arc = d3
      .arc<d3.PieArcDatum<(typeof data)[0]>>()
      .innerRadius(radius * 0.6)
      .outerRadius(radius);

    const arcHover = d3
      .arc<d3.PieArcDatum<(typeof data)[0]>>()
      .innerRadius(radius * 0.6)
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

    // Center text
    g.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", "-0.5em")
      .attr("font-size", "24px")
      .attr("font-family", "Inter, sans-serif")
      .attr("font-weight", "600")
      .attr("fill", "#374151")
      .text(total);

    g.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", "1em")
      .attr("font-size", "11px")
      .attr("font-family", "Inter, sans-serif")
      .attr("fill", "#6b7280")
      .text("Total");
  }, [colors]);

  return (
    <div className="relative h-full w-full">
      <svg ref={svgRef} width="100%" height="300" />
    </div>
  );
};
