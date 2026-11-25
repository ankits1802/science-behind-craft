import type { MapBox } from "@/components/map/basemap";
import type { MapStill, StillRiver } from "@/components/map/timelineMapStill";
import { unitRef } from "@/lib/componentSpecsPlates";
import { isDeclared, type GeneralHead } from "@/lib/componentSpecsGeneral";
import type { TimelinePlace } from "@/lib/explainerPlay";
import { DISTRICT_SHAPES_ASSET } from "@/lib/mapFiles";
import { physicalLayer, type MineralKeyRow } from "@/lib/mapPhysical";
import { datasetShape, type RegionDataset } from "@/lib/regionContract";
import type { LayerLegend } from "@/lib/regionView";
import { boolean, count, integer, list, matching, nullable, number, object, optional, positive, text, type Shape } from "@/lib/shape";
import type { TimelineSource } from "@/lib/timelineView";

export const TIMELINE_MAP_KIND = "timeline_map";
export const TIMELINE_MAP_MARK = "places";
export const PHYSICAL_LAYER_NAMES = ["relief", "rivers", "minerals"] as const;
export const TIMELINE_MAP_STILL = "still";

export type FoundPlace = { latitude: number; longitude: number; wikidataId?: string; districtLgd?: number };
export type MapPlaceSpec = { name: string; wikidata?: string; district?: number; longitude?: number; latitude?: number; at?: string; home?: boolean; found?: FoundPlace };
export type DatedPlaceSpec = { place: number; yearFrom: number; yearTo: number; text: string };
export type DatedRouteSpec = { start: number; end: number; yearFrom: number; yearTo: number; text: string };
export type UndatedFactSpec = { place?: number | null; text: string };
export type TimelineMapSpec = {
  head: GeneralHead;
  places: MapPlaceSpec[];
  points?: DatedPlaceSpec[];
  routes?: DatedRouteSpec[];
  undated?: UndatedFactSpec[];
  layers?: string[];
  datasets?: RegionDataset[];
  boundaryCaption?: string;
  still?: MapStill;
};
export type UnitSaid = { id: string };

const WIKIDATA = matching(/^Q[1-9]\d*$/, "a Wikidata item");
const LAYER = matching(/^[a-z0-9]+(-[a-z0-9]+)*$/, "a layer name");
const STILL_PATH = matching(/^[MLlz\d .-]*$/, "a still's path");

export const mapStillShape: Shape<MapStill> = object<MapStill>({
  box: object<MapBox>({ x: number, y: number, width: number, height: number }),
  grid: positive,
  relief: nullable(list(STILL_PATH)),
  rivers: nullable(list(object<StillRiver>({ rank: integer, d: STILL_PATH }))),
  lakes: nullable(STILL_PATH),
  home: nullable(STILL_PATH),
  minerals: nullable(list(object<MineralKeyRow>({ id: text, label: text, count }))),
  district: nullable(object<LayerLegend>({ title: text, labels: list(text), caption: text, summary: text, dataset: datasetShape }))
});

export const timelineMapSpecShape: Shape<TimelineMapSpec> = object<TimelineMapSpec>({
  head: object<GeneralHead>({ title: unitRef, caption: nullable(unitRef) }),
  places: list(
    object<MapPlaceSpec>({
      name: unitRef,
      wikidata: optional(WIKIDATA),
      district: optional(integer),
      longitude: optional(number),
      latitude: optional(number),
      at: optional(unitRef),
      home: optional(boolean),
      found: optional(object<FoundPlace>({ latitude: number, longitude: number, wikidataId: optional(WIKIDATA), districtLgd: optional(integer) }))
    }),
    1
  ),
  points: optional(list(object<DatedPlaceSpec>({ place: integer, yearFrom: integer, yearTo: integer, text: unitRef }))),
  routes: optional(list(object<DatedRouteSpec>({ start: integer, end: integer, yearFrom: integer, yearTo: integer, text: unitRef }))),
  undated: optional(list(object<UndatedFactSpec>({ place: optional(nullable(integer)), text: unitRef }))),
  layers: optional(list(LAYER)),
  datasets: optional(list(datasetShape)),
  boundaryCaption: optional(text),
  still: optional(mapStillShape)
});

export function isDeclaredTimelineMap(spec: unknown): boolean {
  return typeof spec === "object" && spec !== null && !Array.isArray(spec) && Object.hasOwn(spec, TIMELINE_MAP_MARK);
}

export function declaredForm(kind: string, spec: unknown): boolean {
  return kind === TIMELINE_MAP_KIND ? isDeclaredTimelineMap(spec) : isDeclared(spec);
}

function mapPlace(place: MapPlaceSpec, name: string): TimelinePlace {
  const found = place.found;
  if (!found) return { name, wikidataId: null, latitude: null, longitude: null };
  const district = found.districtLgd === undefined ? {} : { districtLgd: found.districtLgd };
  return { name, wikidataId: found.wikidataId ?? null, latitude: found.latitude, longitude: found.longitude, ...district };
}

export function timelineMapSource(spec: TimelineMapSpec, nameOf: (ref: string) => string): TimelineSource<UnitSaid> {
  return {
    places: spec.places.map((place) => mapPlace(place, nameOf(place.name))),
    points: (spec.points ?? []).map((point) => ({ place: point.place, yearFrom: point.yearFrom, yearTo: point.yearTo, sentence: { id: point.text } })),
    routes: (spec.routes ?? []).map((route) => ({ start: route.start, end: route.end, yearFrom: route.yearFrom, yearTo: route.yearTo, sentence: { id: route.text } })),
    undated: (spec.undated ?? []).map((fact) => ({ place: fact.place ?? null, sentence: { id: fact.text } }))
  };
}

export function homeDistricts(spec: TimelineMapSpec): number[] {
  return [...new Set(spec.places.flatMap((place) => (place.home && place.found?.districtLgd !== undefined ? [place.found.districtLgd] : [])))];
}

export function foundPoints(spec: TimelineMapSpec): { longitude: number; latitude: number }[] {
  return spec.places.flatMap((place) => (place.found ? [{ longitude: place.found.longitude, latitude: place.found.latitude }] : []));
}

export function layerCredits(spec: TimelineMapSpec, boundaryCode: string): RegionDataset[] {
  return (spec.datasets ?? []).filter((dataset) => dataset.code !== boundaryCode);
}

export function physicalLayers(spec: TimelineMapSpec): (typeof PHYSICAL_LAYER_NAMES)[number][] {
  return PHYSICAL_LAYER_NAMES.filter((name) => (spec.layers ?? []).includes(name));
}

export function districtLayer(spec: TimelineMapSpec): string | null {
  return (spec.layers ?? []).find((name) => !(PHYSICAL_LAYER_NAMES as readonly string[]).includes(name)) ?? null;
}

export function timelineMapFiles(spec: TimelineMapSpec): string[] {
  const shapes = homeDistricts(spec).length > 0 || districtLayer(spec) !== null ? [DISTRICT_SHAPES_ASSET] : [];
  return [...physicalLayers(spec).map((name) => physicalLayer(name).asset), ...shapes];
}
