"use client";

import { Loader2, Pause, Play, RotateCw, X } from "lucide-react";

import { ListenAudio } from "@/components/answer/ListenAudio";
import type { Listen } from "@/components/answer/useListen";
import { ProgressBar } from "@/components/ui/ProgressBar";
import type { AnswerLanguage } from "@/lib/answerLanguages";
import { formatClock } from "@/lib/format";
import { elapsedOf, scriptDuration } from "@/lib/listen";

const ROUND_BUTTON = "grid h-12 w-12 shrink-0 place-items-center rounded-full bg-purple-700 text-white transition hover:bg-purple-800 disabled:bg-line-200 disabled:text-ink-500";
const SMALL_BUTTON =
  "inline-flex min-h-9 items-center justify-center rounded-full border border-line-200 bg-card px-3 text-xs font-semibold text-ink-900 transition hover:border-purple-300 pointer-coarse:min-h-11";

function Timing({ listen }: { listen: Listen }) {
  if (!listen.script) return null;
  const total = scriptDuration(listen.script);
  const elapsed = Math.min(total, elapsedOf(listen.script, listen.position));
  const percent = total > 0 ? Math.round((elapsed / total) * 100) : 0;
  return (
    <div className="grid min-w-0 flex-1 gap-1.5">
      <ProgressBar percent={percent} role="progressbar" aria-label="Played" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} className="h-1.5" />
      <span className="text-xs tabular-nums text-ink-500">
        {formatClock(elapsed)} of {formatClock(total)}
      </span>
    </div>
  );
}

export function ListenDock({ listen, language }: { listen: Listen; language: AnswerLanguage }) {
  if (listen.status === "idle") return null;
  const track = listen.script?.tracks[listen.position.track] ?? null;
  const playing = listen.status === "playing";
  return (
    <aside
      aria-label="Listen"
      className="panel fixed inset-x-3 bottom-[calc(var(--bottom-nav-h,0px)+0.75rem)] z-40 grid gap-2 p-3 shadow-lg sm:left-auto sm:right-6 sm:w-[26rem] lg:bottom-6"
      data-testid="listen-dock"
      data-status={listen.status}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="field-label" lang={language.code}>
          Listen · {language.autonym}
        </span>
        <button type="button" className="-m-1 rounded-md p-1 text-ink-500 transition hover:text-ink-900" aria-label="Stop listening" onClick={listen.stop}>
          <X className="h-4 w-4" aria-hidden />
        </button>
      </div>
      {listen.status === "failed" ? (
        <div role="alert" className="flex flex-wrap items-center gap-3 text-sm text-error-600">
          <span className="min-w-0 flex-1">{listen.error}</span>
          <button type="button" className={SMALL_BUTTON} onClick={listen.start}>
            <RotateCw className="mr-1 h-3.5 w-3.5" aria-hidden />
            Try again
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-3">
          <button type="button" className={ROUND_BUTTON} aria-label={playing ? "Pause" : "Play"} disabled={listen.status === "loading"} onClick={listen.toggle}>
            {listen.status === "loading" ? (
              <Loader2 className="h-5 w-5 animate-spin motion-reduce:animate-none" aria-hidden />
            ) : playing ? (
              <Pause className="h-5 w-5" aria-hidden />
            ) : (
              <Play className="h-5 w-5" aria-hidden />
            )}
          </button>
          {listen.status === "loading" ? <span className="flex-1 text-sm text-ink-500">Preparing the audio…</span> : <Timing listen={listen} />}
          <button type="button" className={SMALL_BUTTON} aria-label={`Speed ${listen.rate} times`} onClick={listen.cycleRate}>
            {listen.rate}×
          </button>
        </div>
      )}
      {track ? (
        <ListenAudio
          key={listen.position.track}
          src={track.audioUrl}
          playing={listen.status === "playing"}
          rate={listen.rate}
          onTime={listen.onTime}
          onEnded={listen.onEnded}
          onBroken={listen.onBroken}
          onRefused={listen.onRefused}
        />
      ) : null}
    </aside>
  );
}
