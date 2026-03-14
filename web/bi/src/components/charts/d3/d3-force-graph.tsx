"use client";

import React, { useEffect, useRef, useState } from "react";
import * as d3 from "d3";

interface D3ForceGraphProps {
  colors: readonly string[];
}

interface Node extends d3.SimulationNodeDatum {
  id: string;
  group: number;
}

interface Link extends d3.SimulationLinkDatum<Node> {
  source: string | Node;
  target: string | Node;
  value: number;
}

export const D3ForceGraph: React.FC<D3ForceGraphProps> = ({ colors }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const width = svgRef.current.clientWidth;
    const height = 300;

    // Sample network data
    const nodes: Node[] = [
      { id: "A", group: 1 },
      { id: "B", group: 1 },
      { id: "C", group: 2 },
      { id: "D", group: 2 },
      { id: "E", group: 3 },
      { id: "F", group: 3 },
      { id: "G", group: 1 },
      { id: "H", group: 2 },
    ];

    const links: Link[] = [
      { source: "A", target: "B", value: 1 },
      { source: "A", target: "C", value: 2 },
      { source: "B", target: "D", value: 1 },
      { source: "C", target: "E", value: 3 },
      { source: "D", target: "F", value: 2 },
      { source: "E", target: "G", value: 1 },
      { source: "F", target: "H", value: 2 },
      { source: "G", target: "H", value: 1 },
    ];

    // Create force simulation
    const simulation = d3
      .forceSimulation(nodes)
      .force(
        "link",
        d3
          .forceLink<Node, Link>(links)
          .id((d) => d.id)
          .distance(80),
      )
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(30));

    // Create links
    const link = svg
      .append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", colors[3])
      .attr("stroke-opacity", 0.3)
      .attr("stroke-width", (d) => Math.sqrt(d.value) * 2)
      .style("transition", "all 0.3s ease");

    // Create nodes
    const node = svg
      .append("g")
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", 12)
      .attr("fill", (d) => colors[d.group - 1])
      .attr("stroke", "#ffffff")
      .attr("stroke-width", 2)
      .style("cursor", "pointer")
      .style("transition", "all 0.3s ease")
      .call(
        d3
          .drag<SVGCircleElement, Node>()
          .on("start", dragstarted)
          .on("drag", dragged)
          .on("end", dragended) as any,
      );

    // Add labels
    const label = svg
      .append("g")
      .selectAll("text")
      .data(nodes)
      .join("text")
      .text((d) => d.id)
      .attr("font-size", "11px")
      .attr("font-family", "Inter, sans-serif")
      .attr("fill", "#374151")
      .attr("text-anchor", "middle")
      .attr("dy", 4)
      .style("pointer-events", "none")
      .style("user-select", "none");

    // Hover interactions
    node
      .on("mouseenter", function (event, d) {
        setSelectedNode(d.id);
        d3.select(this)
          .transition()
          .duration(200)
          .attr("r", 16)
          .attr("stroke-width", 3);

        // Highlight connected links
        link
          .transition()
          .duration(200)
          .attr("stroke-opacity", (l) => {
            const source = typeof l.source === "object" ? l.source.id : l.source;
            const target = typeof l.target === "object" ? l.target.id : l.target;
            return source === d.id || target === d.id ? 0.8 : 0.1;
          })
          .attr("stroke-width", (l) => {
            const source = typeof l.source === "object" ? l.source.id : l.source;
            const target = typeof l.target === "object" ? l.target.id : l.target;
            return source === d.id || target === d.id
              ? Math.sqrt(l.value) * 3
              : Math.sqrt(l.value) * 2;
          });
      })
      .on("mouseleave", function () {
        setSelectedNode(null);
        d3.select(this)
          .transition()
          .duration(200)
          .attr("r", 12)
          .attr("stroke-width", 2);

        link
          .transition()
          .duration(200)
          .attr("stroke-opacity", 0.3)
          .attr("stroke-width", (d) => Math.sqrt(d.value) * 2);
      });

    // Update positions on tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as Node).x || 0)
        .attr("y1", (d) => (d.source as Node).y || 0)
        .attr("x2", (d) => (d.target as Node).x || 0)
        .attr("y2", (d) => (d.target as Node).y || 0);

      node.attr("cx", (d) => d.x || 0).attr("cy", (d) => d.y || 0);

      label.attr("x", (d) => d.x || 0).attr("y", (d) => d.y || 0);
    });

    function dragstarted(event: d3.D3DragEvent<SVGCircleElement, Node, Node>) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event: d3.D3DragEvent<SVGCircleElement, Node, Node>) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event: d3.D3DragEvent<SVGCircleElement, Node, Node>) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    return () => {
      simulation.stop();
    };
  }, [colors]);

  return (
    <div className="relative h-full w-full">
      <svg ref={svgRef} width="100%" height="300" />
      {selectedNode && (
        <div className="absolute right-2 top-2 rounded-md bg-white/90 px-3 py-1.5 text-xs font-medium text-gray-700 shadow-sm backdrop-blur-sm dark:bg-gray-800/90 dark:text-gray-200">
          Node: {selectedNode}
        </div>
      )}
    </div>
  );
};
