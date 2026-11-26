"use client";

import { useMemo, useRef } from "react";

import { useFilmScene } from "@/components/answer/FilmScene";
import { ReactionStepList, ReactionStepRail } from "@/components/answer/matter/ReactionStepList";
import { SpeciesCast } from "@/components/answer/matter/SpeciesCast";
import { StepDetail } from "@/components/answer/matter/StepDetail";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { usePlayInView, type PlayInView } from "@/components/motion/usePlayInView";
import { PlayPauseButton } from "@/components/ui/PlayPauseButton";
import { StepStack } from "@/components/ui/StepStack";
import { reactionNotes, type ReactionPlayerBlock } from "@/lib/explainerMatter";
import { stepAt } from "@/lib/filmScenes";
import { carriedKeys, playable, reactionBeat, reactionCast, shownStep, stepPosition, stepRoles } from "@/lib/reactionPlayer";

type StageProps = { block: ReactionPlayerBlock; at: number; animate: boolean };

function PlayerControls({ play, at, count }: { play: PlayInView; at: number; count: number }) {
  return (
    <div className="flex min-w-0 flex-wrap items-center justify-between gap-x-3 gap-y-2" data-testid="reaction-controls">
      <span className="font-ui text-label text-ink-2 [font-variant-numeric:lining-nums_tabular-nums]" role="status" aria-live={play.playing ? "off" : "polite"}>
        {stepPosition(at, count)}
      </span>
      <PlayPauseButton playing={play.playing} motion={play.motion} onToggle={play.toggle} testId="reaction-play" />
    </div>
  );
}

function ReactionStage({ block, at, animate }: StageProps) {
  const cast = useMemo(() => reactionCast(block.steps), [block.steps]);
  const steps = block.steps.map((step, index) => ({
    key: step.reactionId,
    node: (
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3">
        <SpeciesCast cast={cast} roles={stepRoles(step)} carried={carriedKeys(block.steps, index)} />
        <StepDetail step={step} notes={reactionNotes(block, step.reactionId)} animate={animate && index === at} />
      </div>
    )
  }));
  return <StepStack steps={steps} at={at} testId="reaction-stage" />;
}

export function ReactionPlayerView({ block, reduce }: { block: ReactionPlayerBlock; reduce: boolean }) {
  const count = block.steps.length;
  const interactive = playable(count, reduce);
  const film = useFilmScene();
  const watched = useRef<HTMLDivElement | null>(null);
  const play = usePlayInView(count, 0, watched, reactionBeat);
  const at = film ? stepAt(film.progress, count) : shownStep(play.at, count);
  const notesFor = (step: ReactionPlayerBlock["steps"][number]) => reactionNotes(block, step.reactionId);
  return (
    <div ref={film ? undefined : watched} className="kv-figure grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3" data-testid="reaction-player" data-step={interactive ? String(at + 1) : "all"} data-plays="view">
      {interactive ? (
        <>
          {film ? null : <PlayerControls play={play} at={at} count={count} />}
          <ReactionStepRail steps={block.steps} at={at} onChoose={play.choose} />
          <ReactionStage block={block} at={at} animate={film !== null || play.motion} />
        </>
      ) : (
        <ReactionStepList steps={block.steps} notesFor={notesFor} />
      )}
    </div>
  );
}

export function ReactionPlayer({ block }: { block: ReactionPlayerBlock }) {
  const reduce = useAppReducedMotion();
  return <ReactionPlayerView block={block} reduce={reduce} />;
}
