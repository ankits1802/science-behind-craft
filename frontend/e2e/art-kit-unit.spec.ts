import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test, type Page } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { KitSheet } from "../app/design/kit/KitSheet";
import { nearBlocksLoaded } from "../components/answer/nearBlock";
import { KitFigure } from "../components/artkit/KitFigure";
import { kitIds, partIds } from "../components/artkit/kitIds";
import { KitPartArt } from "../components/artkit/KitPartArt";
import { COMPONENT_VIEWS } from "../components/monograph/componentViews";
import { ART_KIT, depictedToken, KIT_MATERIALS, KIT_PART_NAMES } from "../lib/artKit";
import { kitMotionClass, kitSchedule, kitStatus, kitStillStep, kitTimings } from "../lib/artKitMotion";
import { kitSheet, kitSheetLayouts } from "../lib/artKitSheet";
import { declaredForm } from "../lib/componentSpecsTimelineMap";
import { kitDiagramShape, movingPart, type KitDiagramSpec, type KitPart } from "../lib/componentSpecsKit";
import type { ComponentView } from "../lib/componentViewContract";
import { parseKindFixtures } from "../lib/kindFixtures";
import { appDrawn } from "../lib/monographScopes";
import { parseShape, ShapeError } from "../lib/shape";

import { FRONTEND } from "./moduleGraph";

test.beforeAll(() => nearBlocksLoaded());
import { primitivesPage } from "./primitivesPage";

const SHARED = join(FRONTEND, "..", "shared");
const BACKEND_DATA = join(FRONTEND, "..", "backend", "app", "data");
const GOLDEN = JSON.parse(readFileSync(join(SHARED, "art-kit.golden.json"), "utf8")) as unknown;
const KIT_CSS = readFileSync(join(FRONTEND, "components", "artkit", "artkit.css"), "utf8");
const TOKENS = readFileSync(join(FRONTEND, "app", "tokens.css"), "utf8");
const ROOT = TOKENS.slice(TOKENS.indexOf(":root {"), TOKENS.indexOf("}", TOKENS.indexOf(":root {")));
const token = (name: string) => new RegExp(`${name}:\\s*([^;]+);`).exec(ROOT)?.[1] ?? "";
const [BIDRIWARE] = parseKindFixtures({ fixtures: [JSON.parse(readFileSync(join(BACKEND_DATA, "kind_fixtures", "diagram_kit.json"), "utf8"))] });
const BOREWELL = JSON.parse(readFileSync(join(BACKEND_DATA, "monographs", "Kutch-Ajrakh", "specs", "kutch-ajrakh__geology__ajrakhpur-borewell-depth.json"), "utf8")) as Record<string, unknown>;
const WIDTHS = [360, 1440] as const;
const LAYOUTS = kitSheetLayouts();
const MATERIAL_PARTS = kitSheet().filter((part) => part.materials.length);

function viewed(spec: Record<string, unknown>, label = BIDRIWARE.label): string {
  const view = COMPONENT_VIEWS.diagram as ComponentView;
  const component = { label, chapter: "k1", anchor: "#k", kind: "diagram", title: BIDRIWARE.title, description: BIDRIWARE.description, field: BIDRIWARE.field, fields: [], subjects: [] };
  const text = (ref: string) => BIDRIWARE.units[ref]?.text ?? "";
  return renderToStaticMarkup(createElement(() => view({ component, spec, unitRefs: Object.keys(BIDRIWARE.units), renderUnit: text, unitText: text, renderComponent: () => null })));
}

function figure(spec: KitDiagramSpec, texts: Readonly<Record<string, string>>, label: string): string {
  return renderToStaticMarkup(createElement(KitFigure, { spec, label, renderUnit: (ref: string) => texts[ref] ?? "", unitText: (ref: string) => texts[ref] ?? "" }));
}

function partArt(part: KitPart, key: string): string {
  const ids = kitIds(`unit/${key}`);
  return renderToStaticMarkup(createElement("svg", { viewBox: "0 0 120 120" }, createElement(KitPartArt, { part, ids: partIds(ids, key) })));
}

async function widthHolds(page: Page): Promise<boolean> {
  return page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
}

function kitPage(body: string, attributes = ""): string {
  return primitivesPage(`<style>${KIT_CSS}</style><main style="padding-inline:16px">${body}</main>`, attributes);
}

test("the web's kit is the shared golden the backend reads", () => {
  expect(JSON.parse(JSON.stringify(ART_KIT))).toEqual(GOLDEN);
  expect(KIT_PART_NAMES).toEqual(["cloth", "block", "bath", "paste", "heat", "water", "tool", "section", "piece"]);
  expect(KIT_MATERIALS).toHaveLength(38);
  expect(depictedToken("--dye-bidri-white")).toBe(true);
  expect(depictedToken("--dip-4")).toBe(true);
  expect(depictedToken("--dye-ultramarine")).toBe(false);
  expect(depictedToken("--ink-1")).toBe(false);
});

