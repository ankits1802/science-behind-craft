"use client";

import { useRef, useState, type KeyboardEvent } from "react";

import { MONTH_GRID, StripLine } from "@/components/answer/place/StripLine";
import { DatasetCredit } from "@/components/DatasetCredit";
import type { MonthlyRain } from "@/lib/explainerPlace";
import type { RegionDataset } from "@/lib/regionContract";
import { MONTHS, monthReading, rainShares, wettestMonth } from "@/lib/seasonsView";
import { cn } from "@/lib/utils";

const STEP: Record<string, number> = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };

function shifted(month: number, by: number): number {
  return ((month - 1 + by + MONTHS.length) % MONTHS.length) + 1;
}

export function RainfallBars({ rain }: { rain: MonthlyRain }) {
  const wettest = wettestMonth(rain);
  const [active, setActive] = useState(wettest);
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  const shares = rainShares(rain);

  const move = (event: KeyboardEvent<HTMLButtonElement>, month: number) => {
    const by = STEP[event.key];
    if (by === undefined) return;
    event.preventDefault();
    const next = shifted(month, by);
    setActive(next);
    buttons.current[next - 1]?.focus();
  };

  return (
    <div className="min-w-0" data-testid="rainfall-bars">
      <StripLine label={<span className="text-xs font-semibold text-ink-500">Rainfall</span>}>
        <p className="mb-1.5 text-xs font-semibold tabular-nums text-ink-900" data-testid="rainfall-reading">
          {active === wettest ? <span className="font-normal text-ink-500">Wettest · </span> : null}
          {monthReading(rain, active)}
        </p>
        <div role="group" aria-label="Monthly rainfall" className={cn(MONTH_GRID, "h-20 items-end border-b border-line-200")}>
          {MONTHS.map((month) => (
            <button
              key={month}
              ref={(node) => {
                buttons.current[month - 1] = node;
              }}
              type="button"
              tabIndex={month === active ? 0 : -1}
              aria-label={monthReading(rain, month)}
              onPointerEnter={() => setActive(month)}
              onFocus={() => setActive(month)}
              onClick={() => setActive(month)}
              onKeyDown={(event) => move(event, month)}
              className="flex h-full min-w-0 items-end rounded-t-[4px]"
              data-month={month}
            >
              <span
                className={cn("w-full rounded-t-[4px] transition-colors", month === active ? "bg-errand-600 dark:bg-errand-300" : "bg-errand-300 dark:bg-errand-700")}
                style={{ height: `${(shares[month - 1] * 100).toFixed(2)}%` }}
              />
            </button>
          ))}
        </div>
      </StripLine>
    </div>
  );
}

export function RainfallCredit({ rain, dataset }: { rain: MonthlyRain; dataset: RegionDataset | null }) {
  return (
    <StripLine label={null} className="border-t border-line-200 pt-3">
      <p className="text-[11px] leading-4 text-ink-500" data-testid="rainfall-credit">
        Rainfall · {rain.district.name}, {rain.district.stateName} · monthly normal · {rain.period}
      </p>
      {dataset ? <DatasetCredit dataset={dataset} /> : null}
    </StripLine>
  );
}
