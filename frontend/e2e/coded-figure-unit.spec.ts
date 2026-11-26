import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test, type Page } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { nearBlocksLoaded } from "@/components/answer/nearBlock";
import { SandboxFrame } from "@/components/answer/play/SandboxFrame";
import { COMPONENT_VIEWS } from "@/components/monograph/componentViews";
import { project } from "@/components/map/projection";
import { CODED_WORDS_SUMMARY } from "@/components/monograph/kinds/science/CodedFigure";
import { mapFrame } from "@/components/monograph/kinds/science/codedMapBase";
import { CODED_RUN_HEADING, CODED_STILL_HEADING, CodedFigureReview } from "@/components/review/CodedFigureReview";
import { codedFrameDocument, codedFrameHtml, codedFramePieces, LIBRARY_PATHS, type MapBase } from "@/lib/codedFigureFrame";
import { codedFigureShape, codedValues, codedWords, wordedStill, type CodedFigureSpec } from "@/lib/componentSpecsScienceCoded";
import type { ComponentView } from "@/lib/componentViewContract";
import type { MonographDocument } from "@/lib/monographDocument";
import type { FrameLook } from "@/lib/sandboxFrame";
import { parseShape, ShapeError } from "@/lib/shape";

test.beforeAll(() => nearBlocksLoaded());

const REPO = join(__dirname, "..", "..");
const ORIGIN = "https://kalavigyan.example";
const FIXTURE = JSON.parse(readFileSync(join(REPO, "backend", "app", "data", "kind_fixtures", "coded_figure.json"), "utf8")) as { label: string; spec: Record<string, unknown>; units: Record<string, { text: string }> };
const FIGURE = parseShape(codedFigureShape, FIXTURE.spec);
const said = (ref: string) => FIXTURE.units[ref]?.text ?? "";
const WORDS = codedWords(FIGURE, said);
const STILL = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 200"><rect x="4" y="4" width="40" height="20" fill="#3a5f8f" /><text x="8" y="50" data-unit="patina" /></svg>';
const SERVED: CodedFigureSpec = { ...FIGURE, still: STILL, themes: { light: STILL, dark: STILL, hcLight: STILL, hcDark: STILL } };
const TOKENS = { "--ink-1": "rgb(28, 26, 23)", "--sunk": "rgb(239, 233, 221)", "--font-ui": "sans-serif" };
const STILL_LOOK: FrameLook = { tokens: TOKENS, reducedMotion: true };
const MOVING_LOOK: FrameLook = { tokens: TOKENS, reducedMotion: false };

function drawn(spec: CodedFigureSpec): string {
  const component = { label: FIXTURE.label, chapter: "k1", anchor: "#k", kind: "coded_figure", title: "t", description: "d", field: "CHEMISTRY", fields: [], subjects: [] };
  const view = COMPONENT_VIEWS.coded_figure as ComponentView;
  const props = { component, spec, unitRefs: Object.keys(FIXTURE.units), renderUnit: said, unitText: said, renderComponent: () => null };
  return renderToStaticMarkup(createElement(() => view(props)));
}

async function framed(page: Page, look: FrameLook): Promise<void> {
  await page.setContent(codedFrameDocument({ origin: ORIGIN, figure: FIGURE, words: WORDS, base: null }, look));
}

const statusText = (page: Page) => page.locator(".cf-status").textContent();

test("a coded figure's spec reads its code, values, words, libraries and films, and refuses one the site does not serve", () => {
  expect(FIGURE.values.map((value) => value.key)).toEqual(["ammonium", "nitrate", "water"]);
  expect(Object.keys(WORDS)).toEqual(["alt", "ammonium", "nitrate", "water", "weighed", "dissolved", "patina"]);
  expect(() => parseShape(codedFigureShape, { ...FIXTURE.spec, libraries: ["jquery"] })).toThrow(ShapeError);
  expect(() => parseShape(codedFigureShape, { ...FIXTURE.spec, films: [{ key: "dip", src: "https://cdn.example/dip.mp4" }] })).toThrow(ShapeError);
  expect(parseShape(codedFigureShape, { ...FIXTURE.spec, films: [{ key: "dip", src: "/monographs/kit/films/dip.mp4" }] }).films).toHaveLength(1);
});

test("at first paint the figure is its still in four themes with its words in place, and no frame is loaded", () => {
  const html = drawn(SERVED);
  expect(html).toContain('data-coded-frame="still"');
  expect(html.match(/data-theme-variant=/g)).toHaveLength(4);
  expect(html).not.toContain("<iframe");
  expect(html).toContain(said("u0002"));
  expect(html).toContain(CODED_WORDS_SUMMARY);
  expect(html).toContain(said("u0009"));
  expect(drawn(FIGURE)).toContain('data-coded-still="none"');
  const worded = wordedStill(STILL, { patina: "The patina forms <at once>" });
  expect(worded).toContain('data-unit="patina">The patina forms &lt;at once&gt;</text>');
});

test("the frame runs sandboxed with scripts only, its data and words passed in, and loads only the pinned libraries", () => {
  const block = { title: "t", html: codedFrameHtml(FIGURE), values: codedValues(FIGURE) };
  const plain = renderToStaticMarkup(createElement(SandboxFrame, { block, pieces: codedFramePieces({ origin: ORIGIN, figure: FIGURE, words: WORDS, base: null }) }));
  expect(plain).toContain('sandbox="allow-scripts"');
  expect(plain).toContain("media-src &#x27;none&#x27;");
  expect(plain).toContain("script-src &#x27;unsafe-inline&#x27;;");
  const document = codedFrameDocument({ origin: ORIGIN, figure: { ...FIGURE, libraries: ["d3"] }, words: WORDS, base: null }, null);
  expect(document.startsWith('<!doctype html><html lang="en" data-reduced-motion="true"><head>')).toBe(true);
  expect(document).toContain(`script-src 'unsafe-inline' ${ORIGIN}${LIBRARY_PATHS.d3};`);
  expect(document).toContain(`<script src="${ORIGIN}${LIBRARY_PATHS.d3}"></script>`);
  expect(document).not.toContain(LIBRARY_PATHS.three);
  expect(document).toContain('"ammonium":20');
  for (const path of Object.values(LIBRARY_PATHS)) expect(readFileSync(join(REPO, "frontend", "public", path)).length).toBeGreaterThan(100_000);
});

