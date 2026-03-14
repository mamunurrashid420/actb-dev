"use client";

import React, { useEffect, useRef } from "react";
import * as d3 from "d3";

interface D3CandlestickProps {
  colors: readonly string[];
  showGrid?: boolean;
}

interface CandlestickData {
  date: Date;
  open: number;
  high: number;
  low: number;
  close: number;
}

export const D3Candlestick: React.FC<D3CandlestickProps> = ({
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

    // Sample candlestick data
    const data: CandlestickData[] = [
      { date: new Date(2024, 0, 1), open: 51, high: 53, low: 50, close: 52 },
      { date: new Date(2024, 0, 2), open: 52, high: 55, low: 51, close: 54 },
      { date: new Date(2024, 0, 3), open: 54, high: 56, low: 53, close: 55 },
      { date: new Date(2024, 0, 4), open: 55, high: 57, low: 54, close: 56 },
      { date: new Date(2024, 0, 5), open: 56, high: 58, low: 55, close: 57 },
      { date: new Date(2024, 0, 8), open: 57, high: 59, low: 56, close: 58 },
      { date: new Date(2024, 0, 9), open: 58, high: 60, low: 57, close: 59 },
      { date: new Date(2024, 0, 10), open: 59, high: 61, low: 58, close: 60 },
      { date: new Date(2024, 0, 11), open: 60, high: 62, low: 59, close: 61 },
      { date: new Date(2024, 0, 12), open: 61, high: 62, low: 57, close: 58 },
    ];

    // Scales
    const x = d3
      .scaleBand()
      .domain(data.map((d) => d.date.toLocaleDateString()))
      .range([0, width])
      .padding(0.3);

    const y = d3
      .scaleLinear()
      .domain([d3.min(data, (d) => d.low) || 0, d3.max(data, (d) => d.high) || 100])
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

    const candleWidth = x.bandwidth();

    // Draw candlesticks
    data.forEach((d, i) => {
      const center = (x(d.date.toLocaleDateString()) || 0) + candleWidth / 2;
      const isGreen = d.close >= d.open;
      const color = isGreen ? colors[1] || "#10b981" : colors[0] || "#ef4444";

      const candleG = g.append("g").attr("class", `candle-${i}`);

      // High-Low line (wick)
      candleG
        .append("line")
        .attr("x1", center)
        .attr("x2", center)
        .attr("y1", y(d.high))
        .attr("y2", y(d.low))
        .attr("stroke", color)
        .attr("stroke-width", 1.5)
        .style("opacity", 0)
        .transition()
        .delay(i * 50)
        .duration(400)
        .style("opacity", 1);

      // Open-Close body
      const bodyHeight = Math.abs(y(d.open) - y(d.close));
      const bodyY = Math.min(y(d.open), y(d.close));

      const body = candleG
        .append("rect")
        .attr("x", center - candleWidth / 3)
        .attr("y", bodyY)
        .attr("width", (candleWidth * 2) / 3)
        .attr("height", 0)
        .attr("fill", color)
        .attr("stroke", color)
        .attr("stroke-width", 1)
        .attr("rx", 1)
        .style("cursor", "pointer");

      body
        .transition()
        .delay(i * 50)
        .duration(400)
        .attr("height", bodyHeight || 1);

      body
        .on("mouseenter", function () {
          d3.select(this)
            .transition()
            .duration(200)
            .attr("fill-opacity", 0.8)
            .attr("stroke-width", 2);
        })
        .on("mouseleave", function () {
          d3.select(this)
            .transition()
            .duration(200)
            .attr("fill-opacity", 1)
            .attr("stroke-width", 1);
        });
    });

    // Axes
    const xAxis = g
      .append("g")
      .attr("transform", `translate(0,${height})`)
      .call(d3.axisBottom(x));

    xAxis
      .selectAll("text")
      .style("font-size", "10px")
      .style("font-family", "Inter, sans-serif")
      .style("fill", "#6b7280")
      .attr("transform", "rotate(-45)")
      .style("text-anchor", "end");

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
