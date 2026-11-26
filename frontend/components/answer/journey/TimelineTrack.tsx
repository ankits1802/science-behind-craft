"use client";

import type { KeyboardEvent, ReactNode } from "react";

import type { PlayInView } from "@/components/motion/usePlayInView";
import { PlayPauseButton } from "@/components/ui/PlayPauseButton";
import { spreadPositions } from "@/lib/timelinePlay";
import { cn } from "@/lib/utils";

export type TrackPoint = { key: string; position: number; name: string; shown: ReactNode };

type TrackProps = { points: readonly TrackPoint[]; play: PlayInView; label: string; first: string; last: string };

const SPACE = " ";

function spaceToggles(toggle: () => void) {
  return (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key !== SPACE) return;
    event.preventDefault();
    if (event.type === "keydown") toggle();
  };
}

function Points({ points, play, label }: Omit<TrackProps, "first" | "last">) {
  const placed = spreadPositions(points.map((point) => point.position));
  const onSpace = spaceToggles(play.toggle);
  return (
    <div className="relative h-11 min-w-0" role="group" aria-label={label} data-testid="timeline-points">
      <span className="absolute inset-x-0 top-1/2 h-px bg-ink-1" aria-hidden />
      {points.map((point, index) => {
        const current = index === play.at;
        return (
          <button
            key={point.key}
            type="button"
            className="absolute top-1/2 -ms-3 grid size-6 -translate-y-1/2 place-items-center rounded-full"
            style={{ insetInlineStart: `${placed[index]}%` }}
            aria-pressed={current}
            aria-label={point.name}
            onClick={() => play.choose(index)}
            onKeyDown={onSpace}
            onKeyUp={onSpace}
            data-testid="timeline-point"
          >
            <span className={cn("block size-2.5 rounded-full border transition-colors duration-state", current ? "border-indigo bg-indigo" : "border-ink-2 bg-raised")} aria-hidden />
          </button>
        );
      })}
    </div>
  );
}

export function TimelineTrack({ points, play, label, first, last }: TrackProps) {
  const shown = points[play.at] ?? points[points.length - 1];
  return (
    <div className="grid min-w-0 gap-1" data-testid="timeline-track">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
        <p className="min-w-0 font-headline text-h3 text-ink-1 [font-variant-numeric:lining-nums_tabular-nums]" data-testid="timeline-year">
          {shown?.shown}
        </p>
        <PlayPauseButton playing={play.playing} motion={play.motion} onToggle={play.toggle} testId="timeline-play" />
      </div>
      <Points points={points} play={play} label={label} />
      <div className="flex min-w-0 justify-between gap-3 font-ui text-caption text-ink-3 [font-variant-numeric:lining-nums_tabular-nums]" aria-hidden>
        <span>{first}</span>
        <span>{last}</span>
      </div>
      <p className="sr-only" role="status" aria-live={play.playing ? "off" : "polite"}>
        {shown?.name}
      </p>
    </div>
  );
}
