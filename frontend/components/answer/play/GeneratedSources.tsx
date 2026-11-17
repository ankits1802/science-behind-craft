"use client";

import { CitationChips } from "@/components/answer/CitationContext";
import { DatasetCredit } from "@/components/DatasetCredit";
import type { SimulationValue } from "@/lib/explainerPlay";
import { simulationValueText, type ValueBasis } from "@/lib/simulationView";

function ValueRow({ value, basis }: { value: SimulationValue; basis: ValueBasis }) {
  return (
    <li className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-1 rounded-md border border-line-200 bg-surface-50 px-3 py-2" data-testid="generated-value" data-key={value.key}>
      <span className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
        <span className="min-w-0 break-words text-sm text-ink-700">{value.label}</span>
        <span className="text-sm font-semibold tabular-nums text-ink-900">{simulationValueText(value)}</span>
      </span>
      {basis.kind === "stated" ? (
        <span className="min-w-0 break-words text-xs leading-5 text-ink-500" data-testid="generated-value-stated">
          <q>{basis.stated}</q>
          <CitationChips citations={value.citations} />
        </span>
      ) : (
        <DatasetCredit dataset={basis.dataset} />
      )}
    </li>
  );
}

export function GeneratedSources({ values, bases }: { values: readonly SimulationValue[]; bases: readonly ValueBasis[] }) {
  return (
    <section aria-label="Built from" className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2" data-testid="generated-sources">
      <h4 className="field-label">Built from</h4>
      <ul className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2">
        {values.map((value, index) => (
          <ValueRow key={value.key} value={value} basis={bases[index]} />
        ))}
      </ul>
    </section>
  );
}
