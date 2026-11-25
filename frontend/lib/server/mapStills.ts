import { cutStill, heldStill, stillLayers, type StillGeometry, type StillLayers } from "@/components/map/mapStillCut";
import { stillKey, timelineMapFrame, timelineMapNames, type MapStill } from "@/components/map/timelineMapStill";
import { parsedSpec } from "@/lib/componentSpecsGeneral";
import { declaredForm, TIMELINE_MAP_KIND, TIMELINE_MAP_STILL, timelineMapSpecShape, type TimelineMapSpec } from "@/lib/componentSpecsTimelineMap";
import type { MonographDocument } from "@/lib/monographDocument";
import { MAP_LAYER_PATH } from "@/lib/regionContract";
import { layerLegend, parsedMapLayer, type LayerLegend } from "@/lib/regionView";
import { publicFetch } from "@/lib/server/serverFetch";

export const STILLS_KEPT = 200;
export const MAP_LAYER_TAG = "map-layer";

type Spec = Record<string, unknown>;
export type DeclaredMap = { label: string; spec: Spec; map: TimelineMapSpec };
export type StillOf = (map: TimelineMapSpec) => MapStill | null;

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

export function stillOfMaps(layers: StillLayers, legends: ReadonlyMap<string, LayerLegend>, kept: Map<string, StillGeometry> = new Map()): StillOf {
  return (map) => {
    const frame = timelineMapFrame(map);
    const names = timelineMapNames(map);
    const key = stillKey(frame, names);
    const geometry = kept.get(key) ?? cutStill(layers, frame, names);
    if (!kept.has(key)) {
      const oldest = kept.keys().next();
      if (kept.size >= STILLS_KEPT && !oldest.done) kept.delete(oldest.value);
      kept.set(key, geometry);
    }
    return heldStill(geometry, names.district ? (legends.get(names.district) ?? null) : null);
  };
}

async function districtLegends(maps: readonly DeclaredMap[]): Promise<Map<string, LayerLegend>> {
  const ids = [...new Set(maps.flatMap(({ map }) => timelineMapNames(map).district ?? []))];
  const read = await Promise.all(ids.map(async (id) => ({ id, result: await publicFetch(MAP_LAYER_PATH(id), { parse: parsedMapLayer, tags: [`${MAP_LAYER_TAG}:${id}`] }) })));
  return new Map(read.flatMap(({ id, result }) => (result.ok ? [[id, layerLegend(result.body)] as const] : [])));
}

let held: Promise<StillLayers> | null = null;
const KEPT = new Map<string, StillGeometry>();
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
  if (!maps.length) return stilledDocument(document, maps, NO_STILL);
  const [layers, legends] = await Promise.all([heldLayers(), districtLegends(maps)]);
  return stilledDocument(document, maps, stillOfMaps(layers, legends, KEPT));
}
