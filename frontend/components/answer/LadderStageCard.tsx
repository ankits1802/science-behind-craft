"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { CitationChips } from "@/components/answer/CitationContext";
import { EvidenceLevelBadge } from "@/components/answer/EvidenceBadge";
import { ExplainerSentence } from "@/components/answer/ExplainerSentence";
import type { CraftLink } from "@/lib/answerShapes";
import type { LadderStage } from "@/lib/explainerContract";
import { MATERIAL_KIND_LABEL, MATERIAL_ROLE_LABEL, STAGE_TYPE_LABEL } from "@/lib/processView";
import { cn } from "@/lib/utils";

function StageFacts({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-3">
      <h4 className="field-label mb-1.5">{title}</h4>
      <ul className="grid gap-1.5 text-sm leading-6 text-ink-700">{children}</ul>
    </section>
  );
}

function materialRole(material: LadderStage["materials"][number]): string {
  const role = MATERIAL_ROLE_LABEL[material.role];
  const kind = MATERIAL_KIND_LABEL[material.kind];
  return role === kind ? role : `${role} · ${kind}`;
}

function reactionLabel(count: number): string {
  return count === 1 ? "See the reaction" : `See the ${count} reactions`;
}

export function LadderStageCard({ stage, craft, reached }: { stage: LadderStage; craft: CraftLink; reached: boolean }) {
  return (
    <li className="grid grid-cols-[var(--rail)_minmax(0,1fr)] gap-x-3 sm:gap-x-4" data-testid="ladder-stage" data-reached={reached ? "true" : "false"}>
      <span
        aria-hidden
        className={cn(
          "relative z-10 mt-3 grid h-10 w-10 place-items-center justify-self-center rounded-full font-display text-sm font-bold tabular-nums transition-colors duration-300",
          reached ? "bg-purple-700 text-white ring-4 ring-purple-100 dark:ring-purple-950" : "bg-card text-ink-500 ring-2 ring-line-200"
        )}
      >
        {stage.ordinal}
      </span>
      <div className={cn("min-w-0 rounded-lg border p-3.5 transition-colors duration-300 sm:p-4 md:p-5", reached ? "border-purple-200 bg-card dark:border-purple-900" : "border-line-200 bg-card")}>
        <header className="flex flex-wrap items-start justify-between gap-x-3 gap-y-1.5">
          <h3 className="min-w-0 break-words font-display text-base font-bold text-ink-900 md:text-lg">
            <span className="sr-only">Step {stage.ordinal}: </span>
            {stage.name}
          </h3>
          <span className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-medium text-ink-500">{STAGE_TYPE_LABEL[stage.stageType]}</span>
            <EvidenceLevelBadge level={stage.level} />
          </span>
        </header>
        <p className="mt-2 text-[15px] leading-7 text-ink-700">
          {stage.sentences.map((sentence) => (
            <ExplainerSentence key={sentence.id} sentence={sentence} />
          ))}
        </p>
        {stage.materials.length > 0 ? (
          <StageFacts title="Materials">
            {stage.materials.map((material) => (
              <li key={material.materialId}>
                <span className="font-medium text-ink-900">{material.name}</span>
                <span className="text-ink-500"> · {materialRole(material)}</span>
                <CitationChips citations={material.citations} />
              </li>
            ))}
          </StageFacts>
        ) : null}
        {stage.conditions.length > 0 ? (
          <StageFacts title="Conditions">
            {stage.conditions.map((condition, index) => (
              <li key={`${condition.label}:${index}`} data-testid="ladder-condition">
                <span className="font-medium text-ink-900">{condition.label}</span>
                <span>: {condition.stated}</span>
                <CitationChips citations={condition.citations} />
              </li>
            ))}
          </StageFacts>
        ) : null}
        {stage.reactionIds.length > 0 ? (
          <Link href={`${craft.path}?tab=process`} className="mt-3 inline-flex min-h-9 items-center gap-1 text-sm font-semibold text-purple-700 hover:underline dark:text-purple-300">
            {reactionLabel(stage.reactionIds.length)}
            <ArrowRight className="h-3.5 w-3.5" aria-hidden />
          </Link>
        ) : null}
      </div>
    </li>
  );
}
