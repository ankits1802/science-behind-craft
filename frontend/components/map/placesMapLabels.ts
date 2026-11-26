import type { MapBox } from "@/components/map/basemap";
import { ringRadii } from "@/components/map/mapDistance";
import { PEAK_TIERS } from "@/components/map/physical/ReliefLayer";
import { project, type Projected } from "@/components/map/projection";
import type { StillWaters } from "@/components/map/waterLayer";
import type { MapPlace } from "@/lib/componentSpecsGeneral";
import type { MapRingSpec, ShownMarks } from "@/lib/componentSpecsMapLayer";
import type { ReliefFile, RiversFile } from "@/lib/mapPhysical";
import { formatNumber } from "@/lib/measure";

export const RING_LABEL_AT = Math.SQRT1_2;
export const RING_LABEL_GAP = 4;
export const PEAK_GAP = 3;
export const DAM_GAP = 9;

export type LabelAnchor = "start" | "middle" | "end";
export type LabelWeight = "normal" | "medium" | "semibold";
export type MapLabel = {
  key: string;
  at: Projected;
  text: string;
  angle: number;
  anchor: LabelAnchor;
  dx: number;
  lift: boolean;
  tone: string;
  italic: boolean;
  weight: LabelWeight;
  tier: number | null;
  numeric: boolean;
};
export type PeakLabel = { key: string; at: Projected; label: MapLabel; tier: number };

const PLAIN: Omit<MapLabel, "key" | "at" | "text"> = { angle: 0, anchor: "middle", dx: 0, lift: false, tone: "var(--map-label)", italic: false, weight: "normal", tier: null, numeric: false };

export function mapLabel(key: string, at: Projected, text: string, options: Partial<Omit<MapLabel, "key" | "at" | "text">> = {}): MapLabel {
  return { ...PLAIN, ...options, key, at, text };
}

export function inFrame(frame: MapBox, at: Projected): boolean {
  return at.x >= frame.x && at.x <= frame.x + frame.width && at.y >= frame.y && at.y <= frame.y + frame.height;
}

export function frameShare(frame: MapBox, at: Projected): { x: string; y: string } {
  const share = (value: number, start: number, size: number) => `${(((value - start) / size) * 100).toFixed(3)}%`;
  return { x: share(at.x, frame.x, frame.width), y: share(at.y, frame.y, frame.height) };
}

export function riverLabels(file: Pick<RiversFile, "labels"> | null, frame: MapBox, named: readonly string[]): MapLabel[] {
  if (!file) return [];
  return file.labels.flatMap((label) => {
    const at = project(label.longitude, label.latitude);
    if (!inFrame(frame, at)) return [];
    const strong = named.includes(label.text);
    return [mapLabel(`river-${label.text}`, at, label.text, { angle: label.angle, lift: true, italic: true, tone: "var(--map-water-label)", weight: strong ? "medium" : "normal", tier: strong ? null : label.tier })];
  });
}

export function rangeLabels(file: Pick<ReliefFile, "ranges"> | null, frame: MapBox): MapLabel[] {
  if (!file) return [];
  return file.ranges.flatMap((range) => {
    const at = project(range.longitude, range.latitude);
    return inFrame(frame, at) ? [mapLabel(`range-${range.text}`, at, range.text, { angle: range.angle, weight: "medium", tier: range.tier })] : [];
  });
}

export function peakLabels(file: Pick<ReliefFile, "peaks"> | null, frame: MapBox, size: number): PeakLabel[] {
  if (!file) return [];
  return file.peaks.flatMap((peak) => {
    const placed = PEAK_TIERS[peak.name];
    const at = project(peak.longitude, peak.latitude);
    if (!placed || !inFrame(frame, at)) return [];
    const dx = (size + PEAK_GAP) * (placed.side === "start" ? 1 : -1);
    return [{ key: `peak-${peak.name}`, at, tier: placed.tier, label: mapLabel(`peak-${peak.name}`, at, peak.text, { dx, anchor: placed.side, tone: "var(--ink-2)" }) }];
  });
}

export function ringLabels(rings: readonly MapRingSpec[], places: readonly MapPlace[], marks: ShownMarks, frame: MapBox): MapLabel[] {
  return rings.flatMap((ring, index) => {
    const place = places[ring.place];
    if (!marks.rings.has(index) || !place) return [];
    const centre = project(place.longitude, place.latitude);
    const { rx, ry } = ringRadii(place, ring.radiusKm);
    const at = { x: centre.x + rx * RING_LABEL_AT, y: centre.y + ry * RING_LABEL_AT };
    return inFrame(frame, at) ? [mapLabel(`ring-${ring.place}-${ring.radiusKm}`, at, `${formatNumber(ring.radiusKm)} km`, { anchor: "start", dx: RING_LABEL_GAP, weight: "medium" })] : [];
  });
}

export function valueLabels(values: readonly { lgd: number; x: number; y: number; text: string }[], frame: MapBox): MapLabel[] {
  return values.flatMap((value) => {
    const at = { x: value.x, y: value.y };
    return inFrame(frame, at) ? [mapLabel(`value-${value.lgd}`, at, value.text, { weight: "semibold", numeric: true })] : [];
  });
}

export function waterLabels(waters: StillWaters | null, frame: MapBox): MapLabel[] {
  return (waters?.strong ?? []).flatMap((river) => {
    const at = { x: river.x, y: river.y };
    return inFrame(frame, at) ? [mapLabel(`water-${river.name}`, at, river.name, { lift: true, italic: true, tone: "var(--map-water-label)", weight: "medium" })] : [];
  });
}

export function damLabels(waters: StillWaters | null, frame: MapBox): MapLabel[] {
  return (waters?.dams ?? []).flatMap((dam) => {
    const at = { x: dam.x, y: dam.y };
    return inFrame(frame, at) ? [mapLabel(`dam-${dam.name}-${dam.x}-${dam.y}`, at, dam.name, { anchor: "start", dx: DAM_GAP, weight: "medium" })] : [];
  });
}
