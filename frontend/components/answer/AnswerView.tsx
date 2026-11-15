"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ExternalLink, FlaskConical, Loader2 } from "lucide-react";

import { ChemEquation } from "@/components/answer/ChemEquation";
import { CitationChip } from "@/components/answer/CitationChip";
import { EvidenceLevelBadge } from "@/components/answer/EvidenceBadge";
import { SourceDialog, type OpenCitation } from "@/components/answer/SourceDialog";
import { riseItem } from "@/components/guide/guideMotion";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { Accordion } from "@/components/ui/Accordion";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { sourceByline, sourceHost, sourceHref, sourceNumbers, uniqueCitations } from "@/lib/citations";
import type { AnswerPayload, AnswerReaction, AnswerSection, AnswerSentence, Citation, SourceRef } from "@/lib/types";

export type AnswerViewProps = {
  payload: AnswerPayload;
  streaming?: boolean;
  onFollowUp?: (question: string) => void;
};

export function AnswerView({ payload, streaming = false, onFollowUp }: AnswerViewProps) {
  const reduce = useAppReducedMotion();
  const [open, setOpen] = useState<OpenCitation | null>(null);
  const sourcesById = useMemo(() => new Map(payload.sources.map((source) => [source.id, source])), [payload.sources]);
  const numbers = useMemo(
    () => sourceNumbers([...payload.sections, ...payload.openQuestions], payload.reactions),
    [payload.openQuestions, payload.reactions, payload.sections]
  );
  const numbered = useMemo(
    () =>
      [...numbers.entries()]
        .sort((a, b) => a[1] - b[1])
        .map(([id, number]) => ({ number, source: sourcesById.get(id) ?? null, id })),
    [numbers, sourcesById]
  );

  const openCitation = useCallback(
    (citation: Citation) => setOpen({ citation, source: sourcesById.get(citation.sourceId) ?? null, number: numbers.get(citation.sourceId) ?? null }),
    [numbers, sourcesById]
  );

  const hasBody = payload.sections.some((section) => section.sentences.length > 0);

  return (
    <article className="grid gap-5" aria-busy={streaming || undefined} data-testid="answer-view">
      {payload.craft ? (
        <p className="text-sm text-ink-500">
          About{" "}
          <Link href={`/crafts/${encodeURIComponent(payload.craft.slug)}`} className="font-medium text-purple-700 hover:underline dark:text-purple-300">
            {payload.craft.name}
          </Link>
          {payload.craft.path ? <span> · {payload.craft.path}</span> : null}
        </p>
      ) : null}

      {payload.sections.map((section) =>
        section.sentences.length > 0 ? (
          <SectionBlock key={section.id} section={section} reduce={reduce} numbers={numbers} sourcesById={sourcesById} onOpen={openCitation} />
        ) : null
      )}

      {streaming ? (
        <p className="flex items-center gap-2 text-sm text-ink-500" role="status">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          {hasBody ? "Writing…" : "Reading the sources…"}
        </p>
      ) : null}

      {payload.reactions.length > 0 ? (
        <ReactionsPanel reactions={payload.reactions} numbers={numbers} sourcesById={sourcesById} onOpen={openCitation} />
      ) : null}

      {payload.openQuestions.some((section) => section.sentences.length > 0) ? (
        <Accordion title="Open questions" subtitle="Hypotheses with no direct quote.">
          <div className="grid gap-4">
            {payload.openQuestions.map((section) =>
              section.sentences.length > 0 ? (
                <SectionBlock key={section.id} section={section} reduce={reduce} numbers={numbers} sourcesById={sourcesById} onOpen={openCitation} compact />
              ) : null
            )}
          </div>
        </Accordion>
      ) : null}

      {numbered.length > 0 ? <SourcesList entries={numbered} /> : null}

      {!streaming && payload.followUps.length > 0 && onFollowUp ? (
        <section aria-label="Ask next">
          <h2 className="field-label mb-2">Ask next</h2>
          <ActionGroup align="start">
            {payload.followUps.map((question) => (
              <button key={question} type="button" className="field-button-secondary" onClick={() => onFollowUp(question)}>
                {question}
              </button>
            ))}
          </ActionGroup>
        </section>
      ) : null}

      <SourceDialog open={open} onClose={() => setOpen(null)} />
    </article>
  );
}

