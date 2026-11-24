import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test, type Page } from "@playwright/test";
import { createElement } from "react";

import { BLOCK_RENDERERS } from "@/components/answer/blockRenderers";
import type { CitationLookup } from "@/components/answer/CitationContext";
import { nearBlocksLoaded } from "@/components/answer/nearBlock";
import { KitFigureView } from "@/components/answer/play/KitFigureView";
import { BLOCK_KINDS, BUILT_BLOCK_KINDS, explainerBlockShape } from "@/lib/explainerContract";
import { diagramRefs, kitFigureBlockShape, type KitFigureBlock } from "@/lib/explainerKit";
import { blockSourceIds } from "@/lib/explainerView";
import { FRAME_MOTION_GUARD, frameLookStyle, frameTokenNames, readFrameLook, sandboxDocument } from "@/lib/sandboxFrame";
import { parseShape, ShapeError } from "@/lib/shape";

import { withReading } from "./explainerRender";
import { FRONTEND } from "./moduleGraph";
import { primitivesPage } from "./primitivesPage";

test.beforeAll(() => nearBlocksLoaded());

type KitGolden = { sections: { blocks: Record<string, unknown>[] }[]; sources: { id: string }[] };

const GOLDEN = JSON.parse(readFileSync(join(FRONTEND, "..", "shared", "explainer.kit-figure.golden.json"), "utf8")) as KitGolden;
const KIT_CSS = readFileSync(join(FRONTEND, "components", "artkit", "artkit.css"), "utf8");
const LOOKUP: CitationLookup = { numbers: new Map(GOLDEN.sources.map((source, index) => [source.id, index + 1])), sourcesById: new Map() };
const WIDTHS = [360, 1440] as const;
const SOURCE = GOLDEN.sources[0].id;

function figures(): KitFigureBlock[] {
  return GOLDEN.sections[0].blocks.map((block) => parseShape(kitFigureBlockShape, block));
}

function drawn(block: KitFigureBlock): string {
  return withReading(createElement(KitFigureView, { block }), LOOKUP);
}

function answerPage(body: string, attributes = ""): string {
  return primitivesPage(`<style>${KIT_CSS}</style><main style="padding-inline:16px">${body}</main>`, attributes);
}

async function widthHolds(page: Page): Promise<boolean> {
  return page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
}

test("the composed figures the backend sends parse as the block the web draws, between the timeline map and the component", () => {
  const blocks = figures();
  expect(blocks.map((block) => block.diagram.layout)).toEqual(["before_after", "steps", "section"]);
  for (const block of GOLDEN.sections[0].blocks) expect(parseShape(explainerBlockShape, block).kind).toBe("kit_figure");
  expect(BLOCK_KINDS.slice(-2)).toEqual(["kit_figure", "component"]);
  expect(BUILT_BLOCK_KINDS.slice(-3)).toEqual(["timeline_map", "kit_figure", "component"]);
  expect(BLOCK_RENDERERS.kit_figure).toBe(KitFigureView);
  for (const block of blocks) expect(new Set(blockSourceIds(block))).toEqual(new Set([SOURCE]));
  expect(diagramRefs(blocks[0].diagram)).toEqual(["u0001", "u0002", "u0003", "u0004", "u0005", "u0006", "u0007", "u0008"]);
});

test("a figure whose labels miss a unit it draws, or name one it does not, is refused", () => {
  const [vat] = GOLDEN.sections[0].blocks;
  const labels = vat.labels as Record<string, unknown>[];
  expect(() => parseShape(kitFigureBlockShape, { ...vat, labels: labels.slice(0, -1) })).toThrow(ShapeError);
  expect(() => parseShape(kitFigureBlockShape, { ...vat, labels: [...labels, { ref: "u0099", text: "Nowhere" }] })).toThrow(ShapeError);
  expect(() => parseShape(kitFigureBlockShape, { ...vat, labels: [...labels, labels[0]] })).toThrow(ShapeError);
});

