import { decodeRings, type MapBox } from "@/components/map/basemap";
import { decodePolyline, indiaRings, type Ring } from "@/components/map/indiaGeometry";
import { project, type Projected } from "@/components/map/projection";
import { decodeRing } from "@/components/map/shapeGeometry";
import { cutLines, cutRings, gridPoints, relativePath, simplified, type StillCut } from "@/components/map/stillGeometry";
import type { LayerNames, MapStill, StillRiver } from "@/components/map/timelineMapStill";
import { mineralKeyRows, mineralSites, type MineralKeyRow, type MineralsFile, type ReliefFile, type RiversFile } from "@/lib/mapPhysical";
import type { LayerLegend } from "@/lib/regionView";

export const STILL_GRID = 500;
export const STILL_TOLERANCE = 1;
export const STILL_SPECK = 4;
export const STILL_MARGIN = 2;
export const HOME_TENTHS = 10;

export type StillFiles = {
  relief: Pick<ReliefFile, "bands">;
  rivers: Pick<RiversFile, "ranks" | "lakes">;
  minerals: Pick<MineralsFile, "classes" | "sites" | "statuses">;
  shapes: { districts: readonly { lgd: number; rings: readonly string[] }[] };
};

type Rings = Projected[][];
export type StillLayers = { relief: Rings[]; rivers: { rank: number; lines: Rings }[]; lakes: Rings; homes: ReadonlyMap<number, Rings>; minerals: MineralKeyRow[] };
export type StillGeometry = Omit<MapStill, "district">;

const projected = (ring: Ring): Projected[] => ring.map(([longitude, latitude]) => project(longitude, latitude));

export function stillLayers(files: StillFiles): StillLayers {
  const india = indiaRings().flatMap((polygon) => polygon.map(projected));
  const bands = files.relief.bands.map((band) => decodeRings(band.rings).map(projected));
  const rivers = [...files.rivers.ranks].sort((a, b) => b.rank - a.rank).map((group) => ({ rank: group.rank, lines: decodePolyline(group.lines, false).map((record) => projected(record.points)) }));
  const homes = new Map(files.shapes.districts.map((district) => [district.lgd, district.rings.map((ring) => projected(decodeRing(ring)))] as const));
  return { relief: [india, ...bands], rivers, lakes: decodeRings(files.rivers.lakes).map(projected), homes, minerals: mineralKeyRows(files.minerals, mineralSites(files.minerals)) };
}

export function stillCut(frame: MapBox): StillCut {
  const step = frame.width / STILL_GRID;
  const margin = STILL_MARGIN * step;
  const clip = { x: frame.x - margin, y: frame.y - margin, width: frame.width + 2 * margin, height: frame.height + 2 * margin };
  return { box: frame, clip, units: 1 / step, tolerance: STILL_TOLERANCE * step, speck: STILL_SPECK };
}

function homePath(layers: StillLayers, home: readonly number[], cut: StillCut): string | null {
  const rings = home.flatMap((lgd) => layers.homes.get(lgd) ?? []);
  const drawn = rings.map((ring) => relativePath(gridPoints(simplified(ring, cut.tolerance), { x: 0, y: 0 }, HOME_TENTHS), true, HOME_TENTHS)).join("");
  return drawn || null;
}

function riverPaths(layers: StillLayers, cut: StillCut): StillRiver[] {
  return layers.rivers.map((group) => ({ rank: group.rank, d: cutLines(group.lines, cut) })).filter((group) => group.d.length > 0);
}

export function cutStill(layers: StillLayers, frame: MapBox, names: LayerNames): StillGeometry {
  const cut = stillCut(frame);
  const named = (id: string) => names.physical.includes(id);
  return {
    box: frame,
    grid: STILL_GRID,
    relief: named("relief") ? layers.relief.map((rings) => cutRings(rings, cut)) : null,
    rivers: named("rivers") ? riverPaths(layers, cut) : null,
    lakes: named("rivers") ? cutRings(layers.lakes, cut) || null : null,
    home: names.home.length ? homePath(layers, names.home, cut) : null,
    minerals: named("minerals") ? layers.minerals : null
  };
}

export function heldStill(geometry: StillGeometry, district: LayerLegend | null): MapStill | null {
  const still: MapStill = { ...geometry, district };
  const parts = [still.relief, still.rivers, still.lakes, still.home, still.minerals, still.district];
  return parts.some((part) => part !== null) ? still : null;
}
