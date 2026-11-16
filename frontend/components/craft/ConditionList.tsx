"use client";

import { EvidenceLevelBadge, EvidenceSignalBadge } from "@/components/answer/EvidenceBadge";
import { CitationChips } from "@/components/craft/CitationContext";
import { QUANTITY_LABEL, readingClaim, readingRange } from "@/lib/processView";
import type { ConditionReading, StageCondition } from "@/lib/scienceContract";

export function ConditionList({ conditions }: { conditions: readonly StageCondition[] }) {
  return (
    <ul className="grid gap-2">
      {conditions.map((condition) => (
        <li key={condition.id} className="rounded-md border border-line-200 bg-surface-50 px-3 py-2.5" data-testid="process-condition">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="text-sm font-medium text-ink-900">{condition.label}</span>
            <span className="text-xs text-ink-500">{QUANTITY_LABEL[condition.quantity]}</span>
            <span className="ml-auto flex flex-wrap items-center gap-1.5">
              {condition.sourcesDiffer ? <EvidenceSignalBadge signal="SOURCES_DIFFER" /> : null}
              <EvidenceLevelBadge level={condition.level} />
            </span>
          </div>
          <ul className="mt-1.5 grid gap-1">
            {condition.readings.map((reading, index) => (
              <ReadingLine key={`${reading.claimId}:${index}`} condition={condition} reading={reading} />
            ))}
          </ul>
        </li>
      ))}
    </ul>
  );
}

function ReadingLine({ condition, reading }: { condition: StageCondition; reading: ConditionReading }) {
  const range = readingRange(condition, reading);
  return (
    <li className="text-sm leading-6 text-ink-700">
      <span>{reading.stated}</span>
      {range ? <span className="ml-1.5 text-xs tabular-nums text-ink-500">{range}</span> : null}
      {reading.envelope.status === "OUTSIDE" ? <EvidenceSignalBadge signal="OUTSIDE_RANGE" className="ml-1.5 align-middle" /> : null}
      <CitationChips citations={readingClaim(condition, reading).citations} />
    </li>
  );
}
