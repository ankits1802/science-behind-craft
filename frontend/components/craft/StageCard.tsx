"use client";

import type { ReactNode } from "react";

import { EvidenceLevelBadge } from "@/components/answer/EvidenceBadge";
import { ClaimList } from "@/components/craft/ClaimList";
import { ConditionList } from "@/components/craft/ConditionList";
import { ReactionCard } from "@/components/craft/ReactionCard";
import { StageMaterials } from "@/components/craft/StageMaterials";
import { STAGE_TYPE_LABEL } from "@/lib/processView";
import type { ProcessStageView } from "@/lib/scienceContract";

export function StageCard({ stage, position }: { stage: ProcessStageView; position: number }) {
  return (
    <div className="grid grid-cols-[var(--rail)_minmax(0,1fr)] gap-x-4">
      <span aria-hidden className="grid h-8 w-8 place-items-center justify-self-center rounded-full bg-purple-700 font-display text-sm font-bold text-white">
        {position}
      </span>
      <div className="min-w-0">
        <header className="flex flex-wrap items-start justify-between gap-x-3 gap-y-1.5">
          <h3 className="min-w-0 font-display text-base font-bold text-ink-900">
            <span className="sr-only">Step {position}: </span>
            {stage.name}
          </h3>
          <span className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-medium text-ink-500">{STAGE_TYPE_LABEL[stage.stageType]}</span>
            <EvidenceLevelBadge level={stage.level} />
          </span>
        </header>
        {stage.claims.length > 0 ? (
          <div className="mt-2">
            <ClaimList claims={stage.claims} />
          </div>
        ) : null}
        {stage.materials.length > 0 ? (
          <StagePart title="Materials">
            <StageMaterials materials={stage.materials} />
          </StagePart>
        ) : null}
        {stage.conditions.length > 0 ? (
          <StagePart title="Conditions">
            <ConditionList conditions={stage.conditions} />
          </StagePart>
        ) : null}
        {stage.reactions.length > 0 ? (
          <StagePart title="Reactions">
            <div className="grid gap-2">
              {stage.reactions.map((reaction) => (
                <ReactionCard key={reaction.id} reaction={reaction} />
              ))}
            </div>
          </StagePart>
        ) : null}
      </div>
    </div>
  );
}

function StagePart({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-4">
      <h4 className="field-label mb-2">{title}</h4>
      {children}
    </section>
  );
}
