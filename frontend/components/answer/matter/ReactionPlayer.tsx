"use client";

import { useMemo } from "react";
import { Pause, Play, RotateCcw, SkipBack, SkipForward } from "lucide-react";

import { useFilmScene } from "@/components/answer/FilmScene";
import { ReactionStepList } from "@/components/answer/matter/ReactionStepList";
import { SpeciesCast } from "@/components/answer/matter/SpeciesCast";
import { usePlayback, type PlaybackControls } from "@/components/answer/matter/usePlayback";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { reactionNotes, type ReactionPlayerBlock, type ReactionStep } from "@/lib/explainerMatter";
import { stepAt } from "@/lib/filmScenes";
import { carriedKeys, playable, reactionCast, stepPosition, stepRoles } from "@/lib/reactionPlayer";

const ROUND_BUTTON = "field-button-secondary h-10 w-10 shrink-0 rounded-full p-0 pointer-coarse:h-11 pointer-coarse:w-11";

function PlayButton({ playback, atEnd }: { playback: PlaybackControls; atEnd: boolean }) {
  if (playback.playing) {
    return (
      <button type="button" className="field-button min-w-28 rounded-full" onClick={() => playback.send({ type: "pause" })} data-testid="reaction-pause">
        <Pause className="h-4 w-4" aria-hidden />
        Pause
      </button>
    );
  }
  return (
    <button type="button" className="field-button min-w-28 rounded-full" onClick={() => playback.send({ type: "play" })} data-testid="reaction-play">
      {atEnd ? <RotateCcw className="h-4 w-4" aria-hidden /> : <Play className="h-4 w-4" aria-hidden />}
      {atEnd ? "Replay" : "Play"}
    </button>
  );
}

function PlayerControls({ playback, count }: { playback: PlaybackControls; count: number }) {
  const atEnd = playback.at >= count - 1;
  return (
    <div className="flex min-w-0 flex-wrap items-center justify-between gap-x-3 gap-y-2" data-testid="reaction-controls">
      <span className="text-sm font-semibold tabular-nums text-ink-700" aria-live="polite">
        {stepPosition(playback.at, count)}
      </span>
      <div role="toolbar" aria-label="Reaction playback" className="flex items-center gap-1.5">
        <button type="button" className={ROUND_BUTTON} onClick={() => playback.send({ type: "previous" })} disabled={playback.at === 0} aria-label="Previous step">
          <SkipBack className="h-4 w-4" aria-hidden />
        </button>
        <PlayButton playback={playback} atEnd={atEnd} />
        <button type="button" className={ROUND_BUTTON} onClick={() => playback.send({ type: "next" })} disabled={atEnd} aria-label="Next step">
          <SkipForward className="h-4 w-4" aria-hidden />
        </button>
      </div>
    </div>
  );
}

export function ReactionPlayerView({ block, reduce }: { block: ReactionPlayerBlock; reduce: boolean }) {
  const count = block.steps.length;
  const interactive = playable(count, reduce);
  const film = useFilmScene();
  const playback = usePlayback(count, interactive && film === null);
  const cast = useMemo(() => reactionCast(block.steps), [block.steps]);
  const at = film ? stepAt(film.progress, count) : playback.at;
  const open = interactive ? at : null;
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-3" data-testid="reaction-player" data-step={open === null ? "all" : String(open + 1)}>
      {interactive ? (
        <>
          <SpeciesCast cast={cast} roles={stepRoles(block.steps[at] ?? null)} carried={carriedKeys(block.steps, at)} />
          {film ? null : <PlayerControls playback={playback} count={count} />}
        </>
      ) : null}
      <ReactionStepList
        steps={block.steps}
        open={open}
        reduce={reduce}
        onChoose={(index) => playback.send({ type: "choose", index })}
        notesFor={(step: ReactionStep) => reactionNotes(block, step.reactionId)}
      />
    </div>
  );
}

export function ReactionPlayer({ block }: { block: ReactionPlayerBlock }) {
  const reduce = useAppReducedMotion();
  return <ReactionPlayerView block={block} reduce={reduce} />;
}
