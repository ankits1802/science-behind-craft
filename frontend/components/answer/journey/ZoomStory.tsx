"use client";

import { useRef } from "react";
import { ChevronRight } from "lucide-react";

import { useFilmScene } from "@/components/answer/FilmScene";
import { ZoomLevelView } from "@/components/answer/journey/ZoomLevelView";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { usePlayInView, type PlayInView } from "@/components/motion/usePlayInView";
import { PlayPauseButton } from "@/components/ui/PlayPauseButton";
import { StepStack } from "@/components/ui/StepStack";
import type { ZoomStoryBlock } from "@/lib/explainerPlay";
import { stepAt } from "@/lib/filmScenes";
import { ZOOM_LEVEL_LABEL, zoomBeat, zoomStatus, zoomSummary } from "@/lib/zoomView";

type Choose = ((index: number) => void) | null;

function ZoomRail({ block, at, onChoose }: { block: ZoomStoryBlock; at: number; onChoose: Choose }) {
  return (
    <ol className="flex min-w-0 flex-wrap items-center gap-1.5" aria-label="Zoom levels" data-testid="zoom-rail">
      {block.levels.map((level, index) => {
        const label = ZOOM_LEVEL_LABEL[level.level];
        return (
          <li key={level.level} className="flex items-center gap-1.5">
            {index > 0 ? <ChevronRight className="h-3.5 w-3.5 text-ink-3 rtl:-scale-x-100" aria-hidden /> : null}
            {onChoose ? (
              <button type="button" aria-pressed={index === at} onClick={() => onChoose(index)} className="kv-chip" data-testid="zoom-rail-level">
                {label}
              </button>
            ) : (
              <span aria-current={index === at ? "step" : undefined} className="kv-chip" data-testid="zoom-rail-level">
                {label}
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}

function ZoomList({ block }: { block: ZoomStoryBlock }) {
  return (
    <ol className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-8" aria-label="Zoom levels" data-testid="zoom-list">
      {block.levels.map((level, index) => (
        <li key={level.level} className="min-w-0">
          <ZoomLevelView block={block} index={index} moving />
        </li>
      ))}
    </ol>
  );
}

function ZoomStage({ block, at }: { block: ZoomStoryBlock; at: number }) {
  const steps = block.levels.map((level, index) => ({ key: level.level, node: <ZoomLevelView block={block} index={index} moving /> }));
  return <StepStack steps={steps} at={at} testId="zoom-stage" />;
}

export function ZoomStoryView({ block, reduce, play, filmed }: { block: ZoomStoryBlock; reduce: boolean; play: PlayInView; filmed: boolean }) {
  const shown = Math.min(Math.max(0, play.at), block.levels.length - 1);
  if (reduce) {
    return (
      <div className="min-w-0" data-testid="zoom-story" data-motion="none" data-level="all" role="group" aria-label={zoomSummary(block)}>
        <ZoomList block={block} />
      </div>
    );
  }
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-4" data-testid="zoom-story" data-motion="zoom" data-level={block.levels[shown].level} data-plays="view" role="group" aria-label={zoomSummary(block)}>
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
        <ZoomRail block={block} at={shown} onChoose={filmed ? null : play.choose} />
        {filmed ? null : <PlayPauseButton playing={play.playing} motion={play.motion} onToggle={play.toggle} testId="zoom-play" />}
      </div>
      <ZoomStage block={block} at={shown} />
      <p className="sr-only" role="status" aria-live={play.playing ? "off" : "polite"}>
        {zoomStatus(block, shown)}
      </p>
    </div>
  );
}

export function ZoomStory({ block }: { block: ZoomStoryBlock }) {
  const reduce = useAppReducedMotion();
  const film = useFilmScene();
  const watched = useRef<HTMLDivElement | null>(null);
  const count = block.levels.length;
  const play = usePlayInView(count, 0, watched, zoomBeat);
  const at = film ? stepAt(film.progress, count) : play.at;
  return (
    <div ref={film ? undefined : watched} className="min-w-0">
      <ZoomStoryView block={block} reduce={reduce} play={{ ...play, at }} filmed={film !== null} />
    </div>
  );
}
