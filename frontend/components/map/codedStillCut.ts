import type { MapBox } from "@/components/map/basemap";
import { drawsDistrictLines } from "@/components/map/mapLayerFrame";
import { STILL_GRID, stillCut, type HeldWaters, type StillLayers } from "@/components/map/mapStillCut";
import type { Projected } from "@/components/map/projection";
import { cutLines, cutRings } from "@/components/map/stillGeometry";
import { cutWaters, drawsWaters, showsWaters, type HeldTile, type StillWaters } from "@/components/map/waterLayer";
import { answersTo } from "@/lib/mapWaters";

export type CodedLayer = "states" | "districts" | "rivers" | "relief";
export type CodedMapAsk = { layers: readonly CodedLayer[]; districts: readonly number[]; rivers?: readonly string[]; dams?: readonly string[] };
export type CodedStillBase = { box: MapBox; grid: number; land: string | null; relief: string[] | null; rivers: string | null; districts: string | null; states: string | null; homes: string | null; waters: StillWaters | null };
export type CodedRiverPath = { name: string; d: string };
export type CodedDam = { name: string; x: number; y: number };
export type CodedBase = { still: CodedStillBase; rivers: CodedRiverPath[]; dams: CodedDam[] };

const tenths = (value: number) => (Math.round(value * 10) / 10).toString();

function absolutePath(lines: readonly (readonly Projected[])[]): string {
  return lines.map((line) => line.map((point, at) => `${at ? "L" : "M"}${tenths(point.x)} ${tenths(point.y)}`).join("")).join("");
}

function stillWaters(held: HeldWaters, box: MapBox, ask: CodedMapAsk): StillWaters | null {
  const cut = cutWaters(held.tiles, stillCut(box), { rivers: ask.rivers ?? [], dams: ask.dams ?? [] });
  const plain = ask.layers.includes("rivers") && showsWaters(box) ? cut.d : null;
  const kept = { ...cut, d: plain };
  return drawsWaters(kept) ? kept : null;
}

export function codedStillBase(layers: StillLayers, box: MapBox, ask: CodedMapAsk, held: HeldWaters): CodedStillBase {
  const cut = stillCut(box);
  const [india = [], ...bands] = layers.relief;
  const homes = ask.districts.flatMap((lgd) => layers.homes.get(lgd) ?? []);
  return {
    box,
    grid: STILL_GRID,
    land: cutRings(india, cut) || null,
    relief: ask.layers.includes("relief") ? bands.map((rings) => cutRings(rings, cut)) : null,
    rivers: ask.layers.includes("rivers") ? cutLines(layers.rivers.flatMap((group) => group.lines), cut) || null : null,
    districts: drawsDistrictLines(box, ask.layers) ? cutLines([...layers.homes.values()].flat(), cut) || null : null,
    states: cutLines(layers.stateLines, cut) || null,
    homes: cutRings(homes, cut) || null,
    waters: stillWaters(held, box, ask)
  };
}

export function namedRiverPaths(tiles: readonly HeldTile[], names: readonly string[]): CodedRiverPath[] {
  const rivers = tiles.flatMap((tile) => tile.rivers);
  return names.flatMap((name) => {
    const d = absolutePath(rivers.filter((river) => answersTo(river.names, name)).flatMap((river) => river.lines));
    return d ? [{ name, d }] : [];
  });
}

export function namedDams(tiles: readonly HeldTile[], names: readonly string[]): CodedDam[] {
  return tiles
    .flatMap((tile) => tile.dams)
    .filter((dam) => names.some((name) => answersTo([dam.name], name)))
    .map((dam) => ({ name: dam.name, x: Number(tenths(dam.at.x)), y: Number(tenths(dam.at.y)) }));
}

export function codedBase(layers: StillLayers, box: MapBox, ask: CodedMapAsk, held: HeldWaters): CodedBase {
  return { still: codedStillBase(layers, box, ask, held), rivers: namedRiverPaths(held.tiles, ask.rivers ?? []), dams: namedDams(held.tiles, ask.dams ?? []) };
}
