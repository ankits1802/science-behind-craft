import type { MapBox } from "@/components/map/basemap";
import { placesFrame, type FramedPoint, type FrameZoom } from "@/components/map/placesFrame";
import { project } from "@/components/map/projection";
import { sameBox, type LayerNames, type MapStill } from "@/components/map/timelineMapStill";
import type { MapLayerSpec } from "@/lib/componentSpecsGeneral";
import { namedFrameKey } from "@/lib/componentSpecsMapLayer";

export const MAP_LAYER_ZOOM: FrameZoom = { minShare: 0.08, paddingShare: 0.3 };
export const NAMED_ZOOM: FrameZoom = { minShare: 0.08, paddingShare: 0.06 };
export const BASE_LAYERS: readonly string[] = ["relief", "rivers"];
export const KM_PER_DEGREE_LATITUDE = 110.574;
export const KM_PER_DEGREE_LONGITUDE = 111.32;
export const SCALE_SHARE = 0.22;
export const SCALE_STEPS = [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000];

export type MapLayerDrawn = { frame: MapBox; names: LayerNames; still: MapStill | null };
export type ScaleBar = { km: number; length: number };
export type Radii = { rx: number; ry: number };

const radians = (degrees: number) => (degrees * Math.PI) / 180;

function longitudeDegrees(radiusKm: number, latitude: number): number {
  return radiusKm / (KM_PER_DEGREE_LONGITUDE * Math.cos(radians(latitude)));
}

export function ringCorners(centre: FramedPoint, radiusKm: number): FramedPoint[] {
  const across = longitudeDegrees(radiusKm, centre.latitude);
  const up = radiusKm / KM_PER_DEGREE_LATITUDE;
  return [
    { longitude: centre.longitude - across, latitude: centre.latitude },
    { longitude: centre.longitude + across, latitude: centre.latitude },
    { longitude: centre.longitude, latitude: centre.latitude - up },
    { longitude: centre.longitude, latitude: centre.latitude + up }
  ];
}

export function ringRadii(centre: FramedPoint, radiusKm: number): Radii {
  const at = project(centre.longitude, centre.latitude);
  const east = project(centre.longitude + longitudeDegrees(radiusKm, centre.latitude), centre.latitude);
  const north = project(centre.longitude, centre.latitude + radiusKm / KM_PER_DEGREE_LATITUDE);
  return { rx: east.x - at.x, ry: at.y - north.y };
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

function latitudeAt(y: number): number {
  const equator = project(0, 0).y;
  return (equator - y) / (equator - project(0, 1).y);
}

export function scaleBar(frame: MapBox): ScaleBar {
  const latitude = latitudeAt(frame.y + frame.height / 2);
  const unitsPerKm = (project(1, latitude).x - project(0, latitude).x) / (KM_PER_DEGREE_LONGITUDE * Math.cos(radians(latitude)));
  const wanted = (frame.width * SCALE_SHARE) / unitsPerKm;
  const km = [...SCALE_STEPS].reverse().find((step) => step <= wanted) ?? SCALE_STEPS[0];
  return { km, length: km * unitsPerKm };
}
