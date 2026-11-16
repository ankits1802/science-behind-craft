"use client";

import { FlaskConical } from "lucide-react";

import { ChemEquation } from "@/components/answer/ChemEquation";
import { CitationChip } from "@/components/answer/CitationChip";
import { EvidenceLevelBadge, EvidenceSignalBadge } from "@/components/answer/EvidenceBadge";
import { uniqueCitations } from "@/lib/citations";
import type { AnswerReaction, Citation, SourceRef } from "@/lib/types";

export function ReactionsPanel({
  reactions,
  numbers,
  sourcesById,
  onOpen
}: {
  reactions: AnswerReaction[];
  numbers: Map<string, number>;
  sourcesById: Map<string, SourceRef>;
  onOpen: (citation: Citation) => void;
}) {
  return (
    <section className="panel p-5 md:p-6" aria-labelledby="reactions-heading">
      <h2 id="reactions-heading" className="flex items-center gap-2 font-display text-lg font-bold text-ink-900">
        <FlaskConical className="h-5 w-5 text-purple-700 dark:text-purple-300" aria-hidden />
        Reactions
      </h2>
      <ol className="mt-3 grid gap-3">
        {reactions.map((reaction) => (
          <li key={reaction.id} className="rounded-md border border-line-200 bg-surface-50 p-4" data-testid="reaction">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-sm font-semibold text-ink-900">{reaction.label}</span>
              <span className="flex flex-wrap items-center gap-1.5">
                <EvidenceLevelBadge level={reaction.level} />
                {reaction.balanced ? null : <EvidenceSignalBadge signal="UNBALANCED" />}
              </span>
            </div>
            <ChemEquation equation={reaction.equation} className="mt-3 text-base" />
            {reaction.conditions ? <p className="mt-2 text-xs text-ink-500">{reaction.conditions}</p> : null}
            {reaction.citations.length > 0 ? (
              <p className="mt-2 text-xs">
                {uniqueCitations(reaction.citations).map((citation) => (
                  <CitationChip
                    key={`${citation.sourceId}:${citation.claimId}`}
                    citation={citation}
                    number={numbers.get(citation.sourceId) ?? null}
                    title={sourcesById.get(citation.sourceId)?.title ?? null}
                    onOpen={onOpen}
                  />
                ))}
              </p>
            ) : null}
          </li>
        ))}
      </ol>
    </section>
  );
}
