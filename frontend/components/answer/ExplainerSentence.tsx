"use client";

import { CitationChips } from "@/components/answer/CitationContext";
import { EvidenceLevelBadge } from "@/components/answer/EvidenceBadge";
import { useExplainerReading } from "@/components/answer/ExplainerReading";
import { sentenceView } from "@/lib/answerLanguages";
import type { ExplainerSentence as Sentence } from "@/lib/explainerBlockBase";
import { sentenceSegments, type TextPart } from "@/lib/explainerView";
import { wordRanges } from "@/lib/listen";
import type { EvidenceLevel } from "@/lib/types";
import { cn } from "@/lib/utils";

const MARKED_LEVELS: ReadonlySet<EvidenceLevel> = new Set(["VERIFIED", "REVIEWED", "HYPOTHESIS"]);

export const TERM_CLASS =
  "rounded-sm font-medium text-ink-900 underline decoration-purple-500 decoration-dotted decoration-[1.5px] underline-offset-[3px] transition hover:decoration-solid dark:decoration-purple-300";

function Parts({ parts }: { parts: TextPart[] }) {
  return parts.map((part, index) =>
    part.marked ? (
      <mark key={index} className="rounded-sm bg-purple-200 text-ink-900 dark:bg-purple-800 dark:text-white" data-testid="listen-word">
        {part.text}
      </mark>
    ) : (
      <span key={index}>{part.text}</span>
    )
  );
}

export function ExplainerSentence({ sentence }: { sentence: Sentence }) {
  const reading = useExplainerReading();
  const shown = sentenceView(sentence, reading.language, reading.original);
  const terms = sentence.terms.filter((span) => !reading.hiddenTerms.has(span.termKey));
  const listening = reading.listen?.sentenceId === sentence.id ? reading.listen : null;
  const mark = listening ? (wordRanges(shown.text, listening.words)[listening.wordIndex] ?? null) : null;
  const segments = sentenceSegments(shown.text, terms, mark);

  return (
    <span
      className={cn("inline rounded-sm transition-colors", listening ? "bg-purple-50 box-decoration-clone dark:bg-purple-950/60" : null)}
      data-testid="answer-sentence"
      data-sentence-id={sentence.id}
      data-level={sentence.level}
      data-listening={listening ? "true" : undefined}
    >
      <span lang={shown.lang} dir={shown.dir}>
        {segments.map((segment, index) => {
          const term = segment.term;
          return term ? (
            <button
              key={index}
              type="button"
              className={TERM_CLASS}
              aria-haspopup="dialog"
              data-testid="term-span"
              onClick={() => reading.onTerm(term)}
            >
              <Parts parts={segment.parts} />
            </button>
          ) : (
            <Parts key={index} parts={segment.parts} />
          );
        })}
      </span>
      <CitationChips citations={sentence.citations} />
      {MARKED_LEVELS.has(sentence.level) ? <EvidenceLevelBadge level={sentence.level} className="ml-0.5 align-middle" /> : null}{" "}
    </span>
  );
}
