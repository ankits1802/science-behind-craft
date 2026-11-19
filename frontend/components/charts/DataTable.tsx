import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type DataColumn = { key: string; label: string; numeric?: boolean };
export type DataRow = { key: string; cells: Record<string, ReactNode> };

export function DataTable({ caption, columns, rows, className }: { caption: string; columns: readonly DataColumn[]; rows: readonly DataRow[]; className?: string }) {
  return (
    <table className={cn("w-full border-collapse font-ui text-ui font-normal text-ink-1", className)} data-testid="data-table">
      <caption className="sr-only">{caption}</caption>
      <thead>
        <tr className="border-b border-ink-1">
          {columns.map((column) => (
            <th key={column.key} scope="col" className={cn("px-2 py-2 text-label text-ink-2", column.numeric ? "text-end" : "text-start")}>
              {column.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.key} className="border-b border-rule">
            {columns.map((column, at) =>
              at === 0 ? (
                <th key={column.key} scope="row" className="px-2 py-1.5 text-start font-normal">
                  {row.cells[column.key]}
                </th>
              ) : (
                <td key={column.key} className={cn("px-2 py-1.5", column.numeric ? "text-end [font-variant-numeric:lining-nums_tabular-nums]" : "text-start")}>
                  {row.cells[column.key]}
                </td>
              )
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
