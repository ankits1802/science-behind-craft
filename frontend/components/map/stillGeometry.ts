import type { MapBox } from "@/components/map/basemap";
import type { Projected } from "@/components/map/projection";

export type GridPoint = readonly [number, number];
export type StillCut = { box: MapBox; clip: MapBox; units: number; tolerance: number; speck: number };

type Side = { inside: (point: Projected) => boolean; cross: (from: Projected, to: Projected) => Projected };

const acrossX = (x: number) => (from: Projected, to: Projected): Projected => ({ x, y: from.y + ((to.y - from.y) * (x - from.x)) / (to.x - from.x) });
const acrossY = (y: number) => (from: Projected, to: Projected): Projected => ({ x: from.x + ((to.x - from.x) * (y - from.y)) / (to.y - from.y), y });

function sides(box: MapBox): Side[] {
  const right = box.x + box.width;
  const bottom = box.y + box.height;
  return [
    { inside: (point) => point.x >= box.x, cross: acrossX(box.x) },
    { inside: (point) => point.x <= right, cross: acrossX(right) },
    { inside: (point) => point.y >= box.y, cross: acrossY(box.y) },
    { inside: (point) => point.y <= bottom, cross: acrossY(bottom) }
  ];
}

function clippedToSide(points: readonly Projected[], side: Side): Projected[] {
  const kept: Projected[] = [];
  points.forEach((point, at) => {
    const before = points[(at + points.length - 1) % points.length];
    if (side.inside(point)) {
      if (!side.inside(before)) kept.push(side.cross(before, point));
      kept.push(point);
    } else if (side.inside(before)) kept.push(side.cross(before, point));
  });
  return kept;
}

export function clippedRing(ring: readonly Projected[], box: MapBox): Projected[] {
  return sides(box).reduce<Projected[]>((points, side) => (points.length ? clippedToSide(points, side) : points), [...ring]);
}

function insideBox(box: MapBox, point: Projected | undefined): boolean {
  return point !== undefined && point.x >= box.x && point.x <= box.x + box.width && point.y >= box.y && point.y <= box.y + box.height;
}

export function clippedLine(line: readonly Projected[], box: MapBox): Projected[][] {
  const runs: Projected[][] = [];
  let run: Projected[] = [];
  line.forEach((point, at) => {
    if (insideBox(box, point) || insideBox(box, line[at - 1]) || insideBox(box, line[at + 1])) {
      run.push(point);
      return;
    }
    if (run.length >= 2) runs.push(run);
    run = [];
  });
  if (run.length >= 2) runs.push(run);
  return runs;
}

function offset(point: Projected, start: Projected, end: Projected): number {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const length = Math.hypot(dx, dy);
  if (length === 0) return Math.hypot(point.x - start.x, point.y - start.y);
  return Math.abs(dy * point.x - dx * point.y + end.x * start.y - end.y * start.x) / length;
}

function farthest(points: readonly Projected[], start: number, end: number, tolerance: number): number | null {
  let found: number | null = null;
  let most = tolerance;
  for (let at = start + 1; at < end; at += 1) {
    const distance = offset(points[at], points[start], points[end]);
    if (distance > most) {
      most = distance;
      found = at;
    }
  }
  return found;
}

export function simplified(points: readonly Projected[], tolerance: number): Projected[] {
  if (points.length < 3) return [...points];
  const kept = new Set<number>([0, points.length - 1]);
  const spans: (readonly [number, number])[] = [[0, points.length - 1]];
  for (let span = spans.pop(); span !== undefined; span = spans.pop()) {
    const far = farthest(points, span[0], span[1], tolerance);
    if (far === null) continue;
    kept.add(far);
    spans.push([span[0], far], [far, span[1]]);
  }
  return points.filter((_, at) => kept.has(at));
}

export function gridPoints(points: readonly Projected[], origin: Projected, units: number): GridPoint[] {
  const placed: GridPoint[] = [];
  for (const point of points) {
    const next: GridPoint = [Math.round((point.x - origin.x) * units), Math.round((point.y - origin.y) * units)];
    const last = placed[placed.length - 1];
    if (!last || last[0] !== next[0] || last[1] !== next[1]) placed.push(next);
  }
  return placed;
}

export function gridArea(ring: readonly GridPoint[]): number {
  let twice = 0;
  ring.forEach((point, at) => {
    const before = ring[(at + ring.length - 1) % ring.length];
    twice += before[0] * point[1] - point[0] * before[1];
  });
  return Math.abs(twice) / 2;
}

const figure = (value: number, per: number) => String(value / per);

export function relativePath(points: readonly GridPoint[], closed: boolean, per = 1): string {
  const [first, ...rest] = points;
  if (!first) return "";
  const steps = rest.map((point, at) => {
    const before = points[at];
    return `${figure(point[0] - before[0], per)} ${figure(point[1] - before[1], per)}`;
  });
  const drawn = `M${figure(first[0], per)} ${figure(first[1], per)}${steps.length ? `l${steps.join(" ")}` : ""}${closed ? "z" : ""}`;
  return drawn.replace(/ -/g, "-");
}

function closedRing(points: readonly GridPoint[]): GridPoint[] {
  const [first] = points;
  const last = points[points.length - 1];
  return first && last && points.length > 1 && first[0] === last[0] && first[1] === last[1] ? points.slice(0, -1) : [...points];
}

export function cutRings(rings: readonly (readonly Projected[])[], cut: StillCut): string {
  const origin = { x: cut.box.x, y: cut.box.y };
  return rings
    .map((ring) => closedRing(gridPoints(simplified(clippedRing(ring, cut.clip), cut.tolerance), origin, cut.units)))
    .filter((ring) => ring.length >= 3 && gridArea(ring) >= cut.speck)
    .map((ring) => relativePath(ring, true))
    .join("");
}

export function cutLines(lines: readonly (readonly Projected[])[], cut: StillCut): string {
  const origin = { x: cut.box.x, y: cut.box.y };
  return lines
    .flatMap((line) => clippedLine(line, cut.clip))
    .map((run) => gridPoints(simplified(run, cut.tolerance), origin, cut.units))
    .filter((run) => run.length >= 2)
    .map((run) => relativePath(run, false))
    .join("");
}
