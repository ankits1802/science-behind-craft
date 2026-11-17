"use client";

import { FlaskConical } from "lucide-react";

import { ChemEquation } from "@/components/answer/ChemEquation";
import { EvidenceSignalBadge } from "@/components/answer/EvidenceBadge";
import { SpeciesRow } from "@/components/answer/SpeciesRow";
import { ClaimChips } from "@/components/craft/CraftClaims";
import type { PageReaction } from "@/lib/craftPageContract";
import { REACTION_KIND_LABEL, reactionSpoken, speciesNamesLine } from "@/lib/processView";

function hasFormula(reaction: PageReaction): boolean {
  return reaction.species.some((species) => species.formula !== null);
}

export function ReactionCard({ reaction }: { reaction: PageReaction }) {
  return (
    <article className="min-w-0 rounded-md border border-line-200 bg-card p-3.5" data-testid="process-reaction" data-balanced={reaction.balanced}>
      <header className="flex flex-wrap items-start justify-between gap-2">
        <span className="min-w-0">
          <span className="flex items-start gap-1.5 text-sm font-semibold text-ink-900">
            <FlaskConical className="mt-0.5 h-4 w-4 shrink-0 text-purple-700 dark:text-purple-300" aria-hidden />
            <span className="min-w-0 [overflow-wrap:anywhere]">{reaction.label}</span>
          </span>
          <span className="block text-xs text-ink-500">{REACTION_KIND_LABEL[reaction.kind]}</span>
        </span>
        {reaction.balanced ? <EvidenceSignalBadge signal="BALANCED" /> : null}
      </header>
      {reaction.equation ? (
        <>
          <ChemEquation equation={reaction.equation} label={reactionSpoken(reaction)} className="mt-3 text-base" />
          <p className="mt-1 text-xs text-ink-500 [overflow-wrap:anywhere]">{speciesNamesLine(reaction)}</p>
        </>
      ) : hasFormula(reaction) ? (
        <SpeciesRow reaction={reaction} />
      ) : null}
      <p className="mt-2 text-xs">
        <ClaimChips ids={reaction.claimIds} />
      </p>
    </article>
  );
}
