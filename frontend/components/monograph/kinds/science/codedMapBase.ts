import { decodeRings, linesPath, RANN_PATH, ringsPath } from "@/components/map/basemap";
import { loadBorders } from "@/components/map/borderGeometry";
import { INDIA_BOUNDS } from "@/components/map/indiaBounds";
import { bordersToPath, indiaOutlinePath, project, VIEW_BOX } from "@/components/map/projection";
import { loadShapes, shapePath, type DistrictShape } from "@/components/map/shapeGeometry";
import type { MapBase, MapHome } from "@/lib/codedFigureFrame";
import type { CodedBase } from "@/components/map/codedStillCut";
import type { CodedMap, MapLayer } from "@/lib/componentSpecsScienceCoded";
import { loadPhysical, type ReliefFile, type RiversFile } from "@/lib/mapPhysical";

const RELIEF_STEPS_MAX = 7;

export function mapFrame(): Pick<MapBase, "bounds" | "width" | "padding" | "viewBox" | "outline" | "rann"> {
  const corner = project(INDIA_BOUNDS.minLongitude, INDIA_BOUNDS.maxLatitude);
  return {
    bounds: { west: INDIA_BOUNDS.minLongitude, east: INDIA_BOUNDS.maxLongitude, south: INDIA_BOUNDS.minLatitude, north: INDIA_BOUNDS.maxLatitude },
    width: VIEW_BOX.width,
    padding: corner.x,
    viewBox: `0 0 ${VIEW_BOX.width} ${VIEW_BOX.height}`,
    outline: indiaOutlinePath(),
    rann: RANN_PATH
  };
}

function reliefPaths(file: ReliefFile | null): MapBase["relief"] {
  if (!file) return [];
  return file.bands.slice(0, RELIEF_STEPS_MAX).map((band, at) => ({ step: at + 1, d: ringsPath(decodeRings(band.rings)) }));
}

function riverPaths(file: RiversFile | null): string[] {
  if (!file) return [];
  return [...file.ranks].sort((one, other) => other.rank - one.rank).map((group) => linesPath(group.lines));
}

function homes(shapes: readonly DistrictShape[] | null, wanted: readonly number[]): MapHome[] {
  if (!shapes) return [];
  return shapes
    .filter((shape) => wanted.includes(shape.lgd))
    .map((shape) => {
      const { x, y } = project(shape.centroid[0], shape.centroid[1]);
      return { lgd: shape.lgd, d: shapePath(shape), x: Math.round(x * 10) / 10, y: Math.round(y * 10) / 10 };
    });
}

export async function codedMapBase(map: CodedMap, served?: CodedBase): Promise<MapBase> {
  const wants = (layer: MapLayer) => map.layers.includes(layer);
  const [states, districts, relief, rivers, shapes] = await Promise.all([
    wants("states") ? loadBorders("state") : null,
    wants("districts") ? loadBorders("district") : null,
    wants("relief") ? loadPhysical("relief") : null,
    wants("rivers") ? loadPhysical("rivers") : null,
    map.districts.length ? loadShapes() : null
  ]);
  return {
    ...mapFrame(),
    relief: reliefPaths(relief),
    rivers: riverPaths(rivers),
    states: states ? bordersToPath(states) : null,
    districts: districts ? bordersToPath(districts) : null,
    homes: homes(shapes, map.districts),
    named: { rivers: served?.rivers ?? [], dams: served?.dams ?? [] }
  };
}
