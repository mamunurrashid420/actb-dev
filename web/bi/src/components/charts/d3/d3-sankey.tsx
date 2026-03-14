"use client";

import React, { useEffect, useRef } from "react";
import * as d3 from "d3";

interface D3SankeyProps {
  colors: readonly string[];
}

export const D3Sankey: React.FC<D3SankeyProps> = ({ colors }) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const margin = { top: 10, right: 10, bottom: 10, left: 10 };
    const width = svgRef.current.clientWidth - margin.left - margin.right;
    const height = 300 - margin.top - margin.bottom;

    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Sample Sankey data
    const data = {
      nodes: [
        { name: "Source A" },
        { name: "Source B" },
        { name: "Source C" },
        { name: "Middle 1" },
        { name: "Middle 2" },
        { name: "Target X" },
        { name: "Target Y" },
      ],
      links: [
        { source: 0, target: 3, value: 30 },
        { source: 1, target: 3, value: 20 },
        { source: 2, target: 4, value: 25 },
        { source: 3, target: 5, value: 35 },
        { source: 3, target: 6, value: 15 },
        { source: 4, target: 6, value: 25 },
      ],
    };

    // Simple Sankey layout (simplified version)
    const nodeWidth = 20;
    const nodePadding = 30;

    // Position nodes
    const layers = [
      [0, 1, 2], // Sources
      [3, 4], // Middle
      [5, 6], // Targets
    ];

    const layerWidth = width / (layers.length - 1);

    data.nodes.forEach((node: any, i) => {
      const layerIndex = layers.findIndex((layer) => layer.includes(i));
      const positionInLayer = layers[layerIndex].indexOf(i);
      const layerHeight = height / layers[layerIndex].length;

      node.x0 = layerIndex * layerWidth;
      node.x1 = node.x0 + nodeWidth;
      node.y0 = positionInLayer * layerHeight + nodePadding;
      node.y1 = node.y0 + (layerHeight - nodePadding * 2);
    });

    // Draw links
    g.append("g")
      .selectAll("path")
      .data(data.links)
      .join("path")
      .attr("d", (d: any) => {
        const sourceNode = data.nodes[d.source] as any;
        const targetNode = data.nodes[d.target] as any;
        return `
          M ${sourceNode.x1} ${(sourceNode.y0 + sourceNode.y1) / 2}
          C ${(sourceNode.x1 + targetNode.x0) / 2} ${(sourceNode.y0 + sourceNode.y1) / 2},
            ${(sourceNode.x1 + targetNode.x0) / 2} ${(targetNode.y0 + targetNode.y1) / 2},
            ${targetNode.x0} ${(targetNode.y0 + targetNode.y1) / 2}
        `;
      })
      .attr("fill", "none")
      .attr("stroke", colors[0])
      .attr("stroke-opacity", 0.3)
      .attr("stroke-width", (d: any) => Math.max(1, d.value / 2))
      .style("cursor", "pointer")
      .on("mouseenter", function () {
        d3.select(this)
          .transition()
          .duration(200)
          .attr("stroke-opacity", 0.7)
          .attr("stroke-width", (d: any) => Math.max(1, d.value / 1.5));
      })
      .on("mouseleave", function () {
        d3.select(this)
          .transition()
          .duration(200)
          .attr("stroke-opacity", 0.3)
          .attr("stroke-width", (d: any) => Math.max(1, d.value / 2));
      });

    // Draw nodes
    g.append("g")
      .selectAll("rect")
      .data(data.nodes)
      .join("rect")
      .attr("x", (d: any) => d.x0)
      .attr("y", (d: any) => d.y0)
      .attr("width", (d: any) => d.x1 - d.x0)
      .attr("height", (d: any) => d.y1 - d.y0)
      .attr("fill", (d, i) => colors[i % colors.length])
      .attr("stroke", "#ffffff")
      .attr("stroke-width", 1)
      .attr("rx", 2)
      .style("cursor", "pointer")
      .on("mouseenter", function () {
        d3.select(this)
          .transition()
          .duration(200)
          .attr("opacity", 0.8)
          .attr("stroke-width", 2);
      })
      .on("mouseleave", function () {
        d3.select(this)
          .transition()
          .duration(200)
          .attr("opacity", 1)
          .attr("stroke-width", 1);
      });

    // Add labels
    g.append("g")
      .selectAll("text")
      .data(data.nodes)
      .join("text")
      .attr("x", (d: any) => (d.x0 < width / 2 ? d.x1 + 6 : d.x0 - 6))
      .attr("y", (d: any) => (d.y0 + d.y1) / 2)
      .attr("dy", "0.35em")
      .attr("text-anchor", (d: any) => (d.x0 < width / 2 ? "start" : "end"))
      .text((d: any) => d.name)
      .attr("font-size", "11px")
      .attr("font-family", "Inter, sans-serif")
      .attr("fill", "#374151")
      .style("pointer-events", "none");
  }, [colors]);

  return (
    <div className="relative h-full w-full">
      <svg ref={svgRef} width="100%" height="300" />
    </div>
  );
};
