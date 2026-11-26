"use client";

import { useRef, type KeyboardEvent } from "react";

import { StepDetail } from "@/components/answer/matter/StepDetail";
import { STEP_NUMBER } from "@/components/answer/place/figureMarks";
import { nextTabIndex } from "@/components/ui/Tabs";
import type { ExplainerSentence } from "@/lib/explainerBlockBase";
import type { ReactionStep } from "@/lib/explainerMatter";
import { railKey, stepKindLabel } from "@/lib/reactionPlayer";
import { cn } from "@/lib/utils";

type Notes = (step: ReactionStep) => readonly ExplainerSentence[];
type RailProps = { steps: readonly ReactionStep[]; at: number; onChoose: (index: number) => void };

function StepNumber({ number, reached }: { number: number; reached: boolean }) {
  return (
    <span aria-hidden className={cn(STEP_NUMBER, reached ? "bg-ink-1 text-ground" : "border border-rule-strong text-ink-3")}>
      {number}
    </span>
  );
}

function StepLabel({ step, number, reached }: { step: ReactionStep; number: number; reached: boolean }) {
  return (
    <span className="flex min-w-0 items-start gap-3">
      <StepNumber number={number} reached={reached} />
      <span className="min-w-0 pt-1">
        <span className="block break-words font-ui text-h4 text-ink-1">{step.label}</span>
        <span className="block break-words font-ui text-caption text-ink-3">{step.stage ? `${stepKindLabel(step)} · ${step.stage}` : stepKindLabel(step)}</span>
      </span>
    </span>
  );
}

export function ReactionStepList({ steps, notesFor }: { steps: readonly ReactionStep[]; notesFor: Notes }) {
  return (
    <ol className="grid min-w-0 grid-cols-[minmax(0,1fr)] border-t border-rule" aria-label="Reaction steps">
      {steps.map((step, index) => (
        <li key={step.reactionId} data-testid="reaction-step" data-open="true" className="min-w-0 border-b border-s-2 border-b-rule border-s-transparent ps-3 sm:ps-4">
          <div className="py-3">
            <StepLabel step={step} number={index + 1} reached />
          </div>
          <StepDetail step={step} notes={notesFor(step)} animate={false} />
        </li>
      ))}
    </ol>
  );
}

export function ReactionStepRail({ steps, at, onChoose }: RailProps) {
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  function onKeyDown(event: KeyboardEvent<HTMLOListElement>) {
    const next = nextTabIndex(railKey(event.key), at, steps.length);
    if (next === null) return;
    event.preventDefault();
    onChoose(next);
    buttons.current[next]?.focus();
  }
  return (
    <ol className="grid min-w-0 grid-cols-[minmax(0,1fr)] border-t border-rule" aria-label="Reaction steps" onKeyDown={onKeyDown} data-testid="reaction-rail">
      {steps.map((step, index) => {
        const current = index === at;
        return (
          <li
            key={step.reactionId}
            aria-current={current ? "step" : undefined}
            data-testid="reaction-step"
            data-open={current ? "true" : "false"}
            className={cn("min-w-0 border-b border-s-2 border-b-rule ps-3 transition-colors duration-state sm:ps-4", current ? "border-s-ink-1" : "border-s-transparent")}
          >
            <button
              ref={(node) => {
                buttons.current[index] = node;
              }}
              type="button"
              aria-pressed={current}
              tabIndex={current ? 0 : -1}
              onClick={() => onChoose(index)}
              className="block w-full rounded-control py-3 text-start hover:bg-sunk"
            >
              <StepLabel step={step} number={index + 1} reached={index <= at} />
            </button>
          </li>
        );
      })}
    </ol>
  );
}
