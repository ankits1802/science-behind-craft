"use client";

import { ChemEquation } from "@/components/answer/ChemEquation";
import { CitationChips } from "@/components/answer/CitationContext";
import { DatasetCredit } from "@/components/DatasetCredit";
import type { SimulationReaction, SimulationValue } from "@/lib/explainerPlay";
import { simulationValueText, wordEquation, type ValueBasis } from "@/lib/simulationView";
import type { Citation } from "@/lib/types";

const ROW = "grid min-w-0 grid-cols-[minmax(0,1fr)] gap-1 rounded-md border border-line-200 bg-surface-50 px-3 py-2";

function ValueRow({ value, basis }: { value: SimulationValue; basis: ValueBasis }) {
  return (
    <li className={ROW} data-testid="generated-value" data-key={value.key}>
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

function ReactionRow({ reaction }: { reaction: SimulationReaction }) {
  return (
    <li className={ROW} data-testid="generated-reaction" data-reaction={reaction.reactionId}>
      <span className="min-w-0 break-words text-sm text-ink-700">{reaction.label}</span>
      {reaction.equation ? (
        <ChemEquation equation={reaction.equation} display={false} className="text-sm" />
      ) : (
        <span className="min-w-0 break-words text-sm text-ink-900">{wordEquation(reaction)}</span>
      )}
      <CitationChips citations={reaction.citations} />
    </li>
  );
}

function GroundRow({ citation }: { citation: Citation }) {
  return (
    <li className={ROW} data-testid="generated-ground">
      <span className="min-w-0 break-words text-xs leading-5 text-ink-500">
        {citation.quote ? <q>{citation.quote}</q> : null}
        <CitationChips citations={[citation]} />
      </span>
    </li>
  );
}

export function GeneratedSources({
  values,
  bases,
  grounds = [],
  reactions = []
}: {
  values: readonly SimulationValue[];
  bases: readonly ValueBasis[];
  grounds?: readonly Citation[];
  reactions?: readonly SimulationReaction[];
}) {
  return (
    <section aria-label="Built from" className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2" data-testid="generated-sources">
      <h4 className="field-label">Built from</h4>
      <ul className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2">
        {reactions.map((reaction) => (
          <ReactionRow key={reaction.reactionId} reaction={reaction} />
        ))}
        {values.map((value, index) => (
          <ValueRow key={value.key} value={value} basis={bases[index]} />
        ))}
        {grounds.map((citation) => (
          <GroundRow key={citation.id} citation={citation} />
        ))}
      </ul>
    </section>
  );
}
