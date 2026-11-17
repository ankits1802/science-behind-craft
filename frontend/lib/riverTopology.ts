import { apiFetch } from "@/lib/api";
import { RIVER_BASIN_PATH, RIVER_REACHES_OBJECT } from "@/lib/explainerPlace";
import { integer, list, number, object, oneOf, optional, parseShape, ShapeError, type Shape } from "@/lib/shape";

export type LonLat = [number, number];
export type BasinReach = { id: number; nextDown: number; ordStra: number; line: LonLat[] };
export type RiverBasin = { mainRiv: number; reaches: Map<number, BasinReach> };

type Pair = [number, number];
type ReachGeometry = { type: "LineString"; id: number; arcs: number[]; properties: { nextDown: number; ordStra: number } };
type Transform = { scale: Pair; translate: Pair };
type ReachCollection = { type: "GeometryCollection"; geometries: ReachGeometry[] };
type RiverTopologyFile = {
  type: "Topology";
  bbox?: number[];
  transform?: Transform;
  objects: { [RIVER_REACHES_OBJECT]: ReachCollection };
  arcs: Pair[][];
};

const OUTLET = 0;

function positionOf(value: unknown): Pair | null {
  if (!Array.isArray(value) || value.length < 2) return null;
  const [x, y] = value;
  return typeof x === "number" && typeof y === "number" && Number.isFinite(x) && Number.isFinite(y) ? [x, y] : null;
}

const pair: Shape<Pair> = {
  expected: "two numbers",
  parse(value, path) {
    const found = positionOf(value);
    if (!found || (value as unknown[]).length !== 2) throw new ShapeError(path, "two numbers");
    return found;
  }
};

const arcsShape: Shape<Pair[][]> = {
  expected: "arcs of at least two positions",
  parse(value, path) {
    if (!Array.isArray(value)) throw new ShapeError(path, "a list of arcs");
    return value.map((arc: unknown, at) => {
      if (!Array.isArray(arc) || arc.length < 2) throw new ShapeError(`${path}[${at}]`, "an arc of at least two positions");
      return arc.map((entry: unknown, index) => {
        const found = positionOf(entry);
        if (!found) throw new ShapeError(`${path}[${at}][${index}]`, "a position");
        return found;
      });
    });
  }
};

const reachGeometryShape: Shape<ReachGeometry> = object<ReachGeometry>({
  type: oneOf(["LineString"] as const),
  id: integer,
  arcs: list(integer, 1),
  properties: object<ReachGeometry["properties"]>({ nextDown: integer, ordStra: integer })
});

const topologyShape: Shape<RiverTopologyFile> = object<RiverTopologyFile>({
  type: oneOf(["Topology"] as const),
  bbox: optional(list(number, 4)),
  transform: optional(object<Transform>({ scale: pair, translate: pair })),
  objects: object<RiverTopologyFile["objects"]>({
    [RIVER_REACHES_OBJECT]: object<ReachCollection>({ type: oneOf(["GeometryCollection"] as const), geometries: list(reachGeometryShape, 1) })
  }),
  arcs: arcsShape
});

function decodedArcs(file: RiverTopologyFile): LonLat[][] {
  const transform = file.transform;
  if (!transform) return file.arcs.map((arc) => arc.map(([x, y]) => [x, y]));
  const [scaleX, scaleY] = transform.scale;
  const [shiftX, shiftY] = transform.translate;
  return file.arcs.map((arc) => {
    let x = 0;
    let y = 0;
    return arc.map(([dx, dy]) => {
      x += dx;
      y += dy;
      return [x * scaleX + shiftX, y * scaleY + shiftY];
    });
  });
}

function arcAt(arcs: readonly LonLat[][], index: number, reachId: number): LonLat[] {
  const arc = arcs[index >= 0 ? index : ~index];
  if (!arc) throw new ShapeError(`reach ${reachId}.arcs`, `arc indexes below ${arcs.length}`);
  return index >= 0 ? arc : [...arc].reverse();
}

function onEarth([longitude, latitude]: LonLat): boolean {
  return Math.abs(longitude) <= 180 && Math.abs(latitude) <= 90;
}

function reachLine(geometry: ReachGeometry, arcs: readonly LonLat[][]): LonLat[] {
  const line = geometry.arcs.flatMap((index, at) => {
    const arc = arcAt(arcs, index, geometry.id);
    return at === 0 ? arc : arc.slice(1);
  });
  if (!line.every(onEarth)) throw new ShapeError(`reach ${geometry.id}`, "longitudes and latitudes");
  return line;
}

export function riverBasinOf(value: unknown, mainRiv: number): RiverBasin {
  const file = parseShape(topologyShape, value);
  const arcs = decodedArcs(file);
  const reaches = new Map<number, BasinReach>();
  for (const geometry of file.objects[RIVER_REACHES_OBJECT].geometries) {
    if (reaches.has(geometry.id)) throw new ShapeError(`reach ${geometry.id}`, "one geometry per reach");
    reaches.set(geometry.id, { id: geometry.id, nextDown: geometry.properties.nextDown, ordStra: geometry.properties.ordStra, line: reachLine(geometry, arcs) });
  }
  if (reaches.get(mainRiv)?.nextDown !== OUTLET) throw new ShapeError(`basin ${mainRiv}`, `its outlet reach ${mainRiv}`);
  return { mainRiv, reaches };
}

const pending = new Map<number, Promise<RiverBasin>>();

export function fetchRiverBasin(mainRiv: number): Promise<RiverBasin> {
  const existing = pending.get(mainRiv);
  if (existing) return existing;
  const request = apiFetch<unknown>(RIVER_BASIN_PATH(mainRiv), {}, { revalidateFromHttpCache: true })
    .then((body) => riverBasinOf(body, mainRiv))
    .catch((cause: unknown) => {
      pending.delete(mainRiv);
      throw cause;
    });
  pending.set(mainRiv, request);
  return request;
}
