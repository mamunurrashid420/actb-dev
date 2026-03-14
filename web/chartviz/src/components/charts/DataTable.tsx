"use client";

import { useState, useMemo } from "react";
import {
  BaseChartProps,
  HIGHLIGHT_COLORS_LIGHT,
  HighlightType,
} from "@/lib/charts/registry";

interface DataTableProps extends BaseChartProps {
  columns?: Array<{
    field: string;
    header: string;
    width?: number;
    align?: "left" | "center" | "right";
  }>;
  sortable?: boolean;
  paginated?: boolean;
  pageSize?: number;
}

export function DataTable({
  data,
  dimensions,
  dataMapping,
  dataSeries,
  title,
  highlights = [],
  columns,
  sortable = true,
  paginated = true,
  pageSize = 10,
}: DataTableProps) {
  // Note: dataMapping and dataSeries are available for future use
  // (e.g., column-level styling based on semantic metadata)
  void dataMapping;
  void dataSeries;
  const [sortField, setSortField] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [currentPage, setCurrentPage] = useState(1);

  // Auto-generate columns from dimensions if not provided
  const tableColumns = useMemo((): Array<{
    field: string;
    header: string;
    width?: number;
    align?: "left" | "center" | "right";
  }> => {
    if (columns) return columns;

    return dimensions.map((dim) => ({
      field: dim.field,
      header: dim.field.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
      align: dim.type === "numeric" ? ("right" as const) : ("left" as const),
    }));
  }, [columns, dimensions]);

  // Sort data
  const sortedData = useMemo(() => {
    if (!sortField) return data.rows;

    return [...data.rows].sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];

      if (aVal < bVal) return sortDirection === "asc" ? -1 : 1;
      if (aVal > bVal) return sortDirection === "asc" ? 1 : -1;
      return 0;
    });
  }, [data.rows, sortField, sortDirection]);

  // Paginate data
  const paginatedData = useMemo(() => {
    if (!paginated) return sortedData;

    const startIdx = (currentPage - 1) * pageSize;
    return sortedData.slice(startIdx, startIdx + pageSize);
  }, [sortedData, currentPage, pageSize, paginated]);

  const totalPages = Math.ceil(sortedData.length / pageSize);

  const handleSort = (field: string) => {
    if (!sortable) return;

    if (sortField === field) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  // Get highlight info for a row
  const getHighlightInfo = (rowId: string) => {
    const highlight = highlights.find(
      (h) =>
        (h.type === HighlightType.ROW || h.type === HighlightType.POINT_SET) &&
        h.rowIds?.includes(rowId),
    );

    if (!highlight) return null;

    const uniqueInsightIds = [...new Set(highlights.map((h) => h.insightId))];
    const colorIndex = uniqueInsightIds.indexOf(highlight.insightId);
    const backgroundColor =
      HIGHLIGHT_COLORS_LIGHT[colorIndex % HIGHLIGHT_COLORS_LIGHT.length];

    return { backgroundColor, insightId: highlight.insightId };
  };

  return (
    <div className="data-table bg-card overflow-hidden rounded-lg border shadow-sm">
      {title && (
        <div className="border-b px-6 py-4">
          <h3 className="text-foreground text-lg font-semibold">{title}</h3>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="divide-border min-w-full divide-y">
          <thead className="bg-muted/50">
            <tr>
              {tableColumns.map((col) => (
                <th
                  key={col.field}
                  className={`text-muted-foreground px-6 py-3 text-xs font-medium uppercase tracking-wider ${
                    sortable ? "hover:bg-muted cursor-pointer" : ""
                  }`}
                  style={{
                    textAlign: col.align || "left",
                    width: col.width,
                  }}
                  onClick={() => handleSort(col.field)}
                >
                  <div className="flex items-center gap-2">
                    {col.header}
                    {sortable && sortField === col.field && (
                      <span>{sortDirection === "asc" ? "↑" : "↓"}</span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-card divide-border divide-y">
            {paginatedData.map((row, idx) => {
              const highlightInfo = getHighlightInfo(row.row_id);

              return (
                <tr
                  key={row.row_id || idx}
                  style={
                    highlightInfo
                      ? { backgroundColor: highlightInfo.backgroundColor }
                      : {}
                  }
                  className="hover:bg-muted/30"
                >
                  {tableColumns.map((col) => (
                    <td
                      key={col.field}
                      className="text-foreground whitespace-nowrap px-6 py-4 text-sm"
                      style={{ textAlign: col.align || "left" }}
                    >
                      {row[col.field]}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {paginated && totalPages > 1 && (
        <div className="flex items-center justify-between border-t px-6 py-4">
          <div className="text-muted-foreground text-sm">
            Showing {(currentPage - 1) * pageSize + 1} to{" "}
            {Math.min(currentPage * pageSize, sortedData.length)} of {sortedData.length}{" "}
            results
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="hover:bg-muted rounded border px-3 py-1 text-sm disabled:opacity-50"
            >
              Previous
            </button>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="hover:bg-muted rounded border px-3 py-1 text-sm disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
