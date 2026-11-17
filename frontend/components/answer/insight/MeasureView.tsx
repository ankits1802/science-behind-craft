"use client";

import { ArrowRight } from "lucide-react";

import { CitationChips } from "@/components/answer/CitationContext";
import { CitedText } from "@/components/answer/ProseBlockView";
import { DatasetCredit } from "@/components/DatasetCredit";
import type { MeasureBlock, MeasureRow } from "@/lib/explainerInsight";
import { basisText, factorText, measureDatasets, metricText } from "@/lib/insightView";

function Conversion({ row }: { row: MeasureRow }) {
  const conversion = row.conversion;
  return (
    <p className="text-xs leading-5 text-ink-500" data-testid="measure-basis" data-basis={conversion.basis}>
      <span className="font-semibold text-ink-700">{factorText(conversion)}</span>
      <span> · {basisText(conversion)}</span>
      {conversion.citation ? <CitationChips citations={[conversion.citation]} /> : null}
    </p>
  );
}

function MeasureRowView({ row }: { row: MeasureRow }) {
  return (
    <li className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2 rounded-lg border border-line-200 bg-card p-4" data-testid="measure-row">
      <p className="flex min-w-0 flex-wrap items-baseline gap-x-2.5 gap-y-1 font-display text-lg font-bold">
        <span className="min-w-0 break-words text-ink-900" data-testid="measure-stated">
          {row.stated}
        </span>
        <ArrowRight className="h-4 w-4 shrink-0 self-center text-ink-300" aria-hidden />
        <span className="sr-only">is</span>
        <span className="min-w-0 break-words tabular-nums text-purple-700 dark:text-purple-300" data-testid="measure-metric">
          {metricText(row)}
        </span>
      </p>
      <Conversion row={row} />
      <CitedText id={row.sentence.id} sentences={[row.sentence]} className="text-sm leading-7 text-ink-700" />
    </li>
  );
}

export function MeasureView({ block }: { block: MeasureBlock }) {
  const datasets = measureDatasets(block.rows);
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3" data-testid="measure">
      <ul className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3">
        {block.rows.map((row) => (
          <MeasureRowView key={`${row.sentence.id}-${row.stated}`} row={row} />
        ))}
      </ul>
      {datasets.length > 0 ? (
        <div className="grid min-w-0 gap-2 border-t border-line-200 pt-3">
          {datasets.map((dataset) => (
            <DatasetCredit key={dataset.code} dataset={dataset} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
