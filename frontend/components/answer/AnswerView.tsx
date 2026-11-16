"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";

import { AnswerProgress } from "@/components/answer/AnswerProgress";
import { SectionBlock } from "@/components/answer/AnswerSectionBlock";
import { ReactionsPanel } from "@/components/answer/ReactionsPanel";
import { SourceDialog, type OpenCitation } from "@/components/answer/SourceDialog";
import { SourcesList } from "@/components/answer/SourcesList";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { Accordion } from "@/components/ui/Accordion";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { SegmentedChoice } from "@/components/ui/SegmentedChoice";
import { attributesForText, ENGLISH, hasTranslation, type AnswerLanguage } from "@/lib/answerLanguages";
import { sourceNumbers } from "@/lib/citations";
import type { AnswerPayload, AnswerStatus, Citation } from "@/lib/types";

export type AnswerViewProps = {
  payload: AnswerPayload;
  streaming?: boolean;
  status?: AnswerStatus | null;
  onFollowUp?: (question: string) => void;
  language?: AnswerLanguage;
};

const ORIGINAL = "original";
const TRANSLATED = "translated";

export function AnswerView({ payload, streaming = false, status = null, onFollowUp, language = ENGLISH }: AnswerViewProps) {
  const reduce = useAppReducedMotion();
  const [open, setOpen] = useState<OpenCitation | null>(null);
  const [shown, setShown] = useState(TRANSLATED);
  const translated = hasTranslation([...payload.sections, ...payload.openQuestions]);
  const original = translated && shown === ORIGINAL;
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
      {payload.craft || translated ? (
        <div className="flex flex-wrap items-center justify-between gap-3">
          {payload.craft ? (
            <p className="text-sm text-ink-500">
              About{" "}
              <Link href={`/crafts/${encodeURIComponent(payload.craft.slug)}`} className="font-medium text-purple-700 hover:underline dark:text-purple-300">
                {payload.craft.name}
              </Link>
              {payload.craft.path ? <span> · {payload.craft.path}</span> : null}
            </p>
          ) : (
            <span />
          )}
          {translated ? (
            <SegmentedChoice
              label="Answer text"
              value={original ? ORIGINAL : TRANSLATED}
              options={[
                { value: TRANSLATED, label: language.autonym },
                { value: ORIGINAL, label: ENGLISH.label }
              ]}
              onChange={setShown}
            />
          ) : null}
        </div>
      ) : null}

      {payload.sections.map((section) =>
        section.sentences.length > 0 ? (
          <SectionBlock
            key={section.id}
            section={section}
            reduce={reduce}
            numbers={numbers}
            sourcesById={sourcesById}
            onOpen={openCitation}
            language={language}
            original={original}
          />
        ) : null
      )}

      {streaming ? <AnswerProgress status={status} writing={hasBody} /> : null}

      {payload.reactions.length > 0 ? (
        <ReactionsPanel reactions={payload.reactions} numbers={numbers} sourcesById={sourcesById} onOpen={openCitation} />
      ) : null}

      {payload.openQuestions.some((section) => section.sentences.length > 0) ? (
        <Accordion title="Open questions" subtitle="Hypotheses with no direct quote.">
          <div className="grid gap-4">
            {payload.openQuestions.map((section) =>
              section.sentences.length > 0 ? (
                <SectionBlock
                  key={section.id}
                  section={section}
                  reduce={reduce}
                  numbers={numbers}
                  sourcesById={sourcesById}
                  onOpen={openCitation}
                  compact
                  language={language}
                  original={original}
                />
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
              <button key={question} type="button" className="field-button-secondary" onClick={() => onFollowUp(question)} {...attributesForText(question, language)}>
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
