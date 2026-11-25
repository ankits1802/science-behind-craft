import { viewBoxOf, type MapBox } from "@/components/map/basemap";
import { INDIA_BOUNDS } from "@/components/map/indiaBounds";
import { placesFrame, type FramedPoint } from "@/components/map/placesFrame";
import { districtLayer, foundPoints, homeDistricts, physicalLayers, type TimelineMapSpec } from "@/lib/componentSpecsTimelineMap";
import type { MineralKeyRow } from "@/lib/mapPhysical";
import type { LayerLegend } from "@/lib/regionView";

export type LayerNames = { physical: readonly string[]; district: string | null; home: readonly number[] };
export type StillRiver = { rank: number; d: string };
export type MapStill = {
  box: MapBox;
  grid: number;
  relief: string[] | null;
  rivers: StillRiver[] | null;
  lakes: string | null;
  home: string | null;
  minerals: MineralKeyRow[] | null;
  district: LayerLegend | null;
};
export type TimelineMapDrawn = { frame: MapBox; names: LayerNames; still: MapStill | null };

export function inIndia(point: FramedPoint): boolean {
  return point.longitude >= INDIA_BOUNDS.minLongitude && point.longitude <= INDIA_BOUNDS.maxLongitude && point.latitude >= INDIA_BOUNDS.minLatitude && point.latitude <= INDIA_BOUNDS.maxLatitude;
}

export function timelineMapNames(map: TimelineMapSpec): LayerNames {
  return { physical: physicalLayers(map), district: districtLayer(map), home: homeDistricts(map) };
}

export function timelineMapFrame(map: TimelineMapSpec): MapBox {
  return placesFrame(foundPoints(map).filter(inIndia));
}

export function sameBox(one: MapBox, other: MapBox): boolean {
  return one.x === other.x && one.y === other.y && one.width === other.width && one.height === other.height;
}

export function timelineMapDrawn(map: TimelineMapSpec): TimelineMapDrawn {
  const frame = timelineMapFrame(map);
  const still = map.still && sameBox(map.still.box, frame) ? map.still : null;
  return { frame, names: timelineMapNames(map), still };
}

export function stillKey(frame: MapBox, names: LayerNames): string {
  return [viewBoxOf(frame), names.physical.join(","), names.home.join(",")].join("|");
}
