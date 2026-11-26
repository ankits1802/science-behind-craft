import type { MapBox } from "@/components/map/basemap";
import { decodePolyline } from "@/components/map/indiaGeometry";
import { showsDistrictLines } from "@/components/map/mapLayerFrame";
import { project, type Projected } from "@/components/map/projection";
import { clippedLine, cutLines, type StillCut } from "@/components/map/stillGeometry";
import { answersTo, riverNames, type WatersIndex, type WatersTile } from "@/lib/mapWaters";

export type HeldRiver = { id: number; names: string[]; lines: Projected[][] };
export type HeldDam = { name: string; at: Projected };
export type HeldTile = { id: string; rivers: HeldRiver[]; dams: HeldDam[]; plain: Projected[][] };
export type WaterAsk = { rivers: readonly string[]; dams: readonly string[] };
export type StillWaterRiver = { name: string; d: string; x: number; y: number };
export type StillWaterDam = { name: string; x: number; y: number };
export type StillWaters = { d: string | null; strong: StillWaterRiver[]; dams: StillWaterDam[] };

export const NO_ASK: WaterAsk = { rivers: [], dams: [] };

const tenths = (value: number) => Math.round(value * 10) / 10;

export function showsWaters(frame: MapBox): boolean {
  return showsDistrictLines(frame);
}

export function heldTile(tile: WatersTile): HeldTile {
  const projected = (points: readonly [number, number][]) => points.map(([longitude, latitude]) => project(longitude, latitude));
  return {
    id: tile.tile,
    rivers: tile.rivers.map((river) => ({ id: river.id, names: riverNames(river), lines: decodePolyline(river.lines, false).map((record) => projected(record.points)) })),
    dams: tile.dams.map((dam) => ({ name: dam.name, at: project(dam.longitude, dam.latitude) })),
    plain: decodePolyline(tile.plain ?? "", false).map((record) => projected(record.points))
  };
}

export function tileBox(bounds: readonly number[]): MapBox {
  const [west, south, east, north] = bounds;
  const corner = project(west, north);
  const far = project(east, south);
  return { x: corner.x, y: corner.y, width: far.x - corner.x, height: far.y - corner.y };
}

function overlaps(one: MapBox, other: MapBox): boolean {
  return one.x < other.x + other.width && other.x < one.x + one.width && one.y < other.y + other.height && other.y < one.y + one.height;
}

export function tilesInFrame(index: Pick<WatersIndex, "tiles">, frame: MapBox): string[] {
  return showsWaters(frame) ? index.tiles.filter((row) => overlaps(tileBox(row.bounds), frame)).map((row) => row.id) : [];
}

function lengthOf(line: readonly Projected[]): number {
  return line.slice(1).reduce((total, point, at) => total + Math.hypot(point.x - line[at].x, point.y - line[at].y), 0);
}

export function midway(line: readonly Projected[]): Projected | null {
  let left = lengthOf(line) / 2;
  for (let at = 1; at < line.length; at += 1) {
    const step = Math.hypot(line[at].x - line[at - 1].x, line[at].y - line[at - 1].y);
    if (step >= left && step > 0) return { x: line[at - 1].x + ((line[at].x - line[at - 1].x) * left) / step, y: line[at - 1].y + ((line[at].y - line[at - 1].y) * left) / step };
    left -= step;
  }
  return line[0] ?? null;
}

function strongRiver(rivers: readonly HeldRiver[], name: string, cut: StillCut): StillWaterRiver[] {
  const lines = rivers.filter((river) => answersTo(river.names, name)).flatMap((river) => river.lines);
  const runs = lines.flatMap((line) => clippedLine(line, cut.box));
  const longest = runs.reduce<Projected[] | null>((best, run) => (!best || lengthOf(run) > lengthOf(best) ? run : best), null);
  const anchor = longest ? midway(longest) : null;
  const d = cutLines(lines, cut);
  return d && anchor ? [{ name, d, x: tenths(anchor.x), y: tenths(anchor.y) }] : [];
}

function inBox(box: MapBox, at: Projected): boolean {
  return at.x >= box.x && at.x <= box.x + box.width && at.y >= box.y && at.y <= box.y + box.height;
}

export function cutWaters(tiles: readonly HeldTile[], cut: StillCut, ask: WaterAsk): StillWaters {
  const rivers = tiles.flatMap((tile) => tile.rivers);
  const dams = tiles.flatMap((tile) => tile.dams).filter((dam) => inBox(cut.box, dam.at) && ask.dams.some((name) => answersTo([dam.name], name)));
  return {
    d: cutLines([...rivers.flatMap((river) => river.lines), ...tiles.flatMap((tile) => tile.plain)], cut) || null,
    strong: ask.rivers.flatMap((name) => strongRiver(rivers, name, cut)),
    dams: dams.map((dam) => ({ name: dam.name, x: tenths(dam.at.x), y: tenths(dam.at.y) }))
  };
}

export function drawsWaters(waters: StillWaters | null | undefined): waters is StillWaters {
  return Boolean(waters && (waters.d || waters.strong.length || waters.dams.length));
}
