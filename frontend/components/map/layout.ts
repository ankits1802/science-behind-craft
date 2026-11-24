import type { MapBox } from "@/components/map/basemap";
import { project, VIEW_BOX } from "@/components/map/projection";

export interface MapPoint {
  key: string;
  name: string;
  latitude: number;
  longitude: number;
  total: number;
  caption?: string | null;
  countText?: string | null;
  pinLabel?: string | null;
  href?: string | null;
}

const MIN_RADIUS = 12.5;
const MAX_RADIUS = 26;
const GAP = 3;
const MAX_SHIFT = 46;
const MAX_PASSES = 60;
const MOVED = 0.75;

export const WHOLE_MAP: MapBox = { x: 0, y: 0, width: VIEW_BOX.width, height: VIEW_BOX.height };

export type PlacedPin = {
  point: MapPoint;
  x: number;
  y: number;
  anchorX: number;
  anchorY: number;
  radius: number;
  displaced: boolean;
};

type Spot = { x: number; y: number };

export function pinRadius(total: number, busiest: number): number {
  if (busiest <= 0) return MIN_RADIUS;
  const share = Math.sqrt(total) / Math.sqrt(busiest);
  return MIN_RADIUS + (MAX_RADIUS - MIN_RADIUS) * share;
}

export function frameScale(frame: MapBox): number {
  return frame.width / VIEW_BOX.width;
}

function pushedClear(placed: readonly PlacedPin[], key: string, anchor: Spot, radius: number, scale: number): Spot {
  let { x, y } = anchor;
  for (let pass = 0; pass < MAX_PASSES; pass += 1) {
    const clash = placed.find((other) => Math.hypot(other.x - x, other.y - y) < other.radius + radius + GAP * scale);
    if (!clash) break;
    let dx = x - clash.x;
    let dy = y - clash.y;
    let distance = Math.hypot(dx, dy);
    if (distance < 0.001) {
      const angle = (hash(key) % 360) * (Math.PI / 180);
      dx = Math.cos(angle);
      dy = Math.sin(angle);
      distance = 1;
    }
    const push = (clash.radius + radius + GAP * scale - distance) / distance;
    x += dx * push;
    y += dy * push;
    const drift = Math.hypot(x - anchor.x, y - anchor.y);
    if (drift > MAX_SHIFT * scale) {
      return { x: anchor.x + ((x - anchor.x) / drift) * MAX_SHIFT * scale, y: anchor.y + ((y - anchor.y) / drift) * MAX_SHIFT * scale };
    }
  }
  return { x, y };
}

export function layoutPins(points: MapPoint[], frame: MapBox = WHOLE_MAP): PlacedPin[] {
  const scale = frameScale(frame);
  const busiest = points.reduce((most, point) => Math.max(most, point.total), 0);
  const ordered = [...points].sort((a, b) => b.total - a.total || a.key.localeCompare(b.key));
  const placed: PlacedPin[] = [];
  for (const point of ordered) {
    const { x: anchorX, y: anchorY } = project(point.longitude, point.latitude);
    const radius = pinRadius(point.total, busiest) * scale;
    const spot = pushedClear(placed, point.key, { x: anchorX, y: anchorY }, radius, scale);
    const x = clamp(spot.x, frame.x + radius, frame.x + frame.width - radius);
    const y = clamp(spot.y, frame.y + radius, frame.y + frame.height - radius);
    placed.push({ point, x, y, anchorX, anchorY, radius, displaced: Math.hypot(x - anchorX, y - anchorY) > MOVED * scale });
  }
  return placed.sort((a, b) => b.radius - a.radius);
}

function clamp(value: number, low: number, high: number): number {
  return Math.min(high, Math.max(low, value));
}

function hash(text: string): number {
  let value = 0;
  for (let index = 0; index < text.length; index += 1) {
    value = (value * 31 + text.charCodeAt(index)) >>> 0;
  }
  return value;
}
