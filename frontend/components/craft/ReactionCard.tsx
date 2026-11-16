"use client";

import { Fragment } from "react";
import { ArrowRight, FlaskConical } from "lucide-react";

import { ChemEquation } from "@/components/answer/ChemEquation";
import { EvidenceLevelBadge, EvidenceSignalBadge, type EvidenceSignal } from "@/components/answer/EvidenceBadge";
import { CitationChips } from "@/components/craft/CitationContext";
import { ConditionList } from "@/components/craft/ConditionList";
import {
  citationsOf,
  deltaHClaim,
  deltaHText,
  isUnbalanced,
  REACTION_KIND_LABEL,
  reactionSpoken,
  speciesNamesLine,
  speciesSides
} from "@/lib/processView";
import type { ProcessReaction, ReactionSpecies } from "@/lib/scienceContract";

function balanceSignal(reaction: ProcessReaction): EvidenceSignal | null {
  if (reaction.balanced) return "BALANCED";
  return isUnbalanced(reaction) ? "UNBALANCED" : null;
}

export function ReactionCard({ reaction }: { reaction: ProcessReaction }) {
  const signal = balanceSignal(reaction);
  const deltaClaim = deltaHClaim(reaction);
  return (
    <article className="rounded-md border border-line-200 bg-card p-3.5" data-testid="process-reaction">
      <header className="flex flex-wrap items-start justify-between gap-2">
        <span className="min-w-0">
          <span className="flex items-center gap-1.5 text-sm font-semibold text-ink-900">
            <FlaskConical className="h-4 w-4 shrink-0 text-purple-700 dark:text-purple-300" aria-hidden />
            {reaction.label}
          </span>
          <span className="block text-xs text-ink-500">{REACTION_KIND_LABEL[reaction.kind]}</span>
        </span>
        <span className="flex flex-wrap items-center gap-1.5">
          {signal ? <EvidenceSignalBadge signal={signal} /> : null}
          <EvidenceLevelBadge level={reaction.level} />
        </span>
      </header>
      {reaction.equation ? (
        <>
          <ChemEquation equation={reaction.equation} label={reactionSpoken(reaction)} className="mt-3 text-base" />
          <p className="mt-1 text-xs text-ink-500">{speciesNamesLine(reaction)}</p>
        </>
      ) : (
        <SpeciesRow reaction={reaction} />
      )}
      {reaction.deltaH && deltaClaim ? (
        <p className="mt-2 text-sm tabular-nums text-ink-700">
          {deltaHText(reaction.deltaH.kjPerMol)}
          <CitationChips citations={deltaClaim.citations} />
        </p>
      ) : null}
      {reaction.conditions.length > 0 ? (
        <div className="mt-3">
          <ConditionList conditions={reaction.conditions} />
        </div>
      ) : null}
      <p className="mt-2 text-xs">
        <CitationChips citations={citationsOf(reaction.claims)} />
      </p>
    </article>
  );
}

function SpeciesRow({ reaction }: { reaction: ProcessReaction }) {
  const { reactants, products } = speciesSides(reaction);
  return (
    <div className="mt-3">
      <p className="sr-only">{reactionSpoken(reaction)}</p>
      <p aria-hidden className="flex flex-wrap items-center gap-x-2 gap-y-1.5 text-sm text-ink-700">
        <SpeciesGroup species={reactants} />
        <ArrowRight className="h-4 w-4 shrink-0 text-ink-500" />
        <SpeciesGroup species={products} />
      </p>
    </div>
  );
}

function SpeciesGroup({ species }: { species: readonly ReactionSpecies[] }) {
  return species.map((entry, index) => (
    <Fragment key={`${entry.formula ?? ""}:${entry.name ?? ""}:${index}`}>
      {index > 0 ? <span className="text-ink-500">+</span> : null}
      <span className="inline-flex items-center gap-1.5 rounded-full border border-line-200 bg-surface-50 px-2.5 py-0.5">
        {entry.formula ? <ChemEquation equation={entry.formula} display={false} label={entry.formula} /> : null}
        {entry.name ? <span className="text-xs text-ink-700">{entry.name}</span> : null}
      </span>
    </Fragment>
  ));
}
