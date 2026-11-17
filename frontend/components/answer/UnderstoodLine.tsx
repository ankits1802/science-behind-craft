"use client";

import type { ReactNode } from "react";
import { ChevronDown } from "lucide-react";

import type { AnswerLanguage } from "@/lib/answerLanguages";
import { ANY_CRAFT, namesLine } from "@/lib/askCraft";
import type { Understood } from "@/lib/explainerContract";
import type { UnderstoodPart } from "@/lib/explainerView";

export type UnderstoodChange = { parts: ReadonlySet<UnderstoodPart>; onChange: (part: UnderstoodPart) => void };

const PART_CLASS =
  "inline-flex min-h-8 items-center gap-1 rounded-full border border-purple-200 bg-purple-50 px-3 text-[13px] font-semibold text-purple-800 transition hover:border-purple-400 dark:border-purple-900 dark:bg-purple-950/50 dark:text-purple-200 pointer-coarse:min-h-11";

const PART_NAME: Record<UnderstoodPart, string> = { craft: "craft", depth: "depth", language: "answer language" };

function Part({ part, label, change }: { part: UnderstoodPart; label: string; change: UnderstoodChange }) {
  if (!change.parts.has(part)) return <span className="font-semibold text-ink-900">{label}</span>;
  return (
    <button type="button" className={PART_CLASS} aria-label={`Change the ${PART_NAME[part]}: ${label}`} onClick={() => change.onChange(part)}>
      {label}
      <ChevronDown className="h-3.5 w-3.5" aria-hidden />
    </button>
  );
}

function Joiner({ children }: { children: ReactNode }) {
  return <span className="text-ink-500">{children}</span>;
}

export function UnderstoodLine({
  understood,
  depthLabel,
  language,
  change
}: {
  understood: Understood;
  depthLabel: string | null;
  language: AnswerLanguage;
  change: UnderstoodChange;
}) {
  const crafts = understood.crafts.length > 0 ? namesLine(understood.crafts.map((craft) => craft.name)) : ANY_CRAFT;
  return (
    <p className="flex flex-wrap items-center gap-x-2 gap-y-1.5 text-sm" data-testid="understood-line">
      <Joiner>Answering for</Joiner>
      <Part part="craft" label={crafts} change={change} />
      {depthLabel ? (
        <>
          <Joiner>·</Joiner>
          <Part part="depth" label={depthLabel} change={change} />
        </>
      ) : null}
      <Joiner>· in</Joiner>
      <Part part="language" label={language.autonym} change={change} />
    </p>
  );
}
