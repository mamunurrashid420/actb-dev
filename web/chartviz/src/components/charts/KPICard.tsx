"use client";

import { useMemo } from "react";
import { BaseChartProps, HighlightType } from "@/lib/charts/registry";
import { getSentimentColor } from "@/lib/charts/style-guide";

interface KPICardProps extends BaseChartProps {
  format?: "number" | "currency" | "percentage";
}

export function KPICard({
  data,
  dataMapping,
  dataSeries,
  title,
  highlights = [],
  format = "number",
}: KPICardProps) {
  // Use dataMapping.value if available, otherwise find first non-row_id field
  const valueField = useMemo(() => {
    if (dataMapping?.value) return dataMapping.value;
    return data.rows[0] && Object.keys(data.rows[0]).find((k) => k !== "row_id");
  }, [dataMapping, data.rows]);

  const value = valueField ? data.rows[0][valueField] : 0;

  // Get sentiment color from dataSeries if available
  const sentimentColor = useMemo(() => {
    if (!dataSeries || dataSeries.length === 0) return undefined;
    const config = dataSeries.find((s) => s.field === valueField) || dataSeries[0];
    if (config.sentiment && config.sentiment !== "neutral") {
      return getSentimentColor(config.sentiment);
    }
    return undefined;
  }, [dataSeries, valueField]);

  // Check for trend in data (look for a trend field or second row)
  const trendField =
    data.rows[0] && Object.keys(data.rows[0]).find((k) => k.includes("trend"));
  const trendValue = trendField ? data.rows[0][trendField] : null;

  const formatValue = (val: number) => {
    switch (format) {
      case "currency":
        return new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: "USD",
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
        }).format(val);
      case "percentage":
        return `${val.toFixed(1)}%`;
      default:
        return new Intl.NumberFormat("en-US").format(val);
    }
  };

  const getTrendColor = () => {
    if (trendValue === null || trendValue === undefined) return "text-gray-500";
    return trendValue > 0
      ? "text-green-600"
      : trendValue < 0
        ? "text-red-600"
        : "text-gray-500";
  };

  const getTrendIcon = () => {
    if (trendValue === null || trendValue === undefined) return null;
    if (trendValue > 0) return "↑";
    if (trendValue < 0) return "↓";
    return "→";
  };

  return (
    <div className="kpi-card bg-card rounded-lg border p-6 shadow-sm">
      {title && (
        <h3 className="text-muted-foreground mb-2 text-sm font-medium">{title}</h3>
      )}
      <div className="flex items-baseline justify-between">
        <div
          className="text-foreground text-3xl font-bold"
          style={sentimentColor ? { color: sentimentColor } : undefined}
        >
          {formatValue(value)}
        </div>
        {trendValue !== null && trendValue !== undefined && (
          <div className={`text-sm font-medium ${getTrendColor()}`}>
            <span className="mr-1">{getTrendIcon()}</span>
            {Math.abs(trendValue).toFixed(1)}%
          </div>
        )}
      </div>
      {highlights.length > 0 && (
        <div className="text-muted-foreground mt-3 text-xs">
          {highlights.map((h, idx) => (
            <div key={idx}>{h.description || h.type}</div>
          ))}
        </div>
      )}
    </div>
  );
}
