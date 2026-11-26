import { unitRef } from "@/lib/componentSpecsPlates";
import { formatRange } from "@/lib/measure";
import { boolean, integer, list, number, object, oneOf, optional, ruled, text, type Shape } from "@/lib/shape";

export const MAP_LAYER_KIND = "map_layer";
export const EMPHASIS_LAYERS = ["relief", "rivers", "water"] as const;
export const VALUE_CLASSES_MAX = 5;
export const PLACE_SUBJECT = /^place:lgd:(\d+)$/;

export type EmphasisLayer = (typeof EMPHASIS_LAYERS)[number];
export type MapFrameSpec = { places?: number[]; district?: number; state?: number };
export type MapEmphasisSpec = { layers: EmphasisLayer[]; rivers: string[] };
export type MapRouteSpec = { start: number; end: number; text: string };
export type MapRingSpec = { place: number; radiusKm: number; text: string };
export type DistrictValueSpec = { district: number; value: number; reading: string };
export type MapDistrictsSpec = { valueLabel: string; values: DistrictValueSpec[] };
export type MapStepSpec = { text: string; places: number[]; routes: number[]; rings: number[]; districts: boolean };
export type MapPartsSpec = {
  frame?: MapFrameSpec;
  emphasis?: MapEmphasisSpec;
  routes?: MapRouteSpec[];
  rings?: MapRingSpec[];
  districts?: MapDistrictsSpec;
  sequence?: MapStepSpec[];
};
export type ShownMarks = { places: ReadonlySet<number>; current: ReadonlySet<number>; routes: ReadonlySet<number>; rings: ReadonlySet<number>; districts: boolean };
export type ValueClass = { min: number; max: number; label: string };

const index = ruled(integer, "an index from 0", (value) => value >= 0);
const radius = ruled(number, "a radius above 0", (value) => value > 0);

export const mapPartShapes = {
  frame: optional(object<MapFrameSpec>({ places: optional(list(index, 1)), district: optional(integer), state: optional(integer) })),
  emphasis: optional(object<MapEmphasisSpec>({ layers: list(oneOf(EMPHASIS_LAYERS)), rivers: list(text) })),
  routes: optional(list(object<MapRouteSpec>({ start: index, end: index, text: unitRef }), 1)),
  rings: optional(list(object<MapRingSpec>({ place: index, radiusKm: radius, text: unitRef }), 1)),
  districts: optional(object<MapDistrictsSpec>({ valueLabel: unitRef, values: list(object<DistrictValueSpec>({ district: integer, value: number, reading: unitRef }), 2) })),
  sequence: optional(list(object<MapStepSpec>({ text: unitRef, places: list(index), routes: list(index), rings: list(index), districts: boolean }), 2))
} satisfies { [K in keyof MapPartsSpec]-?: Shape<MapPartsSpec[K]> };

export function homeDistrictsOf(subjects: readonly string[]): number[] {
  return [...new Set(subjects.flatMap((subject) => PLACE_SUBJECT.exec(subject)?.slice(1).map(Number) ?? []))];
}

export function namedFrameKey(frame: MapFrameSpec | undefined): string | null {
  if (frame?.district !== undefined) return `district:${frame.district}`;
  if (frame?.state !== undefined) return `state:${frame.state}`;
  return null;
}

function everyIndex(length: number): number[] {
  return Array.from({ length }, (_, at) => at);
}

function stepPlaces(parts: MapPartsSpec, step: MapStepSpec): number[] {
  const routes = step.routes.flatMap((at) => {
    const route = parts.routes?.[at];
    return route ? [route.start, route.end] : [];
  });
  const rings = step.rings.flatMap((at) => {
    const ring = parts.rings?.[at];
    return ring ? [ring.place] : [];
  });
  return [...step.places, ...routes, ...rings];
}

function revealed(count: number, steps: readonly MapStepSpec[], reached: readonly MapStepSpec[], pick: (step: MapStepSpec) => number[]): Set<number> {
  const stepped = new Set(steps.flatMap(pick));
  const shown = new Set(reached.flatMap(pick));
  return new Set(everyIndex(count).filter((item) => !stepped.has(item) || shown.has(item)));
}

export function shownMarks(parts: MapPartsSpec, places: number, at: number): ShownMarks {
  const steps = parts.sequence ?? [];
  const reached = steps.slice(0, at + 1);
  const placesOf = (step: MapStepSpec) => stepPlaces(parts, step);
  const current = steps[at];
  return {
    places: revealed(places, steps, reached, placesOf),
    current: new Set(current ? placesOf(current) : []),
    routes: revealed(parts.routes?.length ?? 0, steps, reached, (step) => step.routes),
    rings: revealed(parts.rings?.length ?? 0, steps, reached, (step) => step.rings),
    districts: parts.districts !== undefined && (!steps.some((step) => step.districts) || reached.some((step) => step.districts))
  };
}

export function valueClasses(values: readonly number[], unit = ""): ValueClass[] {
  const ordered = [...new Set(values)].sort((a, b) => a - b);
  const count = Math.min(VALUE_CLASSES_MAX, ordered.length);
  return everyIndex(count).map((group) => {
    const members = ordered.slice(Math.floor((group * ordered.length) / count), Math.floor(((group + 1) * ordered.length) / count));
    const min = members[0];
    const max = members[members.length - 1];
    return { min, max, label: formatRange(min, max, unit) ?? "" };
  });
}

export function valueClassOf(value: number, classes: readonly ValueClass[]): number {
  const found = classes.findIndex((band) => value <= band.max);
  return found === -1 ? classes.length - 1 : found;
}
