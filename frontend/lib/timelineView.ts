import type { ExplainerSentence } from "@/lib/explainerBlockBase";
import type { TimelinePlace } from "@/lib/explainerPlay";
import { sentenceKey } from "@/lib/sentenceGroups";
import type { LongitudeLatitudeBox } from "@/lib/supplyView";

export type TimelineEntryKind = "point" | "route";
export type TimelineEntryState = "past" | "current" | "later";
export type TimelineEntry<S = ExplainerSentence> = { key: string; kind: TimelineEntryKind; yearFrom: number; yearTo: number; places: number[]; sentence: S };
export type PlacedPlace = { index: number; name: string; wikidataId: string | null; latitude: number; longitude: number; pin: number; beyond: boolean };
export type TimelineRouteLine<S = ExplainerSentence> = { key: string; start: PlacedPlace; end: PlacedPlace; entry: TimelineEntry<S> };
export type EntryGroup<S = ExplainerSentence> = { key: string; sentence: S; items: TimelineEntry<S>[] };
export type TimelineSource<S = ExplainerSentence> = {
  places: readonly TimelinePlace[];
  points: readonly { place: number; yearFrom: number; yearTo: number; sentence: S }[];
  routes: readonly { start: number; end: number; yearFrom: number; yearTo: number; sentence: S }[];
  undated?: readonly { place: number | null; sentence: S }[];
};
export type Placeable = (place: TimelinePlace) => boolean;

const YEARS_PER_CENTURY = 100;
const YEARS_PER_DECADE = 10;

export const REGISTERED: Placeable = (place) => place.wikidataId !== null || place.districtLgd !== undefined;

function ordinal(value: number): string {
  const tens = value % 100;
  if (tens >= 11 && tens <= 13) return `${value}th`;
  return `${value}${["th", "st", "nd", "rd"][value % 10] ?? "th"}`;
}

export function yearSpanText(yearFrom: number, yearTo: number): string {
  if (yearFrom === yearTo) return String(yearFrom);
  if ((yearFrom - 1) % YEARS_PER_CENTURY === 0 && yearTo % YEARS_PER_CENTURY === 0 && yearTo > yearFrom) {
    const first = (yearFrom - 1) / YEARS_PER_CENTURY + 1;
    const last = yearTo / YEARS_PER_CENTURY;
    return first === last ? `${ordinal(first)} century` : `${ordinal(first)}–${ordinal(last)} century`;
  }
  if (yearFrom % YEARS_PER_DECADE === 0 && yearTo === yearFrom + YEARS_PER_DECADE - 1) return `${yearFrom}s`;
  return `${yearFrom}–${yearTo}`;
}

export function timelineEntries<S>(block: TimelineSource<S>): TimelineEntry<S>[] {
  const points = block.points.map((point, index) => ({ key: `point:${index}`, kind: "point" as const, yearFrom: point.yearFrom, yearTo: point.yearTo, places: [point.place], sentence: point.sentence }));
  const routes = block.routes.map((route, index) => ({ key: `route:${index}`, kind: "route" as const, yearFrom: route.yearFrom, yearTo: route.yearTo, places: [route.start, route.end], sentence: route.sentence }));
  return [...points, ...routes].sort((a, b) => a.yearFrom - b.yearFrom || a.yearTo - b.yearTo);
}

export function groupedEntries<S>(entries: readonly TimelineEntry<S>[], keyOf: (sentence: S) => string): EntryGroup<S>[] {
  const groups = new Map<string, EntryGroup<S>>();
  for (const entry of entries) {
    const key = keyOf(entry.sentence);
    const group = groups.get(key) ?? { key, sentence: entry.sentence, items: [] };
    group.items.push(entry);
    groups.set(key, group);
  }
  return [...groups.values()];
}

export function entryGroups(entries: readonly TimelineEntry[]): EntryGroup[] {
  return groupedEntries(entries, sentenceKey);
}

export function groupState<S>(entries: readonly TimelineEntry<S>[], year: number): TimelineEntryState {
  const yearFrom = Math.min(...entries.map((entry) => entry.yearFrom));
  const yearTo = Math.max(...entries.map((entry) => entry.yearTo));
  return entryState({ yearFrom, yearTo }, year);
}

export function timelineStops<S>(entries: readonly TimelineEntry<S>[]): number[] {
  return [...new Set(entries.map((entry) => entry.yearFrom))].sort((a, b) => a - b);
}

export function stopLabel<S>(entries: readonly TimelineEntry<S>[], year: number): string {
  const first = entries.find((entry) => entry.yearFrom === year);
  return first ? yearSpanText(first.yearFrom, first.yearTo) : String(year);
}

export function entryState(entry: Pick<TimelineEntry<unknown>, "yearFrom" | "yearTo">, year: number): TimelineEntryState {
  if (entry.yearFrom > year) return "later";
  return entry.yearTo < year ? "past" : "current";
}

function inBox(latitude: number, longitude: number, box: LongitudeLatitudeBox): boolean {
  return longitude >= box.minLongitude && longitude <= box.maxLongitude && latitude >= box.minLatitude && latitude <= box.maxLatitude;
}

export function placedPlaces(block: Pick<TimelineSource<unknown>, "places">, box: LongitudeLatitudeBox, placeable: Placeable = REGISTERED): PlacedPlace[] {
  const placed: PlacedPlace[] = [];
  block.places.forEach((place, index) => {
    const { wikidataId, latitude, longitude } = place;
    if (!placeable(place) || latitude === null || longitude === null) return;
    placed.push({ index, name: place.name, wikidataId, latitude, longitude, pin: placed.length + 1, beyond: !inBox(latitude, longitude, box) });
  });
  return placed;
}

export function reachedPlaces<S>(entries: readonly TimelineEntry<S>[], year: number, always: readonly number[] = []): Set<number> {
  return new Set([...always, ...entries.filter((entry) => entry.yearFrom <= year).flatMap((entry) => entry.places)]);
}

export function routeLines<S>(entries: readonly TimelineEntry<S>[], placed: readonly PlacedPlace[]): TimelineRouteLine<S>[] {
  const byIndex = new Map(placed.map((place) => [place.index, place]));
  return entries.flatMap((entry) => {
    if (entry.kind !== "route") return [];
    const start = byIndex.get(entry.places[0]);
    const end = byIndex.get(entry.places[1]);
    return start && end ? [{ key: entry.key, start, end, entry }] : [];
  });
}

export function abroadSummary(places: readonly PlacedPlace[]): string {
  return `Beyond the map of India: ${places.map((place) => `${place.pin} ${place.name}`).join(", ")}`;
}

export function timelineSummary<S>(block: Pick<TimelineSource<S>, "places">, entries: readonly TimelineEntry<S>[]): string {
  const stops = timelineStops(entries);
  const names = block.places.map((place) => place.name).join(", ");
  if (stops.length === 0) return names;
  const first = stopLabel(entries, stops[0]);
  const last = stopLabel(entries, stops[stops.length - 1]);
  const span = first === last ? first : `${first} to ${last}`;
  return `${names}, ${span}`;
}
