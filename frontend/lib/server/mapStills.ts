import { mapLayerFrame, mapLayerNames } from "@/components/map/mapLayerFrame";
import type { MapBox } from "@/components/map/basemap";
import { cutStill, heldStill, namedBox, NO_WATERS, stillLayers, type HeldWaters, type StillGeometry, type StillLayers } from "@/components/map/mapStillCut";
import { stillKey, timelineMapFrame, timelineMapNames, type MapStill } from "@/components/map/timelineMapStill";
import { isDeclared, mapLayerSpecShape, parsedSpec, type MapLayerSpec } from "@/lib/componentSpecsGeneral";
import { homeDistrictsOf, MAP_LAYER_KIND, namedFrameKey } from "@/lib/componentSpecsMapLayer";
import { declaredForm, TIMELINE_MAP_KIND, TIMELINE_MAP_STILL, timelineMapSpecShape, type TimelineMapSpec } from "@/lib/componentSpecsTimelineMap";
import type { MonographDocument } from "@/lib/monographDocument";
import { MAP_LAYER_PATH, MAP_LAYERS_PATH, mapLayerListShape, type BoundaryNote } from "@/lib/regionContract";
import { layerLegend, parsedMapLayer, type LayerLegend } from "@/lib/regionView";
import { publicFetch } from "@/lib/server/serverFetch";
import { codedBasedDocument, codedMaps } from "@/lib/server/codedMapStills";
import { heldWaters } from "@/lib/server/waterStills";
import { parseShape } from "@/lib/shape";

export const STILLS_KEPT = 200;
export const MAP_LAYER_TAG = "map-layer";
export const MAP_LAYERS_TAG = "map-layers";

type Spec = Record<string, unknown>;
type Kept = Map<string, StillGeometry>;
export type DeclaredMap = { label: string; spec: Spec; map: TimelineMapSpec };
export type PlacesMap = { label: string; spec: Spec; map: MapLayerSpec; home: number[] };
export type StillOf = (map: TimelineMapSpec) => MapStill | null;
export type PlacesStillOf = (map: PlacesMap) => MapStill | null;

function withoutStill(spec: Spec): Spec {
  return Object.fromEntries(Object.entries(spec).filter(([key]) => key !== TIMELINE_MAP_STILL));
}

function timelineMapLabels(document: MonographDocument): string[] {
  return document.content.components.filter((component) => component.kind === TIMELINE_MAP_KIND && Object.hasOwn(document.specs, component.label)).map((component) => component.label);
}

export function declaredMaps(document: MonographDocument): DeclaredMap[] {
  return timelineMapLabels(document).flatMap((label) => {
    const spec = withoutStill(document.specs[label]);
    const map = declaredForm(TIMELINE_MAP_KIND, spec) ? parsedSpec(timelineMapSpecShape, spec) : null;
    return map ? [{ label, spec, map }] : [];
  });
}

export function placesMaps(document: MonographDocument): PlacesMap[] {
  return document.content.components.flatMap((component) => {
    const found = component.kind === MAP_LAYER_KIND && Object.hasOwn(document.specs, component.label) ? document.specs[component.label] : null;
    if (!found || !isDeclared(found)) return [];
    const spec = withoutStill(found);
    const map = parsedSpec(mapLayerSpecShape, spec);
    return map ? [{ label: component.label, spec, map, home: homeDistrictsOf(component.subjects) }] : [];
  });
}

export function stilledDocument(document: MonographDocument, maps: readonly DeclaredMap[], stillOf: StillOf): MonographDocument {
  const labels = timelineMapLabels(document);
  if (!labels.length) return document;
  const specs = { ...document.specs };
  for (const label of labels) specs[label] = withoutStill(specs[label]);
  for (const { label, spec, map } of maps) {
    const still = stillOf(map);
    if (still) specs[label] = { ...spec, [TIMELINE_MAP_STILL]: still };
  }
  return { ...document, specs };
}

