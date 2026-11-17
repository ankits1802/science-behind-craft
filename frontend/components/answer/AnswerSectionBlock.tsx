"use client";

import { motion } from "framer-motion";

import { CitationChip } from "@/components/answer/CitationChip";
import { riseItem } from "@/components/guide/guideMotion";
import { headingView, paragraphAttributes, sentenceView, type AnswerLanguage } from "@/lib/answerLanguages";
import { uniqueCitations } from "@/lib/citations";
import type { AnswerSection, AnswerSentence, Citation, SourceRef } from "@/lib/types";

export function SectionBlock({
  section,
  reduce,
  numbers,
  sourcesById,
  onOpen,
  compact = false,
  language = null,
  original = false
}: {
  section: AnswerSection;
  reduce: boolean;
  numbers: Map<string, number>;
  sourcesById: Map<string, SourceRef>;
  onOpen: (citation: Citation) => void;
  compact?: boolean;
  language?: AnswerLanguage | null;
  original?: boolean;
}) {
  const heading = headingView(section, language, original);
  const paragraph = paragraphAttributes(section, language, original);
  return (
    <section className={compact ? "" : "panel p-5 md:p-6"}>
      {heading.text ? (
        <h2 lang={heading.lang} dir={heading.dir} className="font-display text-lg font-bold text-ink-900">
          {heading.text}
        </h2>
      ) : null}
      <p lang={paragraph.lang} dir={paragraph.dir} className={heading.text ? "mt-2 text-[15px] leading-8 text-ink-700" : "text-[15px] leading-8 text-ink-700"}>
        {section.sentences.map((sentence) => (
          <SentenceRun
            key={sentence.id}
            sentence={sentence}
            reduce={reduce}
            numbers={numbers}
            sourcesById={sourcesById}
            onOpen={onOpen}
            language={language}
            original={original}
          />
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
  onOpen,
  language,
  original
}: {
  sentence: AnswerSentence;
  reduce: boolean;
  numbers: Map<string, number>;
  sourcesById: Map<string, SourceRef>;
  onOpen: (citation: Citation) => void;
  language: AnswerLanguage | null;
  original: boolean;
}) {
  const citations = uniqueCitations(sentence.citations);
  const shown = sentenceView(sentence, language, original);
  return (
    <motion.span variants={riseItem(reduce, 4)} initial="hidden" animate="show" className="inline" data-testid="answer-sentence" data-sentence-id={sentence.id} data-level={sentence.level}>
      <span lang={shown.lang} dir={shown.dir}>
        {shown.text}
      </span>
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
