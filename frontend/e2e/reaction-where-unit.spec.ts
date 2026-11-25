import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test, type Page } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { COMPONENT_VIEWS } from "../components/monograph/componentViews";
import { Drawing } from "../components/monograph/kinds/science/parts/Drawing";
import type { SvgNode } from "../lib/componentSpecsScienceParts";
import type { ComponentView } from "../lib/componentViewContract";
import { parseKindFixtures, type KindFixture } from "../lib/kindFixtures";
import type { MonographComponent } from "../lib/monographDocument";
import { WHERE_ICON_UNITS_MOST, whereDrawing } from "../lib/reactionWhere";

import { FRONTEND } from "./moduleGraph";
import { AJRAKH_DIR } from "./monographMarkup";
import { drawingLimits, drawingProblems } from "./parity/drawingChecks";
import { primitivesPage } from "./primitivesPage";

type Spec = { steps: { scene: unknown }[] } & Record<string, unknown>;

const KIT_CSS = readFileSync(join(FRONTEND, "public", "monographs", "kit", "monograph.css"), "utf8");
const FIXTURE = join(FRONTEND, "..", "backend", "app", "data", "kind_fixtures", "reaction_player.json");
const AJRAKH_PLAYER = join(AJRAKH_DIR, "specs", "shared__chemistry__indigo-reduction-player.json");
const WIDTHS = [360, 1440] as const;
const ICON: SvgNode = { tag: "svg", attrs: { viewBox: "0 0 24 24" }, children: [{ tag: "rect", attrs: { x: "3", y: "7", width: "18", height: "11", fill: "none", stroke: "var(--ink-2)", "stroke-width": "1.5" } }] };
const ART: SvgNode = { tag: "svg", attrs: { viewBox: "0 0 320 200" }, children: [{ tag: "rect", attrs: { x: "30", y: "30", width: "260", height: "140", fill: "var(--ground)", stroke: "var(--rule-strong)", "stroke-width": "2" } }] };
const ICON_PROBLEM = /^an icon of 24 units draws \d+px wide$/;

function whereIcons(value: unknown): SvgNode[] {
  if (Array.isArray(value)) return value.flatMap(whereIcons);
  if (typeof value !== "object" || value === null) return [];
  const record = value as Record<string, unknown>;
  const own = record.whereIcon && typeof record.whereIcon === "object" ? [record.whereIcon as SvgNode] : [];
  return [...own, ...Object.values(record).flatMap(whereIcons)];
}

function handDrawnPlayer(): { found: KindFixture; spec: Spec } {
  const found = parseKindFixtures({ fixtures: [JSON.parse(readFileSync(FIXTURE, "utf8"))] })[0];
  const spec = structuredClone(found.spec) as Spec;
  for (const step of spec.steps) step.scene = { whereIcon: ICON, where: (step.scene as { where: string }).where, art: [ART] };
  return { found, spec };
}

function drawnPlayer(): string {
  const { found, spec } = handDrawnPlayer();
  const text = (ref: string) => found.units[ref]?.text ?? "";
  const component: MonographComponent = { label: found.label, chapter: "chem", anchor: "#chem", kind: found.kind, title: found.label, description: "", field: "CHEMISTRY", fields: [], subjects: [] };
  const view = COMPONENT_VIEWS[found.kind] as ComponentView;
  return renderToStaticMarkup(createElement(() => view({ component, spec, unitRefs: [], renderUnit: text, unitText: text, renderComponent: () => null })));
}

function rawWhere(): string {
  return `<figure class="rp rx-player"><div class="rx" data-i="1"><div class="rx-where">${renderToStaticMarkup(createElement(Drawing, { node: ICON }))}<p>Where the cloth is soaked</p></div></div></figure>`;
}

async function opened(page: Page, width: number, figure: string): Promise<string[]> {
  await page.setViewportSize({ width, height: 900 });
  await page.setContent(primitivesPage(`<style>${KIT_CSS}</style><main style="padding-inline:16px"><section class="bx bx-chem">${figure}</section></main>`));
  const root = await page.$("figure.rp");
  if (!root) throw new Error("the player is not on the fixture page");
  return drawingProblems(page, root);
}

test("a where drawing of an icon's units draws at its own size, one unit a pixel, and never as the vignette", () => {
  expect(whereDrawing(ICON)).toEqual({ ...ICON, attrs: { viewBox: "0 0 24 24", "aria-hidden": "true", width: "24", height: "24" } });
  expect(whereDrawing({ ...ICON, attrs: { viewBox: "0 0 24 24", class: "vg mark" } }).attrs).toEqual({ viewBox: "0 0 24 24", class: "mark", "aria-hidden": "true", width: "24", height: "24" });
  expect(whereDrawing({ ...ICON, attrs: { viewBox: "0 0 32 20", class: "vg", width: "100%" } }).attrs).toEqual({ viewBox: "0 0 32 20", width: "32", height: "20", "aria-hidden": "true" });
});

test("any other where drawing is the vignette the kit sizes, and Kutch Ajrakh's are drawn as their spec gives them", () => {
  const ajrakh = whereIcons(JSON.parse(readFileSync(AJRAKH_PLAYER, "utf8")));
  expect(ajrakh.length).toBeGreaterThan(0);
  for (const node of ajrakh) expect(whereDrawing(node)).toBe(node);
  expect(whereDrawing({ tag: "svg", attrs: { viewBox: "0 0 33 33" } }).attrs).toEqual({ viewBox: "0 0 33 33", class: "vg", "aria-hidden": "true" });
  expect(whereDrawing({ tag: "svg", attrs: { viewBox: "0 0 132 92", class: "scene" } }).attrs).toEqual({ viewBox: "0 0 132 92", class: "scene vg", "aria-hidden": "true" });
  expect(whereDrawing({ tag: "svg" }).attrs).toEqual({ class: "vg", "aria-hidden": "true" });
  const group: SvgNode = { tag: "g", attrs: { class: "x" } };
  expect(whereDrawing(group)).toBe(group);
});

test("an icon is what the release's drawing checks call an icon", async ({ page }) => {
  await page.setContent("<p>limits</p>");
  expect(WHERE_ICON_UNITS_MOST).toBe((await drawingLimits(page)).iconView);
});

for (const width of WIDTHS) {
  test(`at ${width} px a reaction player draws a step's 24-unit where icon 24 px wide, which drawn as given fails the drawing checks`, async ({ page }) => {
    expect(await opened(page, width, drawnPlayer())).toEqual([]);
    const shown = page.locator(".rx:not([hidden]) .rx-where svg").first();
    expect(await shown.evaluate((node) => Math.round(node.getBoundingClientRect().width))).toBe(24);
    const raw = await opened(page, width, rawWhere());
    expect(raw.some((problem) => ICON_PROBLEM.test(problem)), raw.join("; ")).toBe(true);
  });
}