test("in the frame the words come from the page's units, and nothing reaches the network", async ({ page }) => {
  await framed(page, STILL_LOOK);
  expect(await statusText(page)).toBe(said("u0009"));
  expect(await page.locator('[data-unit="ammonium"]').textContent()).toBe(said("u0004"));
  expect(await page.locator("svg").getAttribute("aria-label")).toBe(said("u0003"));
  expect(await page.locator(".heap-ammonium").getAttribute("height")).toBe("40");
  const reached = await page.evaluate(() => fetch("https://example.com/").then(() => "reached", () => "refused"));
  expect(reached).toBe("refused");
});

test("under reduced motion the figure rests finished and Play steps it at once, with nothing running", async ({ page }) => {
  await framed(page, STILL_LOOK);
  await page.locator(".cf-play").click();
  expect(await statusText(page)).toBe(said("u0007"));
  await page.waitForTimeout(1300);
  expect(await statusText(page)).toBe(said("u0007"));
  expect(await page.evaluate(() => document.getAnimations().filter((animation) => animation.playState === "running").length)).toBe(0);
});

test("with motion allowed Play runs the steps, pauses on a second press and rests on the last state", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await framed(page, MOVING_LOOK);
  await page.locator(".cf-play").click();
  expect(await page.locator(".cf-play").getAttribute("aria-pressed")).toBe("true");
  expect(await statusText(page)).toBe(said("u0007"));
  await page.waitForTimeout(1300);
  expect(await statusText(page)).toBe(said("u0008"));
  await page.locator(".cf-play").click();
  expect(await page.locator(".cf-play").getAttribute("aria-pressed")).toBe("false");
  expect(await statusText(page)).toBe(said("u0009"));
});

test("a map figure is drawn on the site's base, whose Survey of India outline the code cannot take away", async ({ page }) => {
  const base: MapBase = { ...mapFrame(), outline: "M10 10L90 10L90 90Z", rann: "M20 20L30 20L30 30Z", relief: [{ step: 2, d: "M40 40L50 40L50 50Z" }], rivers: ["M10 50L90 50"], states: "M50 10L50 90", districts: null, homes: [] };
  const figure: CodedFigureSpec = { ...FIGURE, map: { layers: ["states", "rivers", "relief"], districts: [] }, code: '<svg viewBox="0 0 1000 1000" data-map=""><circle cx="500" cy="500" r="6"></circle></svg>' };
  await page.setContent(codedFrameDocument({ origin: ORIGIN, figure, words: WORDS, base }, STILL_LOOK));
  const outline = page.locator("svg > g.kv-map-base > path.kv-map-outline");
  expect(await outline.getAttribute("d")).toBe(base.outline);
  expect(await page.locator("svg > g.kv-map-base > path.kv-map-relief-2").count()).toBe(1);
  await page.evaluate(() => document.querySelector(".kv-map-base")?.remove());
  await expect(outline).toHaveCount(1);
  const corner = await page.evaluate(([west, north]) => (window as unknown as { kvMap: { project: (x: number, y: number) => { x: number; y: number } } }).kvMap.project(west, north), [base.bounds.west, base.bounds.north]);
  const expected = project(base.bounds.west, base.bounds.north);
  expect(corner.x).toBeCloseTo(expected.x, 6);
  expect(corner.y).toBeCloseTo(expected.y, 6);
  const east = project(base.bounds.east, base.bounds.south);
  const far = await page.evaluate(([longitude, latitude]) => (window as unknown as { kvMap: { project: (x: number, y: number) => { x: number; y: number } } }).kvMap.project(longitude, latitude), [base.bounds.east, base.bounds.south]);
  expect(far.x).toBeCloseTo(east.x, 6);
  expect(far.y).toBeCloseTo(east.y, 6);
});

test("the Review page shows the coded figure's still beside its live run", () => {
  const units = Object.fromEntries(Object.entries(FIXTURE.units).map(([ref, unit]) => [ref, { chapter: "k1", tag: "p", field: "CHEMISTRY", nodes: [unit.text], claimIds: [] }]));
  const document = {
    content: { components: [{ label: FIXTURE.label, chapter: "k1", anchor: "#k", kind: "coded_figure", title: "t", description: "d", field: "CHEMISTRY", fields: [], subjects: [] }], units },
    specs: { [FIXTURE.label]: SERVED }
  } as unknown as MonographDocument;
  const html = renderToStaticMarkup(createElement(CodedFigureReview, { document, label: FIXTURE.label }));
  expect(html).toContain(CODED_STILL_HEADING);
  expect(html).toContain(CODED_RUN_HEADING);
  expect(html.match(/data-coded-still=""/g)).toHaveLength(2);
  expect(html).toContain('data-coded-frame="still"');
  const other = { ...document, content: { ...document.content, components: [{ ...document.content.components[0], kind: "drawing" }] } } as MonographDocument;
  expect(renderToStaticMarkup(createElement(CodedFigureReview, { document: other, label: FIXTURE.label }))).toBe("");
});
