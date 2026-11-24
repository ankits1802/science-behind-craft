import type { ElementHandle, Page } from "@playwright/test";

import { drawingProblems } from "./drawingChecks";
import { sameText } from "./parityBorrowed";
import { styleDifferences, type StyleDifference, type StyleRecord } from "./parityStyles";

export type ComponentDrawing = { styles: StyleRecord; width: number; text: string };
export type SanityProblem = { label: string; problem: string };

const PROPERTIES = [
  "display",
  "visibility",
  "position",
  "font-family",
  "font-size",
  "font-weight",
  "font-style",
  "line-height",
  "letter-spacing",
  "text-transform",
  "white-space",
  "vertical-align",
  "color",
  "background-color",
  "margin-block-start",
  "margin-block-end",
  "margin-inline-start",
  "padding-block-start",
  "padding-block-end",
  "padding-inline-start",
  "border-block-start-width",
  "border-inline-start-width",
  "column-gap",
  "row-gap",
  "grid-template-columns",
  "flex-direction"
];
export const GRAPHIC_TAGS = ["svg", "img", "canvas", "video", "picture"];
const NODE_CAP = 500;
const BOX_TOLERANCE_PX = 2;

export async function generatedRoot(page: Page, label: string, depth: number): Promise<ElementHandle<Element> | null> {
  const handle = await page.evaluateHandle(
    ({ wanted, steps }) => {
      let node: Element | null = [...document.querySelectorAll("[data-component]")].find((found) => found.getAttribute("data-component") === wanted) ?? null;
      for (let at = 0; node && at <= steps; at += 1) node = node.firstElementChild;
      return node;
    },
    { wanted: label, steps: depth }
  );
  return handle.asElement();
}

export async function authoredRoot(page: Page, selector: string, text: string): Promise<ElementHandle<Element> | null> {
  const candidates = await page.$$(`#kv-main ${selector}`);
  let best: { handle: ElementHandle<Element>; score: number } | null = null;
  for (const handle of candidates) {
    const score = sameText(await handle.evaluate((element) => (element as HTMLElement).innerText ?? element.textContent ?? ""), text);
    if (!best || score > best.score) best = { handle, score };
  }
  return best?.handle ?? null;
}

export async function drawing(root: ElementHandle<Element>): Promise<ComponentDrawing> {
  return root.evaluate(
    (element, { properties, cap }) => {
      const origin = element.getBoundingClientRect();
      const nodes = [element, ...element.querySelectorAll("*")].slice(0, cap);
      const styles = Object.fromEntries(
        nodes.map((node, index) => {
          const style = getComputedStyle(node);
          const box = node.getBoundingClientRect();
          const name = node.getAttribute("class")?.trim().split(/\s+/).filter(Boolean).join(".") ?? "";
          const record: Record<string, string> = Object.fromEntries(properties.map((property) => [property, style.getPropertyValue(property)]));
          record["box-x"] = String(Math.round(box.left - origin.left));
          record["box-width"] = String(Math.round(box.width));
          record["box-height"] = String(Math.round(box.height));
          return [`${index}:${node.tagName.toLowerCase()}${name ? `.${name}` : ""}`, record];
        })
      );
      return { styles, width: origin.width, text: (element as HTMLElement).innerText ?? element.textContent ?? "" };
    },
    { properties: PROPERTIES, cap: NODE_CAP }
  );
}

export async function widthAs(root: ElementHandle<Element>, width: number): Promise<void> {
  await root.evaluate((element, wanted) => {
    const target = element as HTMLElement;
    target.style.setProperty("width", `${wanted}px`);
    target.style.setProperty("max-width", "none");
  }, width);
}

function tag(node: string): string {
  return node.split(":")[1]?.split(".")[0] ?? "";
}

const ROOT = "0:";
const ROOT_PLACEMENT = new Set(["margin-block-start", "margin-block-end", "margin-inline-start", "box-height"]);

function gatedBox(difference: StyleDifference, approved: StyleRecord): boolean {
  const delta = Math.abs(Number(difference.approved) - Number(difference.rendered));
  if (!(delta > BOX_TOLERANCE_PX)) return false;
  if (GRAPHIC_TAGS.includes(tag(difference.node)) || difference.node.startsWith(ROOT)) return true;
  return difference.property === "box-x" && !(approved[difference.node]?.display ?? "").startsWith("inline");
}

export function gatedDifferences(approved: StyleRecord, rendered: StyleRecord): StyleDifference[] {
  return styleDifferences(approved, rendered).filter((difference) => {
    if (difference.node.startsWith(ROOT) && ROOT_PLACEMENT.has(difference.property)) return false;
    return difference.property.startsWith("box-") ? gatedBox(difference, approved) : true;
  });
}

export async function sanityProblems(page: Page, label: string, root: ElementHandle<Element>): Promise<SanityProblem[]> {
  const found = await drawingProblems(page, root);
  return found.map((problem) => ({ label: `${page.url()} ${label}`, problem }));
}
