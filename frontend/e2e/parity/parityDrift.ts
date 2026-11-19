import type { Page } from "@playwright/test";

export type DriftStep = { before: string; after: string; delta: number };
export type HeightRecord = { path: string; depth: number; height: string; width: string; style: string };
export type DriftReport = { step: DriftStep; differences: { path: string; approved: HeightRecord; rendered: HeightRecord }[] };

const BOX_PROPERTIES = ["display", "width", "max-width", "aspect-ratio", "height", "line-height", "font-size", "font-family", "padding-block-start", "padding-block-end", "border-block-start-width", "border-block-end-width", "margin-block-start", "margin-block-end", "vertical-align", "box-sizing"];
const MAX_ELEMENTS = 4000;
const MAX_DIFFERENCES = 12;

export function driftSteps(approved: Record<string, string>, rendered: Record<string, string>): DriftStep[] {
  const ids = Object.keys(approved).filter((id) => id in rendered && Number(approved[id]) > 0 && Number(rendered[id]) > 0);
  const steps: DriftStep[] = [];
  let previous: { id: string; delta: number } | null = null;
  for (const id of ids) {
    const delta = Math.round((Number(rendered[id]) - Number(approved[id])) * 100) / 100;
    if (previous && Math.abs(delta - previous.delta) >= 0.5) steps.push({ before: previous.id, after: id, delta: Math.round((delta - previous.delta) * 100) / 100 });
    previous = { id, delta };
  }
  return steps;
}

export async function sectionHeights(page: Page, id: string): Promise<HeightRecord[]> {
  return page.evaluate(
    ({ target, properties, max }) => {
      const element = document.getElementById(target);
      const section = element?.closest(".kv-ch") ?? element?.closest("section") ?? element?.parentElement;
      if (!section) return [];
      return [section, ...section.querySelectorAll("*")].slice(0, max).map((node, index) => {
        const style = getComputedStyle(node);
        const classes = typeof node.className === "string" ? node.className.trim().split(/\s+/).filter(Boolean).slice(0, 3).join(".") : "";
        let depth = 0;
        for (let up: Element | null = node; up && up !== section; up = up.parentElement) depth += 1;
        return {
          path: `${index}:${node.tagName.toLowerCase()}${classes ? `.${classes}` : ""}`,
          depth,
          height: node.getBoundingClientRect().height.toFixed(2),
          width: node.getBoundingClientRect().width.toFixed(2),
          style: properties.map((name) => `${name}=${style.getPropertyValue(name)}`).join(" ")
        };
      });
    },
    { target: id, properties: BOX_PROPERTIES, max: MAX_ELEMENTS }
  );
}

export function heightDifferences(approved: HeightRecord[], rendered: HeightRecord[]): DriftReport["differences"] {
  const byPath = new Map(rendered.map((record) => [record.path, record]));
  const differs = approved.map((record) => {
    const other = byPath.get(record.path);
    return !!other && (Math.abs(Number(record.height) - Number(other.height)) >= 0.5 || Math.abs(Number(record.width) - Number(other.width)) >= 0.5);
  });
  const parents = parentIndexes(approved);
  return approved
    .filter((record, index) => differs[index] && !(parents[index] >= 0 && differs[parents[index]]))
    .slice(0, MAX_DIFFERENCES)
    .map((record) => ({ path: record.path, approved: record, rendered: byPath.get(record.path) as HeightRecord }));
}

function parentIndexes(records: HeightRecord[]): number[] {
  const open: number[] = [];
  return records.map((record, index) => {
    open[record.depth] = index;
    return record.depth > 0 ? (open[record.depth - 1] ?? -1) : -1;
  });
}
