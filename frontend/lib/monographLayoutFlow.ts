import type { MonographDocument, MonographLayoutEntry } from "@/lib/monographDocument";
import { layoutSizes, proseLines, pullQuotes, setInProse, type PlacedSize } from "@/lib/monographPlacement";
import { hasSentence } from "@/lib/monographRender";

export type LayoutPlacing = { loose: ReadonlySet<string>; lines: ReadonlySet<string>; pulls: ReadonlySet<string>; sizes: ReadonlyMap<string, PlacedSize> };
export type ChapterFlow = { flow: MonographLayoutEntry[]; loose: MonographLayoutEntry[] };

const TITLE_TAG = "h2";

export function layoutPlacing(document: MonographDocument): LayoutPlacing {
  if (document.shell !== null) return { loose: new Set(), lines: new Set(), pulls: new Set(), sizes: new Map() };
  return { loose: setInProse(document), lines: proseLines(document), pulls: pullQuotes(document), sizes: layoutSizes(document) };
}

function afterLede(document: MonographDocument, flow: readonly MonographLayoutEntry[], sentences: number): number {
  const units = document.content.units;
  const told = (entry: MonographLayoutEntry | undefined) => entry?.kind === "unit" && units[entry.ref]?.tag === "p" && hasSentence(units[entry.ref].nodes);
  const title = flow.findIndex((entry) => entry.kind === "unit" && units[entry.ref]?.tag === TITLE_TAG);
  let at = title + 1;
  while (at - title - 1 < sentences && told(flow[at])) at += 1;
  return at;
}

export function chapterFlow(document: MonographDocument, entries: readonly MonographLayoutEntry[], placing: LayoutPlacing, sentences: number): ChapterFlow {
  const loose = entries.filter((entry) => entry.kind === "component" && placing.loose.has(entry.ref));
  const lines = entries.filter((entry) => entry.kind === "unit" && placing.lines.has(entry.ref));
  const set = new Set([...loose, ...lines]);
  const flow = entries.filter((entry) => !set.has(entry));
  if (!lines.length) return { flow, loose };
  const at = afterLede(document, flow, sentences);
  return { flow: [...flow.slice(0, at), ...lines, ...flow.slice(at)], loose };
}
