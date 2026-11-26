import type { Molecule3dBlock } from "@/lib/explainerMatter";
import type { ZoomCompound, ZoomLevel, ZoomLevelName, ZoomStoryBlock } from "@/lib/explainerPlay";

export const ZOOM_LEVEL_LABEL: Record<ZoomLevelName, string> = {
  DISTRICT: "District",
  WORKSHOP: "Workshop",
  CLOTH: "Cloth",
  FIBRE: "Fibre",
  MOLECULE: "Molecule"
};

export function zoomLevelName(level: ZoomLevel): string {
  if (level.district) return level.district.name;
  if (level.compound) return level.compound.name;
  return level.media?.title ?? ZOOM_LEVEL_LABEL[level.level];
}

export function zoomSummary(block: ZoomStoryBlock): string {
  return block.levels.map(zoomLevelName).join(" → ");
}

export function zoomLevelLine(level: ZoomLevel, index: number, count: number): string {
  return `${ZOOM_LEVEL_LABEL[level.level]} · ${index + 1} of ${count}`;
}

export function zoomMolecule(blockId: string, compound: ZoomCompound): Molecule3dBlock {
  return { id: `${blockId}.molecule`, kind: "molecule_3d", version: 1, reuse: null, ...compound };
}

export const ZOOM_LEVEL_MS = 4800;

export function zoomBeat(): number {
  return ZOOM_LEVEL_MS;
}

export function zoomStatus(block: ZoomStoryBlock, at: number): string {
  const level = block.levels[at];
  return level ? `${zoomLevelLine(level, at, block.levels.length)}: ${zoomLevelName(level)}` : "";
}
