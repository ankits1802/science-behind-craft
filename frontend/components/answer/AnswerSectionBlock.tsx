"use client";

import { motion } from "framer-motion";

import { CitationChip } from "@/components/answer/CitationChip";
import { riseItem } from "@/components/guide/guideMotion";
import { uniqueCitations } from "@/lib/citations";
import type { AnswerSection, AnswerSentence, Citation, SourceRef } from "@/lib/types";

export function SectionBlock({
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
