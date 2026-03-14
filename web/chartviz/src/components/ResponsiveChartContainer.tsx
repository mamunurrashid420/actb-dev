"use client";

import { useRef, useState, useEffect } from "react";
import { createChart } from "@/lib/charts/factory";
import type { ChartSpec, ChartDataSlice } from "@/lib/charts/factory";
import type { Highlight } from "@/lib/charts/registry";

interface ResponsiveChartContainerProps {
  spec: ChartSpec;
  data: ChartDataSlice;
  highlights?: Highlight[];
  height?: number;
  minWidth?: number;
}

/**
 * A responsive container that measures its width and renders a chart
 * using the factory's createChart function.
 */
export function ResponsiveChartContainer({
  spec,
  data,
  highlights,
  height = 300,
  minWidth = 200,
}: ResponsiveChartContainerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState<number>(minWidth);

  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const width = entry.contentRect.width;
        if (width > 0) {
          setContainerWidth(Math.max(width, minWidth));
        }
      }
    });

    resizeObserver.observe(containerRef.current);

    // Set initial width
    const initialWidth = containerRef.current.offsetWidth;
    if (initialWidth > 0) {
      setContainerWidth(Math.max(initialWidth, minWidth));
    }

    return () => resizeObserver.disconnect();
  }, [minWidth]);

  return (
    <div ref={containerRef} className="w-full">
      {containerWidth > 0 &&
        createChart(spec, data, highlights, {
          width: containerWidth,
          height,
        })}
    </div>
  );
}
