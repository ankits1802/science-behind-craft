"use client";

import { motion } from "framer-motion";
import { Mic } from "lucide-react";

import type { Dictation } from "@/components/ask/useDictation";
import { soundBar } from "@/components/guide/guideMotion";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import type { AnswerLanguage } from "@/lib/answerLanguages";
import { listeningLabel } from "@/lib/dictation";
import { cn } from "@/lib/utils";

const BARS = [0, 1, 2, 3, 4];

function SoundBars() {
  const reduce = useAppReducedMotion();
  return (
    <span className="hidden h-6 items-center gap-1 sm:flex" aria-hidden>
      {BARS.map((index) => (
        <motion.span key={index} initial={false} {...soundBar(reduce, index)} className="h-[22px] w-1 origin-center rounded-full bg-purple-700 dark:bg-purple-300" />
      ))}
    </span>
  );
}

function MicButton({ listening, language, onPress }: { listening: boolean; language: AnswerLanguage; onPress: () => void }) {
  const label = listening ? "Stop dictation" : `Dictate in ${language.label}`;
  return (
    <button type="button" onClick={onPress} aria-label={label} title={label} data-testid="dictate-button" className="group relative grid h-11 w-11 shrink-0 place-items-center rounded-full">
      {listening ? <span aria-hidden className="absolute inset-0 rounded-full bg-purple-700/40 motion-safe:animate-ping dark:bg-purple-400/40" /> : null}
      <span
        aria-hidden
        className={cn(
          "relative grid h-11 w-11 place-items-center rounded-full transition",
          listening
            ? "border-[3px] border-purple-300 bg-purple-700 text-white dark:border-purple-500 dark:bg-purple-400 dark:text-purple-950"
            : "border border-line-200 bg-card text-ink-700 group-hover:border-purple-300 group-hover:bg-purple-50 group-hover:text-purple-700 dark:group-hover:bg-purple-950/40 dark:group-hover:text-purple-200"
        )}
      >
        <Mic className={listening ? "h-[18px] w-[18px]" : "h-5 w-5"} />
      </span>
    </button>
  );
}

export function DictationControl({ dictation, language, onStart }: { dictation: Dictation; language: AnswerLanguage; onStart: () => void }) {
  const { listening, offered, failure } = dictation;
  const said = listening ? listeningLabel(language) : failure;
  return (
    <div className="flex min-w-0 items-center gap-3">
      {listening || offered ? <MicButton listening={listening} language={language} onPress={listening ? dictation.stop : onStart} /> : null}
      {listening ? <SoundBars /> : null}
      <span
        role="status"
        dir="auto"
        className={cn("min-w-0 text-sm", listening ? "truncate font-semibold text-purple-800 dark:text-purple-200" : "text-ink-500", !said && "sr-only")}
      >
        {said}
      </span>
    </div>
  );
}
