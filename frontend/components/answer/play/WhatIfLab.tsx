"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CircleHelp } from "lucide-react";

import { ExplainerSentence } from "@/components/answer/ExplainerSentence";
import { swapVariants } from "@/components/guide/guideMotion";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import type { WhatIfBlock, WhatIfOption } from "@/lib/explainerPlay";
import { cn } from "@/lib/utils";
import { isUnknownOption, optionNote, UNKNOWN_OUTCOME } from "@/lib/whatIfView";

function OptionButton({ option, on, onPick }: { option: WhatIfOption; on: boolean; onPick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onPick}
      className={cn(
        "flex min-h-11 min-w-0 flex-col items-start gap-0.5 rounded-md border px-3 py-2 text-left text-sm transition-colors",
        on
          ? "border-purple-700 bg-purple-700 text-white"
          : "border-line-200 bg-card text-ink-900 hover:border-purple-300 hover:bg-purple-50 dark:hover:bg-purple-950/40"
      )}
      data-testid="what-if-option"
      data-unknown={isUnknownOption(option)}
    >
      <span className="min-w-0 max-w-full break-words font-semibold">{option.label}</span>
      <span className={cn("text-xs", on ? "text-purple-100" : "text-ink-500")}>{optionNote(option)}</span>
    </button>
  );
}

function Outcomes({ option }: { option: WhatIfOption }) {
  if (isUnknownOption(option)) {
    return (
      <p className="flex items-center gap-1.5 text-sm font-semibold text-ink-700" data-testid="what-if-unknown">
        <CircleHelp className="h-4 w-4 shrink-0 text-ink-500" aria-hidden />
        {UNKNOWN_OUTCOME}
      </p>
    );
  }
  return (
    <ul className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2">
      {option.outcomes.map((outcome) => (
        <li key={outcome.sentence.id} className="min-w-0 break-words text-sm leading-7 text-ink-700" data-testid="what-if-outcome">
          <ExplainerSentence sentence={outcome.sentence} />
        </li>
      ))}
    </ul>
  );
}

export function WhatIfLabView({ block, reduce }: { block: WhatIfBlock; reduce: boolean }) {
  const [chosen, setChosen] = useState(0);
  const option = block.options[chosen];
  const titleId = `${block.id}-title`;
  return (
    <section className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3 rounded-lg border border-line-200 bg-card p-4 sm:p-5" aria-labelledby={titleId} data-testid="what-if" data-chosen={chosen + 1}>
      <header className="min-w-0">
        <p className="eyebrow">What if</p>
        <h3 id={titleId} className="mt-1 break-words font-display text-lg font-bold text-ink-900">
          {block.changed}
        </h3>
      </header>
      <div role="group" aria-labelledby={titleId} className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2 sm:grid-cols-[repeat(2,minmax(0,1fr))] lg:grid-cols-[repeat(3,minmax(0,1fr))]">
        {block.options.map((entry, index) => (
          <OptionButton key={entry.label} option={entry} on={index === chosen} onPick={() => setChosen(index)} />
        ))}
      </div>
      <div className="min-w-0 rounded-md border border-line-200 bg-surface-50 p-3 sm:p-4" aria-live="polite" data-testid="what-if-outcomes" data-motion={reduce ? "none" : "swap"}>
        <AnimatePresence mode="wait" initial={false}>
          <motion.div key={chosen} variants={swapVariants(reduce)} initial="hidden" animate="show" exit="exit" className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2">
            <p className="min-w-0 break-words text-xs font-semibold text-ink-500">{option.label}</p>
            <Outcomes option={option} />
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}

export function WhatIfLab({ block }: { block: WhatIfBlock }) {
  const reduce = useAppReducedMotion();
  return <WhatIfLabView block={block} reduce={reduce} />;
}