test("the vat figure draws its panels, each part's cited label and one Play, finished at rest", () => {
  const html = drawn(figures()[0]);
  expect(html).toContain('data-testid="kit-figure"');
  expect(html).toContain('data-layout="before_after"');
  expect(html.match(/data-kit-panel="/g)).toHaveLength(2);
  for (const text of ["Green to blue", "Cloth in the vat", "Cloth, blue", "As oxygen meets the dye", "Cloth drawn green in the vat, then blue"]) expect(html).toContain(text);
  expect(html.match(/data-testid="citation-chip"/g)?.length).toBe(4);
  expect(html).toContain('data-kit-swatch="--dye-leuco"');
  expect(html).toContain('data-kit-swatch="--dye-indigo"');
  expect(html.match(/data-kit-move="/g)).toHaveLength(2);
  expect(html.match(/>Play</g)).toHaveLength(1);
  expect(html).not.toContain("data-playing");
  expect(html).not.toContain('aria-current="step"');
});

test("a figure with no moving part offers no Play", () => {
  const html = drawn(figures()[2]);
  expect(html).toContain('data-layout="section"');
  expect(html).not.toContain(">Play<");
  expect(html).toContain('data-kit-swatch="earth"');
});

for (const width of WIDTHS) {
  test(`the answer's kit figures fit ${width}px in light and dark with every label at 12px or more`, async ({ page }) => {
    const body = figures().map(drawn).join("");
    await page.setViewportSize({ width, height: 900 });
    for (const theme of ["light", "dark"]) {
      await page.setContent(answerPage(body, `data-theme="${theme}"`));
      expect(await widthHolds(page), theme).toBe(true);
      const sizes = await page.evaluate(() => [...document.querySelectorAll(".kv-kit-key, .kv-kit-step, .kv-kit-alt, .kv-kit-via")].map((node) => parseFloat(getComputedStyle(node).fontSize)));
      expect(Math.min(...sizes)).toBeGreaterThanOrEqual(12);
      const arts = await page.evaluate(() => [...document.querySelectorAll(".kv-kit-art")].map((node) => node.getBoundingClientRect().width));
      expect(Math.min(...arts)).toBeGreaterThan(100);
    }
  });
}

test("the vat figure's motion plays only when pressed and never under either reduced-motion switch", async ({ page }) => {
  const body = drawn(figures()[0]);
  const names = () => page.evaluate(() => [...document.querySelectorAll("[data-kit-move]")].map((node) => getComputedStyle(node).animationName));
  const play = () => page.evaluate(() => document.querySelectorAll("[data-kit-move]").forEach((node) => node.setAttribute("data-playing", "")));
  await page.setContent(answerPage(body));
  expect(await names()).toEqual(["none", "none"]);
  await play();
  expect(await names()).toEqual(["kv-dip", "kv-dip"]);
  await page.setContent(answerPage(body, 'data-reduced-motion="true"'));
  await play();
  expect(await names()).toEqual(["none", "none"]);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setContent(answerPage(body));
  await play();
  expect(await names()).toEqual(["none", "none"]);
});

test("the frame names the design's tokens a generated explainer uses and the channels they read", () => {
  const html = '<style>.kv{color:var(--ink-1);background:var(--chart-series)}</style>';
  expect(frameTokenNames(html)).toEqual(["--sunk", "--ink-1", "--font-ui", "--chart-series"]);
  const values: Record<string, string> = { "--ink-1": "rgb(var(--c-ink-1))", "--c-ink-1": "28 26 23", "--sunk": "#efe9dd", "--chart-series": "#5E6670", "--font-ui": '"IBM Plex Sans", sans-serif' };
  const look = readFrameLook(frameTokenNames(html), (name) => values[name] ?? "", true);
  expect(look).toEqual({ tokens: values, reducedMotion: true });
  const style = frameLookStyle({ tokens: { ...look.tokens, "--bad": "red}</style><script>", "not-a-token": "red" }, reducedMotion: true });
  expect(style.startsWith(':root{--sunk:#efe9dd;--ink-1:rgb(var(--c-ink-1));--font-ui:"IBM Plex Sans", sans-serif;--chart-series:#5E6670;--c-ink-1:28 26 23}')).toBe(true);
  expect(style).not.toContain("</style>");
  expect(style).not.toContain("not-a-token");
  expect(style.endsWith(FRAME_MOTION_GUARD)).toBe(true);
  const framed = sandboxDocument(html, [], look);
  expect(framed.startsWith('<!doctype html><html lang="en" data-reduced-motion="true"><head>')).toBe(true);
  expect(framed).toContain(`<style>${frameLookStyle(look)}</style></head><body>${html}</body>`);
  expect(sandboxDocument(html, [], { tokens: {}, reducedMotion: false }).startsWith('<!doctype html><html lang="en"><head>')).toBe(true);
});

test("inside the frame the tokens resolve and nothing moves under either switch", async ({ page }) => {
  const html = '<style>.kv{color:var(--ink-1);transition:color 1s ease;animation:spin 2s infinite}@keyframes spin{to{opacity:1}}</style><p class="kv">Still</p>';
  const tokens = { "--ink-1": "rgb(28, 26, 23)", "--sunk": "rgb(239, 233, 221)", "--font-ui": "sans-serif" };
  const read = () => page.evaluate(() => {
    const node = document.querySelector(".kv")!;
    const style = getComputedStyle(node);
    return [style.color, style.animationName, style.transitionDuration, getComputedStyle(document.body).backgroundColor];
  });
  await page.setContent(sandboxDocument(html, [], { tokens, reducedMotion: false }));
  expect(await read()).toEqual(["rgb(28, 26, 23)", "spin", "1s", "rgb(239, 233, 221)"]);
  await page.setContent(sandboxDocument(html, [], { tokens, reducedMotion: true }));
  expect((await read()).slice(1, 3)).toEqual(["none", "0s"]);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setContent(sandboxDocument(html, [], { tokens, reducedMotion: false }));
  expect((await read()).slice(1, 3)).toEqual(["none", "0s"]);
});
