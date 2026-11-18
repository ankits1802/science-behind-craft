"use client";

import { ChemEquation } from "@/components/answer/ChemEquation";
import { CitationChips } from "@/components/answer/CitationContext";
import { EvidenceLevelBadge, EvidenceSignalBadge } from "@/components/answer/EvidenceBadge";
import { StepColours } from "@/components/answer/matter/StepColours";
import { CitedText } from "@/components/answer/ProseBlockView";
import { SpeciesRow } from "@/components/answer/SpeciesRow";
import type { ExplainerSentence } from "@/lib/explainerBlockBase";
import type { ReactionStep } from "@/lib/explainerMatter";
import { reactionSpoken, speciesNamesLine } from "@/lib/processView";
import { stepSignal } from "@/lib/reactionPlayer";

function StepConditions({ step }: { step: ReactionStep }) {
  const conditions = step.conditions ?? [];
  if (conditions.length === 0) return null;
  return (
    <ul className="grid gap-1 text-xs text-ink-700" aria-label="Conditions">
      {conditions.map((condition, index) => (
        <li key={`${condition.label}:${index}`} data-testid="step-condition">
          <span className="font-semibold text-ink-900">{condition.label}</span>
          <span>: {condition.stated}</span>
          <CitationChips citations={condition.citations} />
        </li>
      ))}
    </ul>
  );
}

function StepWhy({ id, notes }: { id: string; notes: readonly ExplainerSentence[] }) {
  if (notes.length === 0) return null;
  return (
    <div className="min-w-0" data-testid="step-why">
      <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">What happens and why</p>
      <CitedText id={id} sentences={notes} className="mt-1 text-sm leading-7 text-ink-700" />
    </div>
  );
}

export function StepDetail({ step, notes, animate }: { step: ReactionStep; notes: readonly ExplainerSentence[]; animate: boolean }) {
  const signal = stepSignal(step);
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2.5 px-3 pb-3 sm:pl-[3.25rem]" data-testid="reaction-step-detail">
      <span className="flex flex-wrap items-center gap-1.5">
        {signal ? <EvidenceSignalBadge signal={signal} /> : null}
        <EvidenceLevelBadge level={step.level} />
      </span>
      {step.equation ? (
        <>
          <ChemEquation equation={step.equation} label={reactionSpoken(step)} className="text-base" />
          <p className="text-xs text-ink-500">{speciesNamesLine(step)}</p>
        </>
      ) : (
        <SpeciesRow reaction={step} />
      )}
      <StepColours step={step} animate={animate} />
      <StepConditions step={step} />
      <StepWhy id={`${step.reactionId}.why`} notes={notes} />
      <p className="text-xs">
        <CitationChips citations={step.citations} />
      </p>
    </div>
  );
}
