import type { ReactNode } from "react";

import { MONTHS, monthInitial } from "@/lib/seasonsView";
import { cn } from "@/lib/utils";

export const MONTH_GRID = "grid grid-cols-[repeat(12,minmax(0,1fr))] gap-0.5";

export function StripLine({ label, children, className }: { label: ReactNode; children: ReactNode; className?: string }) {
  return (
    <div className={cn("grid min-w-0 grid-cols-[minmax(0,1fr)] gap-1.5 sm:grid-cols-[minmax(0,9rem)_minmax(0,1fr)] sm:items-center sm:gap-4", className)}>
      {label ?? <span aria-hidden className="max-sm:hidden" />}
      <div className="min-w-0">{children}</div>
    </div>
  );
}

export function MonthHeader() {
  return (
    <StripLine label={null}>
      <div aria-hidden className={cn(MONTH_GRID, "text-center text-[11px] font-semibold text-ink-500")} data-testid="month-header">
        {MONTHS.map((month) => (
          <span key={month}>{monthInitial(month)}</span>
        ))}
      </div>
    </StripLine>
  );
}
