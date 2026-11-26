"use client";

import { useMemo, useState, type ReactNode } from "react";

import { useFilmScene } from "@/components/answer/FilmScene";
import { CITED_TEXTS, TimelineEntries, TimelineSlider, TimelineUndatedList, type TimelineTexts } from "@/components/answer/journey/TimelineEntries";
import { TimelinePins, type TimelineMapParts } from "@/components/answer/journey/TimelinePins";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { INDIA_BOUNDS } from "@/components/map/indiaBounds";
import type { TimelineMapBlock } from "@/lib/explainerPlay";
import { sceneStep } from "@/lib/filmScenes";
import { boundaryNote } from "@/lib/placeView";
import type { BoundaryNote } from "@/lib/regionContract";
import { placedPlaces, reachedPlaces, routeLines, timelineEntries, timelineStops, timelineSummary, type Placeable, type TimelineEntry, type TimelineSource } from "@/lib/timelineView";

const WITH_MAP = "grid min-w-0 grid-cols-[minmax(0,1fr)] gap-5 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] lg:items-start";
const WITHOUT_MAP = "grid min-w-0 grid-cols-[minmax(0,1fr)] gap-4";

export type TimelineControl<S> = (props: { entries: readonly TimelineEntry<S>[]; stops: readonly number[]; at: number; onChoose: (index: number) => void }) => ReactNode;
export type TimelineMapDrawing<S> = { texts: TimelineTexts<S>; boundary: BoundaryNote | null; placeable?: Placeable; pinUndated?: boolean; parts?: TimelineMapParts; control?: TimelineControl<S> };
type FrameProps<S> = { source: TimelineSource<S>; at: number; onChoose: (index: number) => void; drawing: TimelineMapDrawing<S> };

function undatedPlaces<S>(source: TimelineSource<S>): number[] {
  return (source.undated ?? []).flatMap((entry) => (entry.place === null ? [] : [entry.place]));
}

export function TimelineMapFrame<S>({ source, at, onChoose, drawing }: FrameProps<S>) {
  const entries = useMemo(() => timelineEntries(source), [source]);
  const stops = useMemo(() => timelineStops(entries), [entries]);
  const placed = useMemo(() => placedPlaces(source, INDIA_BOUNDS, drawing.placeable), [source, drawing.placeable]);
  const shown = Math.min(Math.max(0, at), Math.max(0, stops.length - 1));
  const year = stops[shown] ?? 0;
  const always = useMemo(() => (drawing.pinUndated ? undatedPlaces(source) : []), [source, drawing.pinUndated]);
  const reached = useMemo(() => reachedPlaces(entries, year, always), [entries, year, always]);
  const routes = useMemo(() => routeLines(entries.filter((entry) => entry.yearFrom <= year), placed), [entries, placed, year]);
  const mapped = placed.length > 0;
  return (
    <div className={mapped ? WITH_MAP : WITHOUT_MAP} data-testid="timeline-map" data-year={year} role="group" aria-label={timelineSummary(source, entries)}>
      {mapped ? <TimelinePins placed={placed} reached={reached} routes={routes} boundary={drawing.boundary} parts={drawing.parts} /> : null}
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-4">
        {stops.length > 1 ? (drawing.control ? drawing.control({ entries, stops, at: shown, onChoose }) : <TimelineSlider entries={entries} stops={stops} at={shown} onChoose={onChoose} />) : null}
        {entries.length > 0 ? <TimelineEntries block={source} entries={entries} placed={placed} year={year} texts={drawing.texts} /> : null}
        {source.undated && source.undated.length > 0 ? <TimelineUndatedList block={source} undated={source.undated} placed={placed} texts={drawing.texts} /> : null}
      </div>
    </div>
  );
}

export function useTimelineStop<S>(source: TimelineSource<S>): [number, (index: number) => void] {
  const reduce = useAppReducedMotion();
  const film = useFilmScene();
  const count = useMemo(() => timelineStops(timelineEntries(source)).length, [source]);
  const [chosen, setChosen] = useState(count - 1);
  return [sceneStep(chosen, count, film ? film.progress : null, reduce), setChosen];
}

export function TimelineMapView({ block, at, onChoose }: { block: TimelineMapBlock; at: number; onChoose: (index: number) => void }) {
  const drawing = useMemo(() => ({ texts: CITED_TEXTS, boundary: boundaryNote(block.boundaryCaption, block.datasets) }), [block]);
  return <TimelineMapFrame source={block} at={at} onChoose={onChoose} drawing={drawing} />;
}

export function TimelineMap({ block }: { block: TimelineMapBlock }) {
  const [at, onChoose] = useTimelineStop(block);
  return <TimelineMapView block={block} at={at} onChoose={onChoose} />;
}
