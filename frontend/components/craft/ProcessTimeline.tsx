"use client";

import { motion } from "framer-motion";

import { ContributedPlates } from "@/components/craft/ContributedPlates";
import { ReactionCard } from "@/components/craft/ReactionCard";
import { StageCard } from "@/components/craft/StageCard";
import { riseItem, staggerParent } from "@/components/guide/guideMotion";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { NO_CONTRIBUTIONS, NO_PLATES, type ContributedPlacement, type ContributedPlate } from "@/lib/craftContributed";
import type { PagePicture, PageProcess, PageStage } from "@/lib/craftPageContract";
import { stageGroups, stagePictures } from "@/lib/craftPageView";

export type StageRows = {
  register: (stageId: string) => (node: HTMLElement | null) => void;
  flashKey: string | null;
};

type StagePlates = ReadonlyMap<string, readonly ContributedPlate[]>;
type StageListProps = { stages: readonly PageStage[]; ordered: boolean; pictures: readonly PagePicture[]; plates: StagePlates; rows?: StageRows };

function StageList({ stages, ordered, pictures, plates, rows }: StageListProps) {
  const reduce = useAppReducedMotion();
  const List = ordered ? motion.ol : motion.ul;
  return (
    <div className="relative isolate">
      {ordered ? <span aria-hidden className="pointer-events-none absolute inset-y-8 left-[calc(2rem-1px)] -z-10 w-0.5 rounded-full bg-progress-track md:left-[calc(2.25rem-1px)]" /> : null}
      <List variants={staggerParent(reduce)} initial="hidden" animate="show" className="grid gap-3">
        {stages.map((stage) => (
          <motion.li
            key={stage.id}
            ref={rows?.register(stage.id)}
            variants={riseItem(reduce)}
            data-flash={rows?.flashKey === stage.id ? "true" : undefined}
            className="fr-flash-row panel scroll-mt-28 p-4 md:p-5"
            data-testid="process-stage"
            data-ordered={ordered ? "true" : "false"}
          >
            <StageCard stage={stage} pictures={stagePictures(pictures, stage.id)} contributed={plates.get(stage.id) ?? NO_PLATES} />
          </motion.li>
        ))}
      </List>
    </div>
  );
}

type TimelineProps = { process: PageProcess; pictures: readonly PagePicture[]; rows?: StageRows; contributed?: ContributedPlacement };

export function ProcessTimeline({ process, pictures, rows, contributed = NO_CONTRIBUTIONS }: TimelineProps) {
  const { numbered, unnumbered } = stageGroups(process.stages);
  return (
    <div className="grid gap-8" data-testid="process-timeline">
      {numbered.length > 0 ? (
        <section aria-label="Steps in order">
          <StageList stages={numbered} ordered pictures={pictures} plates={contributed.stages} rows={rows} />
        </section>
      ) : null}
      {unnumbered.length > 0 ? (
        <section aria-labelledby="process-unordered-heading" data-testid="process-unordered">
          <h2 id="process-unordered-heading" className="font-display text-lg font-bold text-ink-900">
            {numbered.length > 0 ? "Other stages" : "Stages"}
          </h2>
          <p className="mb-3 mt-1 text-sm text-ink-500">The sources don&apos;t place these in the sequence.</p>
          <StageList stages={unnumbered} ordered={false} pictures={pictures} plates={contributed.stages} rows={rows} />
        </section>
      ) : null}
      <ContributedPlates plates={contributed.tabs.process} />
      {process.reactions.length > 0 ? (
        <section aria-labelledby="process-reactions-heading" data-testid="process-reactions">
          <h2 id="process-reactions-heading" className="mb-3 font-display text-lg font-bold text-ink-900">
            Chemistry
          </h2>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {process.reactions.map((reaction) => (
              <ReactionCard key={reaction.id ?? reaction.label} reaction={reaction} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
