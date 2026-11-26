import type { DatasetRow } from "@/lib/mapPhysical";

export type WatersRiver = { id: number; name: string; kind: string; districts: number[]; also?: string[]; agrees?: { name: string; source: string }[]; lines: string };
export type WatersDam = { ref: string; name: string; namedBy: string; longitude: number; latitude: number; districts: number[] };
export type WatersTile = { schemaVersion: number; tile: string; bounds: number[]; rivers: WatersRiver[]; dams: WatersDam[]; plain?: string };
export type WatersTileRow = { id: string; bounds: number[]; rivers: number; dams: number };
export type WatersIndex = { schemaVersion: number; source: string; site: string; licence: string; datasets: DatasetRow[]; bounds: number[]; tileDegrees: number; tolerance: number; tiles: WatersTileRow[] };

export function answersTo(names: readonly string[], asked: string): boolean {
  return names.includes(asked);
}

export function riverNames(river: Pick<WatersRiver, "name" | "also">): string[] {
  return [river.name, ...(river.also ?? [])];
}
