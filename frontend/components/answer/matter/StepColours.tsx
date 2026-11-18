"use client";

import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

import { CitationChips } from "@/components/answer/CitationContext";
import type { ReactionStep, StepColour } from "@/lib/explainerMatter";
import { COLOUR_LABEL, colourChange, colourChangeLine, DYE_SWATCH, type ColourChange } from "@/lib/reactionPlayer";
import { cn } from "@/lib/utils";

const CHANGE_SECONDS = 1.6;

function Swatch({ colour, label }: { colour: StepColour; label: string }) {
  return (
    <span className="inline-flex min-w-0 items-center gap-2" data-testid="step-colour" data-side={colour.side} data-colour={colour.colour}>
      <span aria-hidden className={cn("h-6 w-6 shrink-0 rounded-md border border-line-200", DYE_SWATCH[colour.colour])} />
      <span className="text-xs text-ink-700">
        <span className="font-semibold text-ink-900">{label}</span> {COLOUR_LABEL[colour.colour].toLowerCase()}
      </span>
    </span>
  );
}

function Cloth({ change, animate }: { change: ColourChange; animate: boolean }) {
  const start = change.before ?? change.after;
  const end = change.after ?? change.before;
  if (!start || !end) return null;
  return (
    <span aria-hidden className="relative block h-10 w-full overflow-hidden rounded-lg border border-line-200" data-testid="step-cloth">
      <span className={cn("absolute inset-0", DYE_SWATCH[start.colour])} />
      <motion.span
        className={cn("absolute inset-0", DYE_SWATCH[end.colour])}
        initial={{ opacity: animate ? 0 : 1 }}
        animate={{ opacity: 1 }}
        transition={animate ? { duration: CHANGE_SECONDS, ease: "easeInOut" } : { duration: 0 }}
      />
    </span>
  );
}

function stated(change: ColourChange): StepColour[] {
  const colours = [change.before, change.after].filter((colour): colour is StepColour => colour !== null);
  return colours.filter((colour, index) => colours.findIndex((other) => other.stated === colour.stated) === index);
}

export function StepColours({ step, animate }: { step: Pick<ReactionStep, "colours">; animate: boolean }) {
  const change = colourChange(step);
  if (!change) return null;
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2 rounded-lg border border-line-200 bg-surface-50 p-3" data-testid="step-colours">
      <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">{colourChangeLine(change)}</p>
      <Cloth change={change} animate={animate} />
      <p className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
        {change.before ? <Swatch colour={change.before} label="Before" /> : null}
        {change.before && change.after ? <ArrowRight className="h-4 w-4 shrink-0 text-ink-500" aria-hidden /> : null}
        {change.after ? <Swatch colour={change.after} label="After" /> : null}
      </p>
      {stated(change).map((colour) => (
        <p key={colour.side} className="text-xs leading-5 text-ink-700">
          <q>{colour.stated}</q>
          <CitationChips citations={colour.citations} />
        </p>
      ))}
    </div>
  );
}
