"use client";

import type { RefObject } from "react";
import { Loader2, Pause, Play, RotateCcw, SkipBack, SkipForward, Volume2, VolumeX } from "lucide-react";

import type { Film } from "@/components/answer/film/useFilm";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { scenePosition } from "@/lib/filmScenes";
import { formatClock } from "@/lib/format";

const ROUND = "field-button-secondary h-11 w-11 shrink-0 rounded-full p-0";
const MAIN = "grid h-14 w-14 shrink-0 place-items-center rounded-full bg-purple-700 text-white transition hover:bg-purple-800 aria-disabled:cursor-wait aria-disabled:bg-line-200 aria-disabled:text-ink-500";

function MainButton({ film, playRef }: { film: Film; playRef: RefObject<HTMLButtonElement | null> }) {
  const { clock } = film;
  const loading = film.load === "loading";
  const label = clock.ended ? "Play again" : clock.playing ? "Pause" : "Play";
  return (
    <button ref={playRef} type="button" className={MAIN} aria-label={label} aria-disabled={film.load !== "ready" || undefined} onClick={() => film.send({ type: "toggle" })} data-testid="film-play">
      {loading ? (
        <Loader2 className="h-6 w-6 animate-spin motion-reduce:animate-none" aria-hidden />
      ) : clock.ended ? (
        <RotateCcw className="h-6 w-6" aria-hidden />
      ) : clock.playing ? (
        <Pause className="h-6 w-6" aria-hidden />
      ) : (
        <Play className="h-6 w-6" aria-hidden />
      )}
    </button>
  );
}

export function FilmTiming({ film }: { film: Film }) {
  const percent = film.total > 0 ? Math.round((Math.min(film.elapsed, film.total) / film.total) * 100) : 0;
  return (
    <div className="grid min-w-0 gap-1.5" data-testid="film-timing">
      <ProgressBar percent={percent} role="progressbar" aria-label="Played" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} className="h-1.5" />
      <div className="flex min-w-0 justify-between gap-3 text-xs tabular-nums text-ink-500">
        <span>{film.scenes.length > 0 ? scenePosition(film.clock.scene, film.scenes.length) : null}</span>
        <span>
          {formatClock(film.elapsed)} of {formatClock(film.total)}
        </span>
      </div>
    </div>
  );
}

export function FilmButtons({ film, muted, onMute, playRef }: { film: Film; muted: boolean; onMute: () => void; playRef: RefObject<HTMLButtonElement | null> }) {
  const ready = film.load === "ready";
  return (
    <div className="flex min-w-0 items-center justify-center gap-3" role="toolbar" aria-label="Film" data-testid="film-buttons">
      <button type="button" className={ROUND} aria-label="Previous scene" disabled={!ready} onClick={() => film.send({ type: "previous" })}>
        <SkipBack className="h-4 w-4" aria-hidden />
      </button>
      <MainButton film={film} playRef={playRef} />
      <button type="button" className={ROUND} aria-label="Next scene" disabled={!ready || film.clock.ended} onClick={() => film.send({ type: "next" })}>
        <SkipForward className="h-4 w-4" aria-hidden />
      </button>
      <button type="button" className={ROUND} aria-label="Mute" aria-pressed={muted} onClick={onMute} data-testid="film-mute">
        {muted ? <VolumeX className="h-4 w-4" aria-hidden /> : <Volume2 className="h-4 w-4" aria-hidden />}
      </button>
    </div>
  );
}
