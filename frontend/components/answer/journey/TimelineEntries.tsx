"use client";

import { useId } from "react";
import { ArrowRight, MapPin } from "lucide-react";

import { CitedText } from "@/components/answer/ProseBlockView";
import type { TimelineMapBlock } from "@/lib/explainerPlay";
import { entryState, stopLabel, yearSpanText, type PlacedPlace, type TimelineEntry, type TimelineEntryState } from "@/lib/timelineView";
import { cn } from "@/lib/utils";

const ENTRY_TONE: Record<TimelineEntryState, string> = {
  current: "border-purple-300 bg-purple-50 dark:border-purple-800 dark:bg-purple-950/40",
  past: "border-line-200 bg-card",
  later: "border-dashed border-line-200 bg-surface-50"
};

export function TimelineSlider({ entries, stops, at, onChoose }: { entries: readonly TimelineEntry[]; stops: readonly number[]; at: number; onChoose: (index: number) => void }) {
  const id = useId();
  const label = stopLabel(entries, stops[at]);
  return (
    <div className="grid min-w-0 gap-1" data-testid="timeline-slider">
      <div className="flex min-w-0 items-baseline justify-between gap-3">
        <label htmlFor={id} className="field-label">
          Year
        </label>
        <span className="font-display text-lg font-bold tabular-nums text-ink-900" data-testid="timeline-year">
          {label}
        </span>
      </div>
      <input
        id={id}
        type="range"
        min={0}
        max={stops.length - 1}
        step={1}
        value={at}
        aria-valuetext={label}
        onChange={(event) => onChoose(Number(event.currentTarget.value))}
        className="h-11 w-full min-w-0 cursor-pointer accent-purple-700 dark:accent-purple-400"
      />
      <div className="flex min-w-0 justify-between gap-3 text-[11px] tabular-nums text-ink-500" aria-hidden>
        <span>{stopLabel(entries, stops[0])}</span>
        <span>{stopLabel(entries, stops[stops.length - 1])}</span>
      </div>
    </div>
  );
}

function PlaceName({ name, pin }: { name: string; pin: number | null }) {
  return (
    <span className="inline-flex min-w-0 items-center gap-1">
      {pin === null ? null : (
        <span className="inline-flex items-center gap-0.5 font-bold tabular-nums text-purple-700 dark:text-purple-300" data-testid="timeline-entry-pin">
          <MapPin className="h-3.5 w-3.5" aria-hidden />
          {pin}
        </span>
      )}
      <span className="min-w-0 break-words">{name}</span>
    </span>
  );
}

function EntryPlaces({ block, entry, pins }: { block: TimelineMapBlock; entry: TimelineEntry; pins: ReadonlyMap<number, number> }) {
  return (
    <span className="inline-flex min-w-0 flex-wrap items-center gap-1 text-xs font-semibold uppercase tracking-wide text-ink-500">
      {entry.places.map((place, index) => (
        <span key={`${entry.key}:${place}`} className="inline-flex min-w-0 items-center gap-1">
          {index > 0 ? (
            <>
              <ArrowRight className="h-3.5 w-3.5 shrink-0" aria-hidden />
              <span className="sr-only">to</span>
            </>
          ) : null}
          <PlaceName name={block.places[place]?.name ?? ""} pin={pins.get(place) ?? null} />
        </span>
      ))}
    </span>
  );
}

export function TimelineEntries({ block, entries, placed, year }: { block: TimelineMapBlock; entries: readonly TimelineEntry[]; placed: readonly PlacedPlace[]; year: number }) {
  const pins = new Map(placed.map((place) => [place.index, place.pin]));
  return (
    <ol className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-2.5" aria-label="Through time" data-testid="timeline-entries">
      {entries.map((entry) => {
        const state = entryState(entry, year);
        return (
          <li key={entry.key} className={cn("min-w-0 rounded-lg border p-3 transition-colors sm:p-4", ENTRY_TONE[state])} data-testid="timeline-entry" data-kind={entry.kind} data-state={state}>
            <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
              <span className="font-display text-sm font-bold tabular-nums text-ink-900" data-testid="timeline-years">
                {yearSpanText(entry.yearFrom, entry.yearTo)}
              </span>
              <EntryPlaces block={block} entry={entry} pins={pins} />
            </div>
            <CitedText id={entry.sentence.id} sentences={[entry.sentence]} className="mt-1.5 text-sm leading-7 text-ink-700" />
          </li>
        );
      })}
    </ol>
  );
}
