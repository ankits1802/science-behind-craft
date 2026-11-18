"use client";

import { AnimatePresence, motion } from "framer-motion";

import { StepDetail } from "@/components/answer/matter/StepDetail";
import { layoutSpring } from "@/components/guide/guideMotion";
import type { ExplainerSentence } from "@/lib/explainerBlockBase";
import type { ReactionStep } from "@/lib/explainerMatter";
import { stepKindLabel } from "@/lib/reactionPlayer";
import { cn } from "@/lib/utils";

type StepListProps = {
  steps: readonly ReactionStep[];
  open: number | null;
  reduce: boolean;
  onChoose: (index: number) => void;
  notesFor: (step: ReactionStep) => readonly ExplainerSentence[];
};

function StepNumber({ number, reached }: { number: number; reached: boolean }) {
  return (
    <span
      aria-hidden
      className={cn(
        "grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-bold tabular-nums transition-colors duration-300",
        reached ? "bg-purple-700 text-white dark:bg-purple-400 dark:text-purple-950" : "border border-line-200 bg-card text-ink-500"
      )}
    >
      {number}
    </span>
  );
}

function StepLabel({ step, number, reached }: { step: ReactionStep; number: number; reached: boolean }) {
  return (
    <span className="flex min-w-0 items-start gap-3">
      <StepNumber number={number} reached={reached} />
      <span className="min-w-0 pt-0.5">
        <span className="block break-words text-sm font-semibold text-ink-900">{step.label}</span>
        <span className="block text-xs text-ink-500">{step.stage ? `${stepKindLabel(step)} · ${step.stage}` : stepKindLabel(step)}</span>
      </span>
    </span>
  );
}

function StepItem({ step, index, open, reduce, onChoose, notesFor }: Omit<StepListProps, "steps"> & { step: ReactionStep; index: number }) {
  const current = open === index;
  const expanded = open === null || current;
  const reached = open === null || index <= open;
  return (
    <li
      aria-current={current ? "step" : undefined}
      data-testid="reaction-step"
      data-open={expanded ? "true" : "false"}
      className={cn(
        "min-w-0 rounded-lg border transition-colors duration-300",
        current ? "border-purple-300 bg-purple-50/70 dark:border-purple-800 dark:bg-purple-950/30" : "border-line-200 bg-card"
      )}
    >
      {open === null ? (
        <div className="p-3">
          <StepLabel step={step} number={index + 1} reached={reached} />
        </div>
      ) : (
        <button type="button" onClick={() => onChoose(index)} aria-expanded={current} className="w-full rounded-lg p-3 text-left">
          <StepLabel step={step} number={index + 1} reached={reached} />
        </button>
      )}
      <AnimatePresence initial={false}>
        {expanded ? (
          <motion.div
            key="detail"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={reduce ? { duration: 0 } : { height: layoutSpring(false), opacity: { duration: 0.18 } }}
            className="overflow-hidden"
          >
            <StepDetail step={step} notes={notesFor(step)} animate={current && !reduce} />
          </motion.div>
        ) : null}
      </AnimatePresence>
    </li>
  );
}

export function ReactionStepList({ steps, open, reduce, onChoose, notesFor }: StepListProps) {
  return (
    <ol className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2" aria-label="Reaction steps">
      {steps.map((step, index) => (
        <StepItem key={step.reactionId} step={step} index={index} open={open} reduce={reduce} onChoose={onChoose} notesFor={notesFor} />
      ))}
    </ol>
  );
}