function SectionBlock({
  section,
  reduce,
  numbers,
  sourcesById,
  onOpen,
  compact = false
}: {
  section: AnswerSection;
  reduce: boolean;
  numbers: Map<string, number>;
  sourcesById: Map<string, SourceRef>;
  onOpen: (citation: Citation) => void;
  compact?: boolean;
}) {
  return (
    <section className={compact ? "" : "panel p-5 md:p-6"}>
      {section.heading ? <h2 className="font-display text-lg font-bold text-ink-900">{section.heading}</h2> : null}
      <p className={section.heading ? "mt-2 text-[15px] leading-8 text-ink-700" : "text-[15px] leading-8 text-ink-700"}>
        {section.sentences.map((sentence) => (
          <SentenceRun key={sentence.id} sentence={sentence} reduce={reduce} numbers={numbers} sourcesById={sourcesById} onOpen={onOpen} />
        ))}
      </p>
    </section>
  );
}

function SentenceRun({
  sentence,
  reduce,
  numbers,
  sourcesById,
  onOpen
}: {
  sentence: AnswerSentence;
  reduce: boolean;
  numbers: Map<string, number>;
  sourcesById: Map<string, SourceRef>;
  onOpen: (citation: Citation) => void;
}) {
  const citations = uniqueCitations(sentence.citations);
  return (
    <motion.span variants={riseItem(reduce, 4)} initial="hidden" animate="show" className="inline" data-testid="answer-sentence" data-level={sentence.level}>
      {sentence.text}
      {sentence.translated ? <span className="ml-1 rounded-sm bg-surface-50 px-1 text-[10px] font-semibold uppercase tracking-wide text-ink-500">Translated</span> : null}
      {citations.map((citation) => (
        <CitationChip
          key={`${citation.sourceId}:${citation.claimId}`}
          citation={citation}
          number={numbers.get(citation.sourceId) ?? null}
          title={sourcesById.get(citation.sourceId)?.title ?? null}
          onOpen={onOpen}
        />
      ))}{" "}
    </motion.span>
  );
}

function ReactionsPanel({
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
                {reaction.balanced ? null : <span className="rounded-full border border-amber-500/30 bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">Unbalanced</span>}
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

function SourcesList({ entries }: { entries: { number: number; id: string; source: SourceRef | null }[] }) {
  return (
    <section className="panel p-5 md:p-6" aria-labelledby="sources-heading">
      <h2 id="sources-heading" className="font-display text-lg font-bold text-ink-900">
        Sources
      </h2>
      <ol className="mt-3 grid gap-2.5">
        {entries.map(({ number, id, source }) => {
          const href = source ? sourceHref(source) : null;
          return (
            <li key={id} className="grid grid-cols-[2rem_minmax(0,1fr)] gap-2 text-sm">
              <span className="font-display font-bold tabular-nums text-purple-700 dark:text-purple-300">[{number}]</span>
              <span className="min-w-0">
                {href ? (
                  <a href={href} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-medium text-ink-900 hover:text-purple-700 hover:underline">
                    {source?.title ?? "Source"}
                    <ExternalLink className="h-3.5 w-3.5 shrink-0" aria-hidden />
                  </a>
                ) : (
                  <span className="font-medium text-ink-900">{source?.title ?? "Source"}</span>
                )}
                {source ? (
                  <span className="block text-xs text-ink-500">
                    {[sourceByline(source), sourceHost(href)].filter(Boolean).join(" · ")}
                  </span>
                ) : null}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
