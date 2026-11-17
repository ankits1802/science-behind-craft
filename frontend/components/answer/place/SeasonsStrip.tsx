"use client";

import { RainfallBars, RainfallCredit } from "@/components/answer/place/RainfallBars";
import { MONTH_GRID, MonthHeader, StripLine } from "@/components/answer/place/StripLine";
import { CitedText } from "@/components/answer/ProseBlockView";
import type { Season, SeasonRow, SeasonsBlock } from "@/lib/explainerPlace";
import { datasetRow } from "@/lib/placeView";
import { MONTHS, monthsText, SEASON_LABEL } from "@/lib/seasonsView";
import { cn } from "@/lib/utils";

function SeasonChip({ season }: { season: Season }) {
  return (
    <span className="inline-flex h-6 w-fit items-center rounded-full border border-purple-200 bg-purple-50 px-2.5 text-xs font-semibold text-purple-800 dark:border-purple-800 dark:bg-purple-950/50 dark:text-purple-200" data-testid="season-chip">
      {SEASON_LABEL[season]}
    </span>
  );
}

function MonthCells({ months }: { months: readonly number[] }) {
  const named = new Set(months);
  return (
    <>
      <div aria-hidden className={MONTH_GRID} data-testid="month-cells">
        {MONTHS.map((month) => (
          <span key={month} data-on={named.has(month) ? "true" : "false"} className={cn("h-3 rounded-[4px]", named.has(month) ? "bg-purple-600 dark:bg-purple-400" : "bg-field-100")} />
        ))}
      </div>
      <span className="sr-only">{monthsText(months)}</span>
    </>
  );
}

function RowLabel({ row }: { row: SeasonRow }) {
  return (
    <div className="flex min-w-0 flex-wrap items-center gap-2">
      <span className="min-w-0 break-words text-sm font-semibold text-ink-900">{row.label}</span>
      {row.season && row.months.length > 0 ? <SeasonChip season={row.season} /> : null}
    </div>
  );
}

function SeasonRowView({ row }: { row: SeasonRow }) {
  return (
    <li className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-1.5" data-testid="season-row">
      <StripLine label={<RowLabel row={row} />}>
        {row.months.length > 0 ? <MonthCells months={row.months} /> : row.season ? <SeasonChip season={row.season} /> : null}
      </StripLine>
      <StripLine label={null}>
        <CitedText id={row.sentence.id} sentences={[row.sentence]} className="text-sm leading-7 text-ink-700" />
      </StripLine>
    </li>
  );
}

export function SeasonsStrip({ block }: { block: SeasonsBlock }) {
  const rain = block.rainfall;
  const monthly = rain !== null || block.rows.some((row) => row.months.length > 0);
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3" data-testid="seasons-strip">
      {rain ? <RainfallBars rain={rain} /> : null}
      {monthly ? <MonthHeader /> : null}
      <ol className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-4">
        {block.rows.map((row) => (
          <SeasonRowView key={row.sentence.id} row={row} />
        ))}
      </ol>
      {rain ? <RainfallCredit rain={rain} dataset={datasetRow(block.datasets, rain.datasetCode)} /> : null}
    </div>
  );
}
