"use client";

import { AnimatePresence, motion } from "framer-motion";

import { ChemEquation } from "@/components/answer/ChemEquation";
import { CitationChips } from "@/components/answer/CitationContext";
import { EvidenceLevelBadge, EvidenceSignalBadge } from "@/components/answer/EvidenceBadge";
import { SpeciesRow } from "@/components/answer/SpeciesRow";
import { layoutSpring } from "@/components/guide/guideMotion";
import type { ReactionStep } from "@/lib/explainerMatter";
import { reactionSpoken, speciesNamesLine } from "@/lib/processView";
import { stepKindLabel, stepSignal } from "@/lib/reactionPlayer";
import { cn } from "@/lib/utils";

type StepListProps = { steps: readonly ReactionStep[]; open: number | null; reduce: boolean; onChoose: (index: number) => void };

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
        <span className="block text-xs text-ink-500">{stepKindLabel(step)}</span>
      </span>
    </span>
  );
}

function StepDetail({ step }: { step: ReactionStep }) {
  const signal = stepSignal(step);
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2 px-3 pb-3 sm:pl-[3.25rem]" data-testid="reaction-step-detail">
      <span className="flex flex-wrap items-center gap-1.5">
        {signal ? <EvidenceSignalBadge signal={signal} /> : null}
        <EvidenceLevelBadge level={step.level} />
      </span>
      {step.equation ? (
        <>
          <ChemEquation equation={step.equation} label={reactionSpoken(step)} className="text-base" />
          <p className="text-xs text-ink-500">{speciesNamesLine(step)}</p>
        </>
      ) : (
        <SpeciesRow reaction={step} />
      )}
      <p className="text-xs">
        <CitationChips citations={step.citations} />
      </p>
    </div>
  );
}

function StepItem({ step, index, open, reduce, onChoose }: Omit<StepListProps, "steps"> & { step: ReactionStep; index: number }) {
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
            <StepDetail step={step} />
          </motion.div>
        ) : null}
      </AnimatePresence>
    </li>
  );
}

export function ReactionStepList({ steps, open, reduce, onChoose }: StepListProps) {
  return (
    <ol className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2" aria-label="Reaction steps">
      {steps.map((step, index) => (
        <StepItem key={step.reactionId} step={step} index={index} open={open} reduce={reduce} onChoose={onChoose} />
      ))}
    </ol>
  );
}