export function placesStilledDocument(document: MonographDocument, maps: readonly PlacesMap[], stillOf: PlacesStillOf): MonographDocument {
  if (!maps.length) return document;
  const specs = { ...document.specs };
  for (const found of maps) {
    const still = stillOf(found);
    specs[found.label] = still ? { ...found.spec, [TIMELINE_MAP_STILL]: still } : found.spec;
  }
  return { ...document, specs };
}

function keptGeometry(kept: Kept, key: string, cut: () => StillGeometry): StillGeometry {
  const held = kept.get(key);
  if (held) return held;
  const geometry = cut();
  const oldest = kept.keys().next();
  if (kept.size >= STILLS_KEPT && !oldest.done) kept.delete(oldest.value);
  kept.set(key, geometry);
  return geometry;
}

export function stillOfMaps(layers: StillLayers, legends: ReadonlyMap<string, LayerLegend>, kept: Kept = new Map()): StillOf {
  return (map) => {
    const frame = timelineMapFrame(map);
    const names = timelineMapNames(map);
    const geometry = keptGeometry(kept, stillKey(frame, names), () => cutStill(layers, frame, names));
    return heldStill(geometry, names.district ? (legends.get(names.district) ?? null) : null);
  };
}

export function placesFrameOf(layers: StillLayers, map: MapLayerSpec): MapBox {
  return namedBox(layers, map.frame) ?? mapLayerFrame(map);
}

export function stillOfPlaces(layers: StillLayers, boundary: BoundaryNote | null, kept: Kept = new Map(), waters: HeldWaters = NO_WATERS): PlacesStillOf {
  return ({ map, home }) => {
    const named = namedBox(layers, map.frame);
    const frame = named ?? mapLayerFrame(map);
    const names = mapLayerNames(map, home);
    const geometry = keptGeometry(kept, stillKey(frame, names), () => cutStill(layers, frame, names, waters));
    const still = heldStill(geometry, null);
    if (!still) return null;
    const key = named ? namedFrameKey(map.frame) : null;
    return { ...still, boundary, ...(key ? { named: key } : {}) };
  };
}

async function listedBoundary(places: readonly PlacesMap[]): Promise<BoundaryNote | null> {
  if (!places.length) return null;
  const result = await publicFetch(MAP_LAYERS_PATH, { parse: (body) => parseShape(mapLayerListShape, body), tags: [MAP_LAYERS_TAG] });
  return result.ok ? result.body.boundary : null;
}

async function districtLegends(maps: readonly DeclaredMap[]): Promise<Map<string, LayerLegend>> {
  const ids = [...new Set(maps.flatMap(({ map }) => timelineMapNames(map).district ?? []))];
  const read = await Promise.all(ids.map(async (id) => ({ id, result: await publicFetch(MAP_LAYER_PATH(id), { parse: parsedMapLayer, tags: [`${MAP_LAYER_TAG}:${id}`] }) })));
  return new Map(read.flatMap(({ id, result }) => (result.ok ? [[id, layerLegend(result.body)] as const] : [])));
}

let held: Promise<StillLayers> | null = null;
const KEPT: Kept = new Map();
const NO_STILL: StillOf = () => null;

function heldLayers(): Promise<StillLayers> {
  held ??= import("@/lib/server/mapLayerFiles")
    .then((files) => stillLayers(files.STILL_FILES))
    .catch((cause: unknown) => {
      held = null;
      throw cause;
    });
  return held;
}

export async function withMapStills(document: MonographDocument): Promise<MonographDocument> {
  const maps = declaredMaps(document);
  const places = placesMaps(document);
  const coded = codedMaps(document);
  if (!maps.length && !places.length && !coded.length) return codedBasedDocument(stilledDocument(document, maps, NO_STILL), [], null, NO_WATERS);
  const [layers, legends, boundary] = await Promise.all([heldLayers(), districtLegends(maps), listedBoundary(places)]);
  const waters = await heldWaters([...places.map(({ map }) => placesFrameOf(layers, map)), ...coded.map((figure) => figure.box)]);
  const timeline = stilledDocument(document, maps, stillOfMaps(layers, legends, KEPT));
  const placed = placesStilledDocument(timeline, places, stillOfPlaces(layers, boundary, KEPT, waters));
  return codedBasedDocument(placed, coded, layers, waters);
}
