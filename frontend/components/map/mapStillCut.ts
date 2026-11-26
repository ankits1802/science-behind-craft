import { decodeRings, type MapBox, type NeighbourFile } from "@/components/map/basemap";
import { decodeBorders, type BordersFile } from "@/components/map/borderGeometry";
import { decodePolyline, indiaRings, type Ring } from "@/components/map/indiaGeometry";
import { NAMED_ZOOM, showsDistrictLines } from "@/components/map/mapLayerFrame";
import { projectedFrame } from "@/components/map/placesFrame";
import { project, type Projected } from "@/components/map/projection";
import { decodeRing } from "@/components/map/shapeGeometry";
import { cutLines, cutRings, gridPoints, relativePath, simplified, type StillCut } from "@/components/map/stillGeometry";
import type { LayerNames, MapStill, StillDistrict, StillRiver } from "@/components/map/timelineMapStill";
import { cutWaters, drawsWaters, NO_ASK, showsWaters, type HeldTile } from "@/components/map/waterLayer";
import { layerCredits, mineralKeyRows, mineralSites, type MineralKeyRow, type MineralsFile, type ReliefFile, type RiversFile } from "@/lib/mapPhysical";
import type { MapFrameSpec } from "@/lib/componentSpecsMapLayer";
import type { RegionDataset } from "@/lib/regionContract";
import type { LayerLegend } from "@/lib/regionView";

export const STILL_GRID = 500;
export const STILL_TOLERANCE = 1;
export const STILL_SPECK = 4;
export const STILL_MARGIN = 2;
export const HOME_TENTHS = 10;

export type StillFiles = {
  relief: Pick<ReliefFile, "bands" | "datasets">;
  rivers: Pick<RiversFile, "ranks" | "lakes" | "datasets">;
  minerals: Pick<MineralsFile, "classes" | "sites" | "statuses">;
  shapes: { districts: readonly { lgd: number; stateLgd: number; rings: readonly string[]; centroid: readonly number[] }[] };
  neighbours: Pick<NeighbourFile, "countries">;
  stateBorders: Pick<BordersFile, "lines">;
};

type Rings = Projected[][];
export type StillLayers = {
  relief: Rings[];
  rivers: { rank: number; lines: Rings }[];
  lakes: Rings;
  homes: ReadonlyMap<number, Rings>;
  centres: ReadonlyMap<number, Projected>;
  states: ReadonlyMap<number, number>;
  stateLines: Rings;
  neighbours: Rings;
  minerals: MineralKeyRow[];
  credits: RegionDataset[];
};
export type StillGeometry = Omit<MapStill, "district">;
export type HeldWaters = { tiles: readonly HeldTile[]; credits: RegionDataset[] };

export const NO_WATERS: HeldWaters = { tiles: [], credits: [] };

const projected = (ring: Ring): Projected[] => ring.map(([longitude, latitude]) => project(longitude, latitude));

export function stillLayers(files: StillFiles): StillLayers {
  const india = indiaRings().flatMap((polygon) => polygon.map(projected));
  const bands = files.relief.bands.map((band) => decodeRings(band.rings).map(projected));
  const rivers = [...files.rivers.ranks].sort((a, b) => b.rank - a.rank).map((group) => ({ rank: group.rank, lines: decodePolyline(group.lines, false).map((record) => projected(record.points)) }));
  const homes = new Map(files.shapes.districts.map((district) => [district.lgd, district.rings.map((ring) => projected(decodeRing(ring)))] as const));
  const centres = new Map(files.shapes.districts.map((district) => [district.lgd, project(district.centroid[0], district.centroid[1])] as const));
  const states = new Map(files.shapes.districts.map((district) => [district.lgd, district.stateLgd] as const));
  const neighbours = files.neighbours.countries.flatMap((country) => decodeRings(country.rings).map(projected));
  const credits = layerCredits([...files.relief.datasets, ...files.rivers.datasets]);
  const lakes = decodeRings(files.rivers.lakes).map(projected);
  const stateLines = decodeBorders(files.stateBorders.lines).map(projected);
  return { relief: [india, ...bands], rivers, lakes, homes, centres, states, stateLines, neighbours, minerals: mineralKeyRows(files.minerals, mineralSites(files.minerals)), credits };
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

function valuedDistricts(layers: StillLayers, valued: readonly number[], cut: StillCut): StillDistrict[] | null {
  const drawn = valued.flatMap((lgd) => {
    const d = cutRings(layers.homes.get(lgd) ?? [], cut);
    const centre = layers.centres.get(lgd);
    return d && centre ? [{ lgd, d, x: Number(centre.x.toFixed(1)), y: Number(centre.y.toFixed(1)) }] : [];
  });
  return drawn.length ? drawn : null;
}

function baseParts(layers: StillLayers, names: LayerNames, cut: StillCut, held: HeldWaters): Partial<StillGeometry> {
  const districts = showsDistrictLines(cut.box) ? [...layers.homes.values()].flat() : [];
  const ask = names.emphasis ? { rivers: names.emphasis.rivers, dams: names.emphasis.dams ?? [] } : NO_ASK;
  const waters = showsWaters(cut.box) ? cutWaters(held.tiles, cut, ask) : null;
  const drawn = drawsWaters(waters);
  return {
    lines: cutLines(districts, cut) || null,
    states: cutLines(layers.stateLines, cut) || null,
    neighbours: cutRings(layers.neighbours, cut) || null,
    valued: valuedDistricts(layers, names.valued ?? [], cut),
    credits: drawn ? [...layers.credits, ...held.credits] : layers.credits,
    waters: drawn ? waters : null
  };
}

export function cutStill(layers: StillLayers, frame: MapBox, names: LayerNames, held: HeldWaters = NO_WATERS): StillGeometry {
  const cut = stillCut(frame);
  const named = (id: string) => names.physical.includes(id);
  return {
    box: frame,
    grid: STILL_GRID,
    relief: named("relief") ? layers.relief.map((rings) => cutRings(rings, cut)) : null,
    rivers: named("rivers") ? riverPaths(layers, cut) : null,
    lakes: named("rivers") ? cutRings(layers.lakes, cut) || null : null,
    home: names.home.length ? homePath(layers, names.home, cut) : null,
    minerals: named("minerals") ? layers.minerals : null,
    ...(names.base ? baseParts(layers, names, cut, held) : {})
  };
}

function namedDistricts(layers: StillLayers, frame: MapFrameSpec | undefined): number[] {
  if (frame?.district !== undefined) return [frame.district];
  const state = frame?.state;
  return state === undefined ? [] : [...layers.states].filter(([, owner]) => owner === state).map(([lgd]) => lgd);
}

export function namedBox(layers: StillLayers, frame: MapFrameSpec | undefined): MapBox | null {
  const points = namedDistricts(layers, frame).flatMap((lgd) => (layers.homes.get(lgd) ?? []).flat());
  return points.length ? projectedFrame(points, NAMED_ZOOM) : null;
}

export function heldStill(geometry: StillGeometry, district: LayerLegend | null): MapStill | null {
  const still: MapStill = { ...geometry, district };
  const parts = [still.relief, still.rivers, still.lakes, still.home, still.minerals, still.district];
  return parts.some((part) => part !== null) ? still : null;
}