test("a composed diagram is the site's own drawing and Kutch Ajrakh's authored diagram keeps its view", () => {
  expect(declaredForm("diagram", BIDRIWARE.spec)).toBe(true);
  expect(appDrawn("diagram", BIDRIWARE.spec)).toBe(true);
  expect(declaredForm("diagram", BOREWELL)).toBe(false);
  expect(appDrawn("diagram", BOREWELL)).toBe(false);
  const authored = viewed(BOREWELL, "kutch-ajrakh/geology/ajrakhpur-borewell-depth");
  expect(authored).toContain('class="well-svg kv-well"');
  expect(authored).not.toContain('data-testid="kit-diagram"');
});

test("the Bidriware fixture draws its three panels, every part's cited label and one Play", () => {
  const spec = parseShape(kitDiagramShape, BIDRIWARE.spec);
  expect(spec.panels.map((panel) => movingPart(panel))).toEqual([null, 0, null]);
  const html = viewed(BIDRIWARE.spec);
  expect(html).toContain('data-testid="kit-diagram"');
  expect(html.match(/data-kit-panel="/g)).toHaveLength(3);
  expect(html.match(/data-kit-move="1"/g)).toHaveLength(1);
  for (const ref of ["u0002", "u0006", "u0010", "u0014"]) expect(html).toContain(BIDRIWARE.units[ref].text);
  expect(html.match(/>Play</g)).toHaveLength(1);
  expect(html).toContain('role="status" aria-live="polite"></p>');
  expect(html).not.toContain("data-playing");
  expect(html).not.toContain('aria-current="step"');
  expect(html).toContain('data-kit-swatch="--dye-bidri-silver"');
});

test("the shape refuses a spec off the kit, and takes earth only as a layer", () => {
  const panel = (part: Record<string, unknown>) => ({ head: { title: "u0001" }, layout: "steps", alt: "u0002", panels: [{ label: "u0003", parts: [part] }, { label: "u0004", parts: [part] }] });
  expect(() => parseShape(kitDiagramShape, panel({ part: "cloth", form: "swatch", material: "--ink-1", label: "u0005" }))).toThrow(ShapeError);
  expect(() => parseShape(kitDiagramShape, panel({ part: "loom", label: "u0005" }))).toThrow(ShapeError);
  expect(() => parseShape(kitDiagramShape, panel({ part: "cloth", form: "swatch", material: "earth", label: "u0005" }))).toThrow(ShapeError);
  const layers = [{ material: "earth", label: "u0006" }, { material: "--dye-mud", label: "u0007" }];
  expect(parseShape(kitDiagramShape, panel({ part: "section", layers, label: "u0005" })).panels).toHaveLength(2);
});

for (const part of MATERIAL_PARTS) {
  test(`the ${part.name} part draws every depicted material textured and edged in ink`, () => {
    for (const tile of part.materials) {
      const svg = partArt(tile.part, `${part.name}-${tile.key.replace(/[^a-z0-9]+/g, "-")}`);
      expect(svg, tile.key).toContain(`var(${tile.key})`);
      expect(svg, tile.key).toMatch(/url\(#kit-unit-[\w-]+-(weave|ripple|strata|grain|speckle)\)/);
      expect(svg, tile.key).toContain('stroke="var(--ink-1)"');
    }
  });
}

test("every part's every form is drawn and named on the kit sheet", () => {
  const sheet = kitSheet();
  expect(sheet.map((part) => part.name)).toEqual([...KIT_PART_NAMES]);
  expect(sheet.map((part) => part.variants.length)).toEqual([7, 5, 5, 4, 4, 3, 7, 5, 8]);
  expect(MATERIAL_PARTS.map((part) => part.name)).toEqual(["cloth", "block", "bath", "paste", "tool", "section", "piece"]);
  expect(sheet[0].families).toBe("Serves Textiles and More crafts");
  const html = renderToStaticMarkup(createElement(KitSheet));
  expect(html.match(/data-kit-tile="/g)).toHaveLength(48 + 7 * 38);
  for (const material of KIT_MATERIALS) expect(html.match(new RegExp(`data-kit-specimen="${material}"`, "g")), material).toHaveLength(7);
  expect(html.match(/data-kit-sheet-layout="/g)).toHaveLength(4);
});

for (const width of WIDTHS) {
  test(`the kit sheet and the four layouts fit ${width}px in light and dark, every label at 12px or more`, async ({ page }) => {
    const body = renderToStaticMarkup(createElement(KitSheet));
    await page.setViewportSize({ width, height: 900 });
    for (const theme of ["light", "dark"]) {
      await page.setContent(kitPage(body, `data-theme="${theme}"`));
      expect(await widthHolds(page), theme).toBe(true);
      const sizes = await page.evaluate(() => [...document.querySelectorAll(".kv-kit-tile-caption, .kv-kit-key, .kv-kit-step, .kv-kit-via")].map((node) => parseFloat(getComputedStyle(node).fontSize)));
      expect(Math.min(...sizes)).toBeGreaterThanOrEqual(12);
      const arts = await page.evaluate(() => [...document.querySelectorAll(".kv-kit-art")].map((node) => node.getBoundingClientRect().width));
      expect(Math.min(...arts)).toBeGreaterThan(100);
    }
    const grounds: string[] = [];
    for (const theme of ["light", "dark"]) {
      await page.setContent(kitPage(body, `data-theme="${theme}"`));
      grounds.push(await page.evaluate(() => getComputedStyle(document.querySelector(".kv-kit-art")!).backgroundColor));
    }
    expect(grounds[0]).not.toBe(grounds[1]);
  });
}

test("each layout lays its panels out phone first and joins a sequence with arrows", async ({ page }) => {
  const body = LAYOUTS.map((layout) => figure(layout.spec, layout.texts, `unit/${layout.key}`)).join("");
  const tracks = () => page.evaluate(() => Object.fromEntries([...document.querySelectorAll(".kv-kit")].map((node) => [node.getAttribute("data-layout"), getComputedStyle(node.querySelector(".kv-kit-panels")!).gridTemplateColumns.split(" ").length])));
  const arrow = () => page.evaluate(() => getComputedStyle(document.querySelector(".kv-kit-arrow")!).transform);
  await page.setViewportSize({ width: 360, height: 900 });
  await page.setContent(kitPage(body));
  expect(await tracks()).toEqual({ steps: 2, before_after: 1, section: 1, sequence: 1 });
  expect(await arrow()).not.toBe("none");
  expect(await widthHolds(page)).toBe(true);
  await page.setViewportSize({ width: 1440, height: 900 });
  expect(await tracks()).toEqual({ steps: 3, before_after: 2, section: 1, sequence: 3 });
  expect(await arrow()).toBe("none");
  const section = await page.evaluate(() => getComputedStyle(document.querySelector('[data-layout="section"] .kv-kit-panel')!).gridTemplateColumns.split(" ").length);
  expect(section).toBe(2);
});

test("motion rests on the finished state, plays on the moving part only, and never under either switch", async ({ page }) => {
  const sequence = LAYOUTS.find((layout) => layout.key === "sequence")!;
  const dried: KitDiagramSpec = { head: { title: "u0001" }, layout: "before_after", alt: "u0007", panels: [{ label: "u0002", parts: [{ part: "cloth", form: "swatch", material: "--dye-cloth", label: "u0005" }] }, { label: "u0003", via: "u0006", motion: "dry", parts: [{ part: "paste", form: "spread", material: "--dye-mud-wet", dried: "--dye-mud", label: "u0005" }] }] };
  const body = figure(sequence.spec, sequence.texts, "unit/motion") + figure(dried, sequence.texts, "unit/dried");
  const state = () =>
    page.evaluate(() => {
      const [dip, dry] = [...document.querySelectorAll("[data-kit-move]")];
      return { dip: [getComputedStyle(dip).clipPath, getComputedStyle(dip).animationName], dry: [getComputedStyle(dry).clipPath, getComputedStyle(dry).animationName] };
    });
  const play = () => page.evaluate(() => document.querySelectorAll("[data-kit-move]").forEach((node) => node.setAttribute("data-playing", "")));
  await page.setContent(kitPage(body));
  expect(await state()).toEqual({ dip: ["inset(0px)", "none"], dry: ["inset(100% 0px 0px)", "none"] });
  await play();
  const playing = await state();
  expect([playing.dip[1], playing.dry[1]]).toEqual(["kv-dip", "kv-oxidise"]);
  await page.setContent(kitPage(body, 'data-reduced-motion="true"'));
  await play();
  expect((await state()).dip[1]).toBe("none");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setContent(kitPage(body));
  await play();
  expect((await state()).dry[1]).toBe("none");
});

test("Play runs each panel in turn on the motion tokens, and steps one still panel a press when motion is off", () => {
  const timings = kitTimings(token);
  expect(timings).toEqual({ dip: 600, hold: 500, oxidise: 1500 });
  expect(kitSchedule([null, "dip", null], timings)).toEqual([
    { panel: 0, moves: false, at: 0 },
    { panel: 1, moves: true, at: 1000 },
    { panel: 2, moves: false, at: 2100 },
    { panel: null, moves: false, at: 3100 }
  ]);
  expect(kitSchedule(["dry"], timings).at(-1)?.at).toBe(2000);
  expect([kitStillStep(null, 3), kitStillStep(0, 3), kitStillStep(2, 3)]).toEqual([0, 1, null]);
  expect(kitStatus(1, ["Sanded level", "In the bath", "Lifted out"])).toBe("Step 2 of 3: In the bath");
  expect(kitStatus(null, ["Sanded level"])).toBe("At rest");
  expect([kitMotionClass("dip"), kitMotionClass("take"), kitMotionClass("dry")]).toEqual(["motion-dip", "motion-dip", "motion-oxidise"]);
});
