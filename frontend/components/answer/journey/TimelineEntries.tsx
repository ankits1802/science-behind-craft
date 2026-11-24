"use client";

import { useId, type ReactNode } from "react";
import { ArrowRight } from "lucide-react";

import { PIN_DISC, READING_PROSE } from "@/components/answer/place/figureMarks";
import { CitedText } from "@/components/answer/ProseBlockView";
import type { ExplainerSentence } from "@/lib/explainerBlockBase";
import { sentenceKey } from "@/lib/sentenceGroups";
import { groupedEntries, groupState, stopLabel, yearSpanText, type PlacedPlace, type TimelineEntry, type TimelineEntryState, type TimelineSource } from "@/lib/timelineView";
import { cn } from "@/lib/utils";

export type TimelineTexts<S> = { say: (sentence: S, className: string) => ReactNode; keyOf: (sentence: S) => string; idOf: (sentence: S) => string };

export const CITED_TEXTS: TimelineTexts<ExplainerSentence> = {
  say: (sentence, className) => <CitedText id={sentence.id} sentences={[sentence]} className={className} />,
  keyOf: sentenceKey,
  idOf: (sentence) => sentence.id
};

const ENTRY_RULE: Record<TimelineEntryState, string> = {
  current: "border-s-ink-1",
  past: "border-s-transparent",
  later: "border-s-transparent"
};

type Places = Pick<TimelineSource<unknown>, "places">;

export function TimelineSlider<S>({ entries, stops, at, onChoose }: { entries: readonly TimelineEntry<S>[]; stops: readonly number[]; at: number; onChoose: (index: number) => void }) {
  const id = useId();
  const label = stopLabel(entries, stops[at]);
  return (
    <div className="grid min-w-0 gap-1" data-testid="timeline-slider">
      <div className="flex min-w-0 items-baseline justify-between gap-3">
        <label htmlFor={id} className="font-ui text-label text-ink-2">
          Year
        </label>
        <span className="font-headline text-h3 text-ink-1 [font-variant-numeric:lining-nums_tabular-nums]" data-testid="timeline-year">
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
        className="h-11 w-full min-w-0 cursor-pointer accent-indigo"
      />
      <div className="flex min-w-0 justify-between gap-3 font-ui text-caption text-ink-3 [font-variant-numeric:lining-nums_tabular-nums]" aria-hidden>
        <span>{stopLabel(entries, stops[0])}</span>
        <span>{stopLabel(entries, stops[stops.length - 1])}</span>
      </div>
    </div>
  );
}

function PlaceName({ name, pin }: { name: string; pin: number | null }) {
  return (
    <span className="inline-flex min-w-0 items-center gap-1.5">
      {pin === null ? null : (
        <span className={PIN_DISC} data-testid="timeline-entry-pin">
          <span className="sr-only">Pin </span>
          {pin}
        </span>
      )}
      <span className="min-w-0 break-words">{name}</span>
    </span>
  );
}

function EntryPlaces<S>({ block, entry, pins }: { block: Places; entry: TimelineEntry<S>; pins: ReadonlyMap<number, number> }) {
  return (
    <span className="inline-flex min-w-0 flex-wrap items-center gap-1.5 font-ui text-label text-ink-2">
      {entry.places.map((place, index) => (
        <span key={`${entry.key}:${place}`} className="inline-flex min-w-0 items-center gap-1.5">
          {index > 0 ? (
            <>
              <ArrowRight className="h-3.5 w-3.5 shrink-0 text-ink-3 rtl:-scale-x-100" aria-hidden />
              <span className="sr-only">to</span>
            </>
          ) : null}
          <PlaceName name={block.places[place]?.name ?? ""} pin={pins.get(place) ?? null} />
        </span>
      ))}
    </span>
  );
}

function EntryLine<S>({ block, entry, pins, state }: { block: Places; entry: TimelineEntry<S>; pins: ReadonlyMap<number, number>; state: TimelineEntryState }) {
  return (
    <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1" data-testid="timeline-item" data-kind={entry.kind}>
      <span className={cn("font-ui text-h4 [font-variant-numeric:lining-nums_tabular-nums]", state === "later" ? "text-ink-3" : "text-ink-1")} data-testid="timeline-years">
        {yearSpanText(entry.yearFrom, entry.yearTo)}
      </span>
      <EntryPlaces block={block} entry={entry} pins={pins} />
    </div>
  );
}

type UndatedProps<S> = { block: Places; undated: readonly { place: number | null; sentence: S }[]; placed: readonly PlacedPlace[]; texts: TimelineTexts<S> };

export function TimelineUndatedList<S>({ block, undated, placed, texts }: UndatedProps<S>) {
  const pins = new Map(placed.map((place) => [place.index, place.pin]));
  return (
    <section className="grid min-w-0 gap-2" aria-label="Without a date" data-testid="timeline-undated">
      <h4 className="kicker">Without a date</h4>
      <ul className="grid min-w-0 grid-cols-[minmax(0,1fr)] border-t border-rule">
        {undated.map((entry, at) => (
          <li key={`${texts.idOf(entry.sentence)}:${at}`} className="grid min-w-0 gap-y-1 border-b border-rule py-3" data-testid="timeline-undated-entry">
            {entry.place === null ? null : (
              <span className="font-ui text-label text-ink-2">
                <PlaceName name={block.places[entry.place]?.name ?? ""} pin={pins.get(entry.place) ?? null} />
              </span>
            )}
            {texts.say(entry.sentence, READING_PROSE)}
          </li>
        ))}
      </ul>
    </section>
  );
}

type EntriesProps<S> = { block: Places; entries: readonly TimelineEntry<S>[]; placed: readonly PlacedPlace[]; year: number; texts: TimelineTexts<S> };

export function TimelineEntries<S>({ block, entries, placed, year, texts }: EntriesProps<S>) {
  const pins = new Map(placed.map((place) => [place.index, place.pin]));
  return (
    <ol className="grid min-w-0 grid-cols-[minmax(0,1fr)] border-t border-ink-1" aria-label="Through time" data-testid="timeline-entries">
      {groupedEntries(entries, texts.keyOf).map((group) => {
        const state = groupState(group.items, year);
        return (
          <li
            key={group.key}
            aria-current={state === "current" ? "step" : undefined}
            className={cn("grid min-w-0 gap-y-1 border-b border-s-2 border-b-rule py-3 ps-3 transition-colors duration-state sm:ps-4", ENTRY_RULE[state])}
            data-testid="timeline-entry"
            data-state={state}
          >
            {group.items.map((entry) => (
              <EntryLine key={entry.key} block={block} entry={entry} pins={pins} state={state} />
            ))}
            {texts.say(group.sentence, state === "later" ? "mt-0.5 max-w-measure font-reading text-body-sm text-ink-2" : `mt-0.5 ${READING_PROSE}`)}
          </li>
        );
      })}
    </ol>
  );
}
