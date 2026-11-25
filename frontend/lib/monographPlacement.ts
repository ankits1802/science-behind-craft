import type { MonographDocument } from "@/lib/monographDocument";

export const PAGE_LAYOUT_DATA = "page-layout";
export const MASTHEAD_ROLES: readonly string[] = ["HERO", "OPENER"];
export const PLACED_SIZES = ["MARGIN", "COLUMN", "WIDE", "BLEED"] as const;
export const BODY_ROLE = "BODY";
export const PULL_QUOTE_ROLE = "PULL_QUOTE";
export const ROLE_SIZES: Readonly<Record<string, PlacedSize>> = { SIDEBAR: "MARGIN", OPENER: "WIDE", PLATE: "COLUMN" };
const PICTURE_KIND = "picture_plate";

export type PlacedSize = (typeof PLACED_SIZES)[number];
export type PlacedCrop = { x: number; y: number; width: number; height: number };
export type PlacedEntry = { ref: string; chapter: string; role: string; order: number; size: PlacedSize | null; crop: PlacedCrop | null };
export type FrameCrop = PlacedCrop & { ratio: number };
export type SlotPlacement = { size: PlacedSize | null; crop: FrameCrop | null };

export const UNPLACED: SlotPlacement = { size: null, crop: null };

function fraction(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1 ? value : null;
}

function cropOf(value: unknown): PlacedCrop | null {
  if (!value || typeof value !== "object") return null;
  const box = value as Record<string, unknown>;
  const [x, y, width, height] = [box.x, box.y, box.width, box.height].map(fraction);
  if (x === null || y === null || width === null || height === null || width === 0 || height === 0) return null;
  return x + width <= 1 && y + height <= 1 ? { x, y, width, height } : null;
}

function sizeOf(value: unknown): PlacedSize | null {
  return PLACED_SIZES.find((size) => size === value) ?? null;
}

export function placedEntries(document: MonographDocument): PlacedEntry[] {
  const value = document.content.data[PAGE_LAYOUT_DATA];
  const entries = value && typeof value === "object" ? (value as { entries?: unknown }).entries : null;
  if (!Array.isArray(entries)) return [];
  return entries.flatMap((entry) => {
    if (!entry || typeof entry !== "object") return [];
    const { ref, chapter, role, order, size, crop } = entry as Record<string, unknown>;
    if (typeof ref !== "string" || typeof chapter !== "string" || typeof role !== "string") return [];
    return [{ ref, chapter, role, order: typeof order === "number" ? order : 0, size: sizeOf(size), crop: cropOf(crop) }];
  });
}

export function entrySize(entry: PlacedEntry): PlacedSize | null {
  return entry.size ?? (Object.hasOwn(ROLE_SIZES, entry.role) ? ROLE_SIZES[entry.role] : null);
}

export function layoutSizes(document: MonographDocument): Map<string, PlacedSize> {
  const sized = placedEntries(document).flatMap((entry) => {
    const size = entrySize(entry);
    return size ? [[entry.ref, size] as const] : [];
  });
  return new Map(sized);
}

export function arrangedLabels(document: MonographDocument): Set<string> {
  return new Set(placedEntries(document).map((entry) => entry.ref));
}

export function proseArranged(document: MonographDocument): Set<string> {
  const units = document.content.units;
  return new Set(placedEntries(document).filter((entry) => entry.role === BODY_ROLE && Object.hasOwn(units, entry.ref)).map((entry) => entry.chapter));
}

export function setInProse(document: MonographDocument): Set<string> {
  const arranged = proseArranged(document);
  const units = document.content.units;
  return new Set(placedEntries(document).filter((entry) => !arranged.has(entry.chapter) && !MASTHEAD_ROLES.includes(entry.role) && !Object.hasOwn(units, entry.ref)).map((entry) => entry.ref));
}

export function proseLines(document: MonographDocument): Set<string> {
  const arranged = proseArranged(document);
  const units = document.content.units;
  return new Set(placedEntries(document).filter((entry) => !arranged.has(entry.chapter) && entry.role !== BODY_ROLE && Object.hasOwn(units, entry.ref)).map((entry) => entry.ref));
}

export function pullQuotes(document: MonographDocument): Set<string> {
  return new Set(placedEntries(document).filter((entry) => entry.role === PULL_QUOTE_ROLE).map((entry) => entry.ref));
}

function pictureOf(document: MonographDocument, label: string): { width: number; height: number } | null {
  const spec = Object.hasOwn(document.specs, label) ? document.specs[label] : null;
  const picture = spec?.picture;
  if (!picture || typeof picture !== "object") return null;
  const { width, height } = picture as Record<string, unknown>;
  return typeof width === "number" && typeof height === "number" && width > 0 && height > 0 ? { width, height } : null;
}

export function frameCrop(document: MonographDocument, label: string): FrameCrop | null {
  const crop = placedEntries(document).find((entry) => entry.ref === label)?.crop ?? null;
  const picture = crop ? pictureOf(document, label) : null;
  if (!crop || !picture) return null;
  return { ...crop, ratio: (crop.width * picture.width) / (crop.height * picture.height) };
}

export function slotPlacement(document: MonographDocument, label: string, beside: boolean): SlotPlacement {
  if (document.shell !== null) return UNPLACED;
  const placed = layoutSizes(document).get(label) ?? null;
  const size = beside ? "MARGIN" : placed === "MARGIN" ? "COLUMN" : placed;
  return { size, crop: frameCrop(document, label) };
}

export function croppedDocument(document: MonographDocument): MonographDocument {
  if (document.shell !== null) return document;
  const crops = placedEntries(document).filter((entry) => entry.crop !== null && pictureOf(document, entry.ref) !== null);
  if (!crops.length) return document;
  const specs = { ...document.specs };
  for (const entry of crops) {
    const spec = specs[entry.ref];
    specs[entry.ref] = { ...spec, picture: { ...(spec.picture as object), focal: entry.crop } };
  }
  return { ...document, specs };
}

export function placedMastheadPicture(document: MonographDocument): string | null {
  const pictures = new Set(document.content.components.filter((component) => component.kind === PICTURE_KIND).map((component) => component.label));
  const chapters = [...new Set(document.content.layout.map((entry) => entry.chapter))];
  const rank = (placed: PlacedEntry) => [MASTHEAD_ROLES.indexOf(placed.role), chapters.indexOf(placed.chapter), placed.order];
  const found = placedEntries(document)
    .filter((placed) => pictures.has(placed.ref) && MASTHEAD_ROLES.includes(placed.role) && chapters.includes(placed.chapter))
    .sort((a, b) => {
      const [left, right] = [rank(a), rank(b)];
      return left[0] - right[0] || left[1] - right[1] || left[2] - right[2];
    });
  return found[0]?.ref ?? null;
}
