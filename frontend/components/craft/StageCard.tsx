"use client";

import type { ReactNode } from "react";

import { ClaimList } from "@/components/craft/ClaimList";
import { ClaimChips, usePageClaims } from "@/components/craft/CraftClaims";
import { CraftPictures } from "@/components/craft/CraftPictures";
import { ReactionCard } from "@/components/craft/ReactionCard";
import { StageMaterials } from "@/components/craft/StageMaterials";
import type { PagePicture, PageStage, StageTiming } from "@/lib/craftPageContract";
import { TIMING_LABEL } from "@/lib/craftPageView";
import { STAGE_TYPE_LABEL } from "@/lib/processView";

function StageMark({ order }: { order: number | null }) {
  if (order === null) return <span aria-hidden className="mt-1.5 h-3.5 w-3.5 justify-self-center rounded-full border-2 border-purple-300 bg-card dark:border-purple-500" />;
  return (
    <span aria-hidden className="grid h-8 w-8 place-items-center justify-self-center rounded-full bg-sunk font-ui text-ui font-semibold tabular-nums text-ink-1">
      {order}
    </span>
  );
}

function TimingList({ timing }: { timing: readonly StageTiming[] }) {
  return (
    <dl className="grid gap-1.5">
      {timing.map((entry) => (
        <div key={`${entry.kind}:${entry.claimId}`} className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-sm" data-testid="process-timing">
          <dt className="field-label">{TIMING_LABEL[entry.kind]}</dt>
          <dd className="min-w-0 text-ink-900 [overflow-wrap:anywhere]">
            {entry.text}
            <ClaimChips ids={[entry.claimId]} />
          </dd>
        </div>
      ))}
    </dl>
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

export function StageCard({ stage, pictures }: { stage: PageStage; pictures: readonly PagePicture[] }) {
  const claims = usePageClaims(stage.claimIds);
  return (
    <div className="grid grid-cols-[2rem_minmax(0,1fr)] gap-x-4">
      <StageMark order={stage.order} />
      <div className="min-w-0">
        <header className="flex flex-wrap items-start justify-between gap-x-3 gap-y-1.5">
          <h3 className="min-w-0 font-display text-base font-bold text-ink-900 [overflow-wrap:anywhere]">
            {stage.order !== null ? <span className="sr-only">Step {stage.order}: </span> : null}
            {stage.name}
            {stage.localName ? <span className="ml-2 text-sm font-medium italic text-ink-500">{stage.localName}</span> : null}
          </h3>
          <span className="text-xs font-medium text-ink-500">{STAGE_TYPE_LABEL[stage.stageType]}</span>
        </header>
        <div className="mt-2">
          <ClaimList claims={claims} />
        </div>
        {stage.materials.length > 0 ? (
          <StagePart title="Materials">
            <StageMaterials items={stage.materials} testId="process-material" />
          </StagePart>
        ) : null}
        {stage.tools.length > 0 ? (
          <StagePart title="Tools">
            <StageMaterials items={stage.tools} testId="process-tool" />
          </StagePart>
        ) : null}
        {stage.timing.length > 0 ? (
          <StagePart title="Timing">
            <TimingList timing={stage.timing} />
          </StagePart>
        ) : null}
        {stage.reactions.length > 0 ? (
          <StagePart title="Chemistry">
            <div className="grid grid-cols-1 gap-2">
              {stage.reactions.map((reaction) => (
                <ReactionCard key={reaction.id ?? reaction.label} reaction={reaction} />
              ))}
            </div>
          </StagePart>
        ) : null}
        {pictures.length > 0 ? (
          <StagePart title="Pictures">
            <CraftPictures pictures={pictures} layout="stage" />
          </StagePart>
        ) : null}
      </div>
    </div>
  );
}
