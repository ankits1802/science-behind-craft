"use client";

import { useMemo, useRef } from "react";

import { useFilmScene } from "@/components/answer/FilmScene";
import { CITED_TEXTS, TimelineEntries, TimelineUndatedList, type TimelineTexts } from "@/components/answer/journey/TimelineEntries";
import { TimelinePins, type TimelineMapParts } from "@/components/answer/journey/TimelinePins";
import { TimelineTrack, type TrackPoint } from "@/components/answer/journey/TimelineTrack";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { INDIA_BOUNDS } from "@/components/map/indiaBounds";
import { usePlayInView, type PlayInView } from "@/components/motion/usePlayInView";
import type { TimelineMapBlock } from "@/lib/explainerPlay";
import { sceneStep } from "@/lib/filmScenes";
import { boundaryNote } from "@/lib/placeView";
import type { BoundaryNote } from "@/lib/regionContract";
import { pointPositions, timelineBeat } from "@/lib/timelinePlay";
import { placedPlaces, reachedPlaces, routeLines, stopLabel, timelineEntries, timelineStops, timelineSummary, type Placeable, type TimelineEntry, type TimelineSource } from "@/lib/timelineView";

const WITH_MAP = "grid min-w-0 grid-cols-[minmax(0,1fr)] gap-5 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] lg:items-start";
const WITHOUT_MAP = "grid min-w-0 grid-cols-[minmax(0,1fr)] gap-4";
export const TIMELINE_POINTS_LABEL = "Dated moments on the map";

export type TimelineMapDrawing<S> = { texts: TimelineTexts<S>; boundary: BoundaryNote | null; placeable?: Placeable; pinUndated?: boolean; parts?: TimelineMapParts };
type FrameProps<S> = { source: TimelineSource<S>; play: PlayInView; drawing: TimelineMapDrawing<S> };

function undatedPlaces<S>(source: TimelineSource<S>): number[] {
  return (source.undated ?? []).flatMap((entry) => (entry.place === null ? [] : [entry.place]));
}

export function stopPoints<S>(entries: readonly TimelineEntry<S>[], stops: readonly number[]): TrackPoint[] {
  const positions = pointPositions(stops);
  return stops.map((stop, at) => ({ key: String(stop), position: positions[at], name: stopLabel(entries, stop), shown: stopLabel(entries, stop) }));
}

function StopTrack({ points, play }: { points: readonly TrackPoint[]; play: PlayInView }) {
  return <TimelineTrack points={points} play={play} label={TIMELINE_POINTS_LABEL} first={points[0].name} last={points[points.length - 1].name} />;
}

export function TimelineMapFrame<S>({ source, play, drawing }: FrameProps<S>) {
  const entries = useMemo(() => timelineEntries(source), [source]);
  const stops = useMemo(() => timelineStops(entries), [entries]);
  const points = useMemo(() => stopPoints(entries, stops), [entries, stops]);
  const placed = useMemo(() => placedPlaces(source, INDIA_BOUNDS, drawing.placeable), [source, drawing.placeable]);
  const shown = Math.min(Math.max(0, play.at), Math.max(0, stops.length - 1));
  const year = stops[shown] ?? 0;
  const always = useMemo(() => (drawing.pinUndated ? undatedPlaces(source) : []), [source, drawing.pinUndated]);
  const reached = useMemo(() => reachedPlaces(entries, year, always), [entries, year, always]);
  const routes = useMemo(() => routeLines(entries.filter((entry) => entry.yearFrom <= year), placed), [entries, placed, year]);
  const mapped = placed.length > 0;
  return (
    <div className={mapped ? WITH_MAP : WITHOUT_MAP} data-testid="timeline-map" data-year={year} role="group" aria-label={timelineSummary(source, entries)}>
      {mapped ? <TimelinePins placed={placed} reached={reached} routes={routes} boundary={drawing.boundary} parts={drawing.parts} /> : null}
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-4">
        {stops.length > 1 ? <StopTrack points={points} play={{ ...play, at: shown }} /> : null}
        {entries.length > 0 ? <TimelineEntries block={source} entries={entries} placed={placed} year={year} texts={drawing.texts} /> : null}
        {source.undated && source.undated.length > 0 ? <TimelineUndatedList block={source} undated={source.undated} placed={placed} texts={drawing.texts} /> : null}
      </div>
    </div>
  );
}

export function TimelineMapView({ block, play }: { block: TimelineMapBlock; play: PlayInView }) {
  const drawing = useMemo(() => ({ texts: CITED_TEXTS, boundary: boundaryNote(block.boundaryCaption, block.datasets) }), [block]);
  return <TimelineMapFrame source={block} play={play} drawing={drawing} />;
}

export function TimelineMap({ block }: { block: TimelineMapBlock }) {
  const watched = useRef<HTMLDivElement | null>(null);
  const reduce = useAppReducedMotion();
  const film = useFilmScene();
  const count = useMemo(() => timelineStops(timelineEntries(block)).length, [block]);
  const play = usePlayInView(count, count - 1, watched, timelineBeat);
  const at = film ? sceneStep(play.at, count, film.progress, reduce) : play.at;
  return (
    <div ref={film ? undefined : watched} className="min-w-0" data-testid="timeline-map-play" data-at={at}>
      <TimelineMapView block={block} play={{ ...play, at }} />
    </div>
  );
}
