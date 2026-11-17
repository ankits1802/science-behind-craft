"use client";

import { motion } from "framer-motion";
import { Check, X } from "lucide-react";

import { useExplainerReading } from "@/components/answer/ExplainerReading";
import { CitedText } from "@/components/answer/ProseBlockView";
import { riseItem } from "@/components/guide/guideMotion";
import { sentenceView } from "@/lib/answerLanguages";
import type { QuizQuestion } from "@/lib/explainerLearning";
import { optionMark, optionOrder, promptParts, type OptionMark, type QuizPick } from "@/lib/quizView";
import { cn } from "@/lib/utils";

const OPTION = "flex min-h-12 w-full min-w-0 items-center justify-between gap-2 rounded-md border-2 px-4 py-2 text-left text-[15px] font-semibold transition-colors";

const MARK_CLASS: Record<OptionMark, string> = {
  open: "border-line-200 bg-card text-ink-900 hover:border-purple-300 hover:bg-purple-50 dark:hover:bg-purple-950/40",
  right: "border-evidence-600 bg-evidence-100 text-evidence-800 dark:border-evidence-400 dark:bg-evidence-950 dark:text-evidence-200",
  wrong: "border-steward-600 bg-steward-100 text-steward-800 dark:border-steward-400 dark:bg-steward-950 dark:text-steward-200",
  other: "border-line-200 bg-surface-50 text-ink-500"
};

const MARK_WORDS: Partial<Record<OptionMark, string>> = { right: "right answer", wrong: "your answer" };

function Prompt({ question, id }: { question: QuizQuestion; id: string }) {
  const { language } = useExplainerReading();
  const keyed = question.options[question.answer];
  const shown = keyed ? sentenceView(keyed.sentence, language, false) : null;
  const parts = promptParts(question.prompt);
  return (
    <p id={id} lang={shown?.lang} dir={shown?.dir} className="break-words font-display text-base font-semibold leading-7 text-ink-900 md:text-lg">
      {parts ? (
        <>
          {parts[0]}
          <span aria-hidden className="mx-0.5 inline-block w-16 border-b-2 border-purple-400 align-baseline dark:border-purple-300" data-testid="quiz-blank" />
          <span className="sr-only">blank</span>
          {parts[1]}
        </>
      ) : (
        question.prompt
      )}
    </p>
  );
}

function OptionButton({ text, mark, onPick }: { text: string; mark: OptionMark; onPick: () => void }) {
  const words = MARK_WORDS[mark];
  return (
    <button type="button" onClick={onPick} aria-disabled={mark !== "open"} className={cn(OPTION, MARK_CLASS[mark])} data-testid="quiz-option" data-mark={mark}>
      <span className="min-w-0 break-words">{text}</span>
      {mark === "right" ? <Check className="h-4 w-4 shrink-0" aria-hidden /> : null}
      {mark === "wrong" ? <X className="h-4 w-4 shrink-0" aria-hidden /> : null}
      {words ? <span className="sr-only">, {words}</span> : null}
    </button>
  );
}

function Reveal({ question, pick, id, reduce }: { question: QuizQuestion; pick: number; id: string; reduce: boolean }) {
  const keyed = question.options[question.answer];
  const right = pick === question.answer;
  return (
    <motion.div
      variants={riseItem(reduce, 8)}
      initial={reduce ? false : "hidden"}
      animate="show"
      className={cn(
        "grid min-w-0 gap-1 rounded-md border px-3 py-2.5",
        right ? "border-evidence-300 bg-evidence-50 dark:border-evidence-800 dark:bg-evidence-950/50" : "border-amber-500/40 bg-surface-50"
      )}
      data-testid="quiz-reveal"
      data-right={right ? "true" : "false"}
    >
      <p className={cn("text-sm font-semibold", right ? "text-evidence-800 dark:text-evidence-200" : "text-amber-800 dark:text-amber-200")}>
        {right ? "Right." : `Not quite. It is ${keyed.text}.`}
      </p>
      <CitedText id={id} sentences={[keyed.sentence]} className="text-sm leading-7 text-ink-700" />
    </motion.div>
  );
}

export function QuizQuestionCard({
  question,
  id,
  position,
  pick,
  reduce,
  onPick
}: {
  question: QuizQuestion;
  id: string;
  position: string;
  pick: QuizPick;
  reduce: boolean;
  onPick: (index: number) => void;
}) {
  const promptId = `${id}-prompt`;
  return (
    <li className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3 rounded-lg border border-line-200 bg-card p-4" data-testid="quiz-question" data-answered={pick === null ? "false" : "true"}>
      <span className="text-xs font-semibold text-ink-500">{position}</span>
      <Prompt question={question} id={promptId} />
      <div role="group" aria-labelledby={promptId} className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2 sm:grid-cols-[repeat(2,minmax(0,1fr))]">
        {optionOrder(question.options).map((index) => (
          <OptionButton key={question.options[index].termKey} text={question.options[index].text} mark={optionMark(question, pick, index)} onPick={() => onPick(index)} />
        ))}
      </div>
      <div aria-live="polite" className="min-w-0">
        {pick !== null ? <Reveal question={question} pick={pick} id={`${id}-answer`} reduce={reduce} /> : null}
      </div>
    </li>
  );
}
