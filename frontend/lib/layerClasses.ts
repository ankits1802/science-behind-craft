import type { LayerClass, MapLayer } from "@/lib/regionContract";

export const VIEW_CLASS_MAX = 5;
export const BREAK_FIGURES = 3;

function inclusiveCuts(ordered: readonly number[], groups: number): number[] {
  const span = ordered.length - 1;
  const cuts: number[] = [];
  for (let step = 1; step < groups; step += 1) {
    const at = Math.floor((step * span) / groups);
    const share = step * span - at * groups;
    cuts.push((ordered[at] * (groups - share) + ordered[at + 1] * share) / groups);
  }
  return cuts;
}

function figures(value: number): number {
  return Number(value.toPrecision(BREAK_FIGURES));
}

export function viewClasses(values: readonly number[]): LayerClass[] {
  if (values.length === 0) throw new RangeError("a view needs at least one value to class");
  const ordered = [...values].sort((a, b) => a - b);
  const low = ordered[0];
  const high = ordered[ordered.length - 1];
  const groups = Math.min(VIEW_CLASS_MAX, new Set(ordered).size);
  const cuts = ordered.length > 1 && groups > 1 ? inclusiveCuts(ordered, groups) : [];
  const inner = [...new Set(cuts.map(figures).filter((cut) => low < cut && cut < high))].sort((a, b) => a - b);
  const breaks = [low, ...inner, high];
  return breaks.slice(1).map((max, index) => ({ min: breaks[index], max }));
}

export function layerInView(layer: MapLayer, lgds: Iterable<number>): MapLayer | null {
  const shown = Object.fromEntries([...new Set(lgds)].flatMap((lgd) => (layer.values[String(lgd)] === undefined ? [] : [[String(lgd), layer.values[String(lgd)]]])));
  const values = Object.values(shown);
  if (values.length === 0) return null;
  return { ...layer, values: shown, classes: viewClasses(values) };
}
