"use client";

import { useEffect, useRef, useMemo } from "react";
import * as d3 from "d3";
import {
  BaseChartProps,
  createInsightColorMap,
  getHighlightColor,
  HighlightType,
} from "@/lib/charts/registry";
import {
  getSentimentColor,
  getProminenceOpacity,
  getProminenceStrokeWidth,
  getStrokeDashArray,
} from "@/lib/charts/style-guide";

interface LineChartProps extends BaseChartProps {
  curve?: "linear" | "monotone" | "step" | "cardinal";
  showDots?: boolean;
  strokeWidth?: number;
  showArea?: boolean;
}

export function LineChart({
  data,
  dimensions,
  dataMapping,
  dataSeries,
  title,
  width = 600,
  height = 400,
  highlights = [],
  curve = "monotone",
  showDots = true,
  strokeWidth = 2,
  showArea = false,
}: LineChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const axesRef = useRef<SVGGElement>(null);

  // Use dataMapping if available, otherwise fall back to dimension scanning
  const xField = useMemo(
    () =>
      dataMapping?.xAxis ||
      dimensions.find((d) => d.type === "time" || d.type === "category")?.field,
    [dataMapping, dimensions],
  );
  const yField = useMemo(
    () => dataMapping?.yAxis || dimensions.find((d) => d.type === "numeric")?.field,
    [dataMapping, dimensions],
  );
  const isTimeSeries = useMemo(
    () => dimensions.find((d) => d.field === xField)?.type === "time",
    [dimensions, xField],
  );

  // Get series classification for styling
  const seriesConfig = useMemo(() => {
    if (!dataSeries || dataSeries.length === 0) {
      return {
        color: "#4F46E5",
        opacity: 1,
        strokeWidth: strokeWidth,
        dashArray: "none",
      };
    }
    // Find the series config matching yField
    const config = dataSeries.find((s) => s.field === yField) || dataSeries[0];
    return {
      color: getSentimentColor(config.sentiment),
      opacity: getProminenceOpacity(config.prominence),
      strokeWidth: getProminenceStrokeWidth(config.prominence, strokeWidth),
      dashArray: getStrokeDashArray(config.purpose),
    };
  }, [dataSeries, yField, strokeWidth]);

  // Set up margins and dimensions
  const margin = { top: 40, right: 30, bottom: 60, left: 60 };
  const boundsWidth = width - margin.left - margin.right;
  const boundsHeight = height - margin.top - margin.bottom;

  const processedData = useMemo(() => {
    if (!xField) return [];
    // Parse dates if time dimension
    const parseTime = d3.timeParse("%Y-%m-%d");
    return data.rows.map((d) => ({
      ...d,
      [xField]: isTimeSeries ? parseTime(d[xField]) : d[xField],
    }));
  }, [data.rows, xField, isTimeSeries]);

  // X scale
  const xScale = useMemo(() => {
    if (!xField || !processedData.length) return null;

    if (isTimeSeries) {
      const [minDate, maxDate] = d3.extent(processedData, (d) => d[xField]) as [
        Date,
        Date,
      ];
      return d3.scaleTime().domain([minDate, maxDate]).range([0, boundsWidth]);
    }

    return d3
      .scalePoint()
      .domain(processedData.map((d) => d[xField]))
      .range([0, boundsWidth])
      .padding(0.5);
  }, [processedData, xField, isTimeSeries, boundsWidth]);

  // Y scale
  const yScale = useMemo(() => {
    if (!yField || !processedData.length) return null;

    const max = d3.max(processedData, (d) => d[yField]) || 0;
    return d3.scaleLinear().domain([0, max]).nice().range([boundsHeight, 0]);
  }, [processedData, yField, boundsHeight]);

  // Render axes with D3
  useEffect(() => {
    if (!axesRef.current || !xScale || !yScale) return;

    const svgElement = d3.select(axesRef.current);
    svgElement.selectAll("*").remove();

    // X axis
    const xAxisGenerator = isTimeSeries
      ? d3.axisBottom(xScale as d3.ScaleTime<number, number>).ticks(6)
      : d3.axisBottom(xScale as d3.ScalePoint<string>);

    svgElement
      .append("g")
      .attr("transform", `translate(0,${boundsHeight})`)
      .call(xAxisGenerator)
      .selectAll("text")
      .attr("transform", "rotate(-45)")
      .style("text-anchor", "end");

    // Y axis
    const yAxisGenerator = d3.axisLeft(yScale);
    svgElement.append("g").call(yAxisGenerator);
  }, [xScale, yScale, boundsHeight, isTimeSeries]);

  if (!xField || !yField || !xScale || !yScale || !processedData.length) {
    return <svg ref={svgRef} width={width} height={height} />;
  }

  // Curve functions
  const curveMap = {
    linear: d3.curveLinear,
    monotone: d3.curveMonotoneX,
    step: d3.curveStep,
    cardinal: d3.curveCardinal,
  };

  // Build line path
  const lineBuilder = d3
    .line<any>()
    .x((d) => (xScale as any)(d[xField]))
    .y((d) => yScale(d[yField]))
    .curve(curveMap[curve]);

  const linePath = lineBuilder(processedData);

  // Build area path if enabled
  const areaBuilder = d3
    .area<any>()
    .x((d) => (xScale as any)(d[xField]))
    .y0(boundsHeight)
    .y1((d) => yScale(d[yField]))
    .curve(curveMap[curve]);

  const areaPath = showArea ? areaBuilder(processedData) : null;

  // Highlight processing
  const insightColorMap = createInsightColorMap(highlights);
  const highlightedRowIds = new Set(
    highlights
      .filter((h) => h.type === HighlightType.POINT_SET && h.rowIds)
      .flatMap((h) => h.rowIds || []),
  );

  return (
    <svg ref={svgRef} width={width} height={height}>
      {title && (
        <text
          x={width / 2}
          y={20}
          textAnchor="middle"
          style={{ fontSize: "16px", fontWeight: "bold", fill: "currentColor" }}
        >
          {title}
        </text>
      )}
      <g transform={`translate(${margin.left},${margin.top})`}>
        {/* Area fill */}
        {areaPath && (
          <path
            d={areaPath}
            fill={seriesConfig.color}
            opacity={seriesConfig.opacity * 0.2}
          />
        )}
        {/* Line */}
        {linePath && (
          <path
            d={linePath}
            fill="none"
            stroke={seriesConfig.color}
            strokeWidth={seriesConfig.strokeWidth}
            strokeDasharray={seriesConfig.dashArray}
            opacity={seriesConfig.opacity}
            data-prominence={dataSeries?.[0]?.prominence}
            data-purpose={dataSeries?.[0]?.purpose}
            data-sentiment={dataSeries?.[0]?.sentiment}
          />
        )}
        {/* Dots */}
        {showDots &&
          processedData.map((d, i) => {
            const isHighlighted = d.row_id && highlightedRowIds.has(d.row_id);
            const highlight = isHighlighted
              ? highlights.find((h) => h.rowIds?.includes(d.row_id))
              : null;
            const dotColor = highlight
              ? getHighlightColor(highlight.insightId, insightColorMap)
              : seriesConfig.color;

            return (
              <circle
                key={i}
                cx={(xScale as any)(d[xField])}
                cy={yScale(d[yField])}
                r={isHighlighted ? 6 : 4}
                fill={dotColor}
                stroke="white"
                strokeWidth={2}
                opacity={seriesConfig.opacity}
              />
            );
          })}
        {/* Threshold lines from highlights */}
        {highlights
          .filter(
            (h) => h.type === HighlightType.THRESHOLD && h.thresholdValue !== undefined,
          )
          .map((h, i) => (
            <line
              key={`threshold-${i}`}
              x1={0}
              x2={boundsWidth}
              y1={yScale(h.thresholdValue!)}
              y2={yScale(h.thresholdValue!)}
              stroke={getHighlightColor(h.insightId, insightColorMap)}
              strokeWidth={2}
              strokeDasharray="5,5"
            />
          ))}
      </g>
      {/* Axes group */}
      <g ref={axesRef} transform={`translate(${margin.left},${margin.top})`} />
    </svg>
  );
}
