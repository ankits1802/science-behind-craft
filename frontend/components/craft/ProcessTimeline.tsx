"use client";

import type { ReactNode } from "react";
import { motion } from "framer-motion";

import { NoSourceFound } from "@/components/craft/ClaimList";
import { StageCard } from "@/components/craft/StageCard";
import { riseItem, staggerParent } from "@/components/guide/guideMotion";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { shownVariants } from "@/lib/processView";
import type { CraftProcess, ProcessStageView } from "@/lib/scienceContract";

export type StageRows = {
  register: (stageId: string) => (node: HTMLElement | null) => void;
  flashKey: string | null;
};

export type StageMediaSlot = (stage: ProcessStageView) => ReactNode;

export function ProcessTimeline({ process, rows, stageMedia }: { process: CraftProcess; rows?: StageRows; stageMedia?: StageMediaSlot }) {
  const reduce = useAppReducedMotion();
  const variants = shownVariants(process);

  if (variants.length === 0) {
    return (
      <div className="panel p-5">
        <NoSourceFound />
      </div>
    );
  }

  return (
    <div className="grid gap-8">
      {variants.map((variant) => (
        <section key={variant.id} aria-label={variants.length > 1 ? variant.name : "Process steps"}>
          {variants.length > 1 ? <h2 className="mb-3 font-display text-lg font-bold text-ink-900">{variant.name}</h2> : null}
          <div className="relative isolate">
            <span aria-hidden className="pointer-events-none absolute inset-y-8 left-[calc(2rem-1px)] -z-10 w-0.5 rounded-full bg-progress-track md:left-[calc(2.25rem-1px)]" />
            <motion.ol variants={staggerParent(reduce)} initial="hidden" animate="show" className="grid gap-3 [--rail:2rem]">
              {variant.stages.map((stage, index) => (
                <motion.li
                  key={stage.id}
                  ref={rows?.register(stage.id)}
                  variants={riseItem(reduce)}
                  data-flash={rows?.flashKey === stage.id ? "true" : undefined}
                  className="fr-flash-row panel scroll-mt-28 p-4 md:p-5"
                  data-testid="process-stage"
                >
                  <StageCard stage={stage} position={index + 1} />
                  {stageMedia?.(stage)}
                </motion.li>
              ))}
            </motion.ol>
          </div>
        </section>
      ))}
    </div>
  );
}
