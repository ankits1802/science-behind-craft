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

export type PlacedPin = {
  point: MapPoint;
  x: number;
  y: number;
  anchorX: number;
  anchorY: number;
  radius: number;
  displaced: boolean;
};

export function pinRadius(total: number, busiest: number): number {
  if (busiest <= 0) return MIN_RADIUS;
  const share = Math.sqrt(total) / Math.sqrt(busiest);
  return MIN_RADIUS + (MAX_RADIUS - MIN_RADIUS) * share;
}

export function layoutPins(points: MapPoint[]): PlacedPin[] {
  const busiest = points.reduce((most, point) => Math.max(most, point.total), 0);
  const ordered = [...points].sort((a, b) => b.total - a.total || a.key.localeCompare(b.key));

  const placed: PlacedPin[] = [];
  for (const point of ordered) {
    const { x: anchorX, y: anchorY } = project(point.longitude, point.latitude);
    const radius = pinRadius(point.total, busiest);
    let x = anchorX;
    let y = anchorY;

    for (let pass = 0; pass < MAX_PASSES; pass += 1) {
      const clash = placed.find((other) => Math.hypot(other.x - x, other.y - y) < other.radius + radius + GAP);
      if (!clash) break;

      const needed = clash.radius + radius + GAP;
      let dx = x - clash.x;
      let dy = y - clash.y;
      let distance = Math.hypot(dx, dy);
      if (distance < 0.001) {
        const angle = (hash(point.key) % 360) * (Math.PI / 180);
        dx = Math.cos(angle);
        dy = Math.sin(angle);
        distance = 1;
      }
      const push = (needed - distance) / distance;
      x += dx * push;
      y += dy * push;

      const drift = Math.hypot(x - anchorX, y - anchorY);
      if (drift > MAX_SHIFT) {
        x = anchorX + ((x - anchorX) / drift) * MAX_SHIFT;
        y = anchorY + ((y - anchorY) / drift) * MAX_SHIFT;
        break;
      }
    }

    x = clamp(x, radius, VIEW_BOX.width - radius);
    y = clamp(y, radius, VIEW_BOX.height - radius);

    placed.push({
      point,
      x,
      y,
      anchorX,
      anchorY,
      radius,
      displaced: Math.hypot(x - anchorX, y - anchorY) > 0.75
    });
  }

  return placed.sort((a, b) => b.radius - a.radius);
}

export function bloomDelays(pins: readonly PlacedPin[], bloom: number): Map<string, number> {
  const delays = new Map<string, number>();
  if (pins.length === 0) return delays;
  const centreX = pins.reduce((sum, pin) => sum + pin.x, 0) / pins.length;
  const centreY = pins.reduce((sum, pin) => sum + pin.y, 0) / pins.length;
  let furthest = 0;
  for (const pin of pins) furthest = Math.max(furthest, Math.hypot(pin.x - centreX, pin.y - centreY));
  for (const pin of pins) {
    const share = furthest === 0 ? 0 : Math.hypot(pin.x - centreX, pin.y - centreY) / furthest;
    delays.set(pin.point.key, share * bloom);
  }
  return delays;
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
