"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronRight, ZoomIn, ZoomOut } from "lucide-react";

import { useFilmScene } from "@/components/answer/FilmScene";
import { ZoomLevelView } from "@/components/answer/journey/ZoomLevelView";
import { zoomThrough } from "@/components/guide/guideMotion";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { ActionGroup } from "@/components/ui/ActionGroup";
import type { ZoomStoryBlock } from "@/lib/explainerPlay";
import { stepAt } from "@/lib/filmScenes";
import { cn } from "@/lib/utils";
import { ZOOM_LEVEL_LABEL, zoomSummary } from "@/lib/zoomView";

const STEP_PILL = "inline-flex min-h-9 items-center rounded-full border px-3 text-xs font-semibold transition-colors pointer-coarse:min-h-11";
const STEP_TONE = {
  on: "border-purple-700 bg-purple-700 text-white",
  passed: "border-purple-300 bg-purple-50 text-purple-700 dark:border-purple-800 dark:bg-purple-950/40 dark:text-purple-200",
  resting: "border-line-200 bg-card text-ink-700 hover:border-purple-300"
} as const;

type Choose = ((index: number) => void) | null;

function ZoomRail({ block, at, onChoose }: { block: ZoomStoryBlock; at: number; onChoose: Choose }) {
  return (
    <ol className="flex min-w-0 flex-wrap items-center gap-1.5" aria-label="Zoom levels" data-testid="zoom-rail">
      {block.levels.map((level, index) => {
        const tone = STEP_TONE[index === at ? "on" : index < at ? "passed" : "resting"];
        const label = ZOOM_LEVEL_LABEL[level.level];
        return (
          <li key={level.level} className="flex items-center gap-1.5">
            {index > 0 ? <ChevronRight className="h-3.5 w-3.5 text-ink-300" aria-hidden /> : null}
            {onChoose ? (
              <button type="button" aria-pressed={index === at} onClick={() => onChoose(index)} className={cn(STEP_PILL, tone)} data-testid="zoom-rail-level">
                {label}
              </button>
            ) : (
              <span aria-current={index === at ? "step" : undefined} className={cn(STEP_PILL, tone)} data-testid="zoom-rail-level">
                {label}
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}

function ZoomSteps({ at, count, onChoose }: { at: number; count: number; onChoose: (index: number) => void }) {
  return (
    <ActionGroup align="start">
      <button type="button" className="field-button-secondary" disabled={at === 0} onClick={() => onChoose(at - 1)}>
        <ZoomOut className="h-4 w-4" aria-hidden />
        Zoom out
      </button>
      <button type="button" className="field-button" disabled={at >= count - 1} onClick={() => onChoose(at + 1)}>
        <ZoomIn className="h-4 w-4" aria-hidden />
        Zoom in
      </button>
    </ActionGroup>
  );
}

function ZoomList({ block }: { block: ZoomStoryBlock }) {
  return (
    <ol className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-6" aria-label="Zoom levels" data-testid="zoom-list">
      {block.levels.map((level, index) => (
        <li key={level.level} className="min-w-0">
          <ZoomLevelView block={block} index={index} moving={false} />
        </li>
      ))}
    </ol>
  );
}

export function ZoomStoryView({ block, reduce, at, onChoose }: { block: ZoomStoryBlock; reduce: boolean; at: number; onChoose: Choose }) {
  const shown = Math.min(Math.max(0, at), block.levels.length - 1);
  if (reduce) {
    return (
      <div className="min-w-0" data-testid="zoom-story" data-motion="none" data-level="all" role="group" aria-label={zoomSummary(block)}>
        <ZoomList block={block} />
      </div>
    );
  }
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-4" data-testid="zoom-story" data-motion="zoom" data-level={block.levels[shown].level} role="group" aria-label={zoomSummary(block)}>
      <ZoomRail block={block} at={shown} onChoose={onChoose} />
      <div className="min-w-0" aria-live="polite">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div key={block.levels[shown].level} variants={zoomThrough(false)} initial="hidden" animate="show" exit="exit" className="min-w-0">
            <ZoomLevelView block={block} index={shown} moving />
          </motion.div>
        </AnimatePresence>
      </div>
      {onChoose ? <ZoomSteps at={shown} count={block.levels.length} onChoose={onChoose} /> : null}
    </div>
  );
}

export function ZoomStory({ block }: { block: ZoomStoryBlock }) {
  const reduce = useAppReducedMotion();
  const film = useFilmScene();
  const [chosen, setChosen] = useState(0);
  const at = film ? stepAt(film.progress, block.levels.length) : chosen;
  return <ZoomStoryView block={block} reduce={reduce} at={at} onChoose={film ? null : setChosen} />;
}
