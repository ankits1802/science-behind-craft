import type { MapBox } from "@/components/map/basemap";
import { ringCorners } from "@/components/map/mapDistance";
import { WHOLE_MAP } from "@/components/map/layout";
import { placesFrame, type FramedPoint, type FrameZoom } from "@/components/map/placesFrame";
import { sameBox, type LayerNames, type MapStill } from "@/components/map/timelineMapStill";
import type { MapLayerSpec } from "@/lib/componentSpecsGeneral";
import { namedFrameKey } from "@/lib/componentSpecsMapLayer";

export const MAP_LAYER_ZOOM: FrameZoom = { minShare: 0.08, paddingShare: 0.3 };
export const NAMED_ZOOM: FrameZoom = { minShare: 0.08, paddingShare: 0.06 };
export const BASE_LAYERS: readonly string[] = ["relief", "rivers"];
export const DISTRICT_LINES_SHARE = 0.35;

export type MapLayerDrawn = { frame: MapBox; names: LayerNames; still: MapStill | null };

export function showsDistrictLines(frame: MapBox): boolean {
  return frame.width <= WHOLE_MAP.width * DISTRICT_LINES_SHARE;
}

export function framedPoints(spec: MapLayerSpec): FramedPoint[] {
  const chosen = spec.frame?.places ?? spec.places.map((_, at) => at);
  const places = chosen.flatMap((at) => (spec.places[at] ? [spec.places[at]] : []));
  const rings = (spec.rings ?? []).filter((ring) => chosen.includes(ring.place)).flatMap((ring) => (spec.places[ring.place] ? ringCorners(spec.places[ring.place], ring.radiusKm) : []));
  return [...places, ...rings];
}

export function mapLayerFrame(spec: MapLayerSpec): MapBox {
  const key = namedFrameKey(spec.frame);
  if (key !== null && spec.still?.named === key) return spec.still.box;
  return placesFrame(framedPoints(spec), MAP_LAYER_ZOOM);
}

export function mapLayerNames(spec: MapLayerSpec, home: readonly number[]): LayerNames {
  const valued = (spec.districts?.values ?? []).map((value) => value.district);
  return { physical: BASE_LAYERS, district: null, home, base: true, valued, emphasis: spec.emphasis ?? { layers: [], rivers: [] } };
}

export function mapLayerDrawn(spec: MapLayerSpec, home: readonly number[]): MapLayerDrawn {
  const frame = mapLayerFrame(spec);
  const still = spec.still && sameBox(spec.still.box, frame) ? spec.still : null;
  return { frame, names: mapLayerNames(spec, home), still };
}
