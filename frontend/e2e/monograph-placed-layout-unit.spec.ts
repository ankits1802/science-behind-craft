import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test, type Page } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { AuthProvider } from "../components/AuthProvider";
import { documentScopes } from "../components/monograph/kitFirstScopes";
import { MonographPage } from "../components/monograph/MonographPage";
import { ThemeProvider } from "../components/ThemeProvider";
import type { MonographDocument } from "../lib/monographDocument";
import type { ChapterBlock, ChapterPlan } from "../lib/monographRenderLayout";
import { shownPage } from "../lib/monographShownPage";

import { FRONTEND } from "./moduleGraph";
import { BLEED, COLUMN, IRON, KILN, layoutEntries, MARGIN, proseDocument, PULL, SIDE, sizedDocument, VAT, WIDE, withLayout } from "./placedLayoutFixture";
import { PRIMITIVE_CSS } from "./primitivesPage";
import { KIN, templateDocument } from "./templateMonographFixture";

const KIT_CSS = readFileSync(join(FRONTEND, "public", "monographs", "kit", "monograph.css"), "utf8");
const PAGE_CSS = readFileSync(join(FRONTEND, "components", "monograph", "documentPage.css"), "utf8");
const SPREAD_FROM = 1200;
const READING_COLUMN = 680;

const pageHtml = (document: MonographDocument) => renderToStaticMarkup(createElement(AuthProvider, null, createElement(ThemeProvider, null, createElement(MonographPage, { document }))));
const chapterOf = (document: MonographDocument, key: string): ChapterPlan => shownPage(document).plan.chapters.find((chapter) => chapter.key === key)!;
const shape = (blocks: readonly ChapterBlock[]) => blocks.map((block) => (block.kind === "component" ? block.label : block.kind));

function home(html: string, label: string): string {
  const from = html.indexOf(`data-component="${label}"`);
  expect(from, label).toBeGreaterThan(0);
  return html.slice(html.lastIndexOf("<div", from), html.indexOf("<figure", from));
}

async function drawn(page: Page, width: number, html: string): Promise<void> {
  await page.setViewportSize({ width, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setContent(`<!doctype html><html lang="en" data-theme="light"><head><meta charset="utf-8"><style>${PRIMITIVE_CSS}</style><style>${KIT_CSS}</style><style>${PAGE_CSS}</style></head><body>${html}</body></html>`, { waitUntil: "domcontentloaded" });
}

test("a WIDE, BLEED and COLUMN entry each take their frame, and a SIDEBAR one stands in its paragraph's margin", () => {
  const html = pageHtml(sizedDocument());
  const frame = (label: string, size: string) => `<div class="bx bx-pt my-12" data-component="${label}" data-component-kind="picture_plate" data-home="kind" data-size="${size}">`;
  expect(home(html, WIDE)).toBe(`${frame(WIDE, "wide")}<div class="screen"><div class="wrap kv-passage">`);
  expect(home(html, BLEED)).toBe(`${frame(BLEED, "bleed")}<div class="screen"><div class="wrap kv-passage kv-bleed">`);
  expect(home(html, COLUMN)).toBe(`${frame(COLUMN, "column")}<div class="screen"><div class="wrap kv-passage"><div class="spread"><div class="main">`);
  expect(home(html, MARGIN)).toBe(`<div class="bx bx-pt" data-component="${MARGIN}" data-component-kind="picture_plate" data-home="kind" data-size="margin">`);
  expect(html).toMatch(new RegExp(`<aside class="margin note keep" aria-label="Sources in this passage"><ul>.*?</ul><div class="margin-plate" data-beside="component"><div class="bx bx-pt" data-component="${MARGIN}"`));
  const made = chapterOf(sizedDocument(), "made");
  expect(shape(made.blocks)).toEqual(["passage", WIDE, BLEED, COLUMN, "passage"]);
  expect(made.blocks[4]).toMatchObject({ kind: "passage", asides: [{ after: "made-3", ref: MARGIN, kind: "component" }] });
});

test("a component in a margin names its kit scope to the page's first sheet", () => {
  const document = sizedDocument();
  const kin = new Set([KIN, "kin-1", "kin-2"]);
  const moved = document.content.layout.filter((entry) => kin.has(entry.ref)).map((entry) => ({ ...entry, chapter: "made" }));
  document.content.layout = [...document.content.layout.filter((entry) => !kin.has(entry.ref)), ...moved];
  withLayout(document, [...layoutEntries(document), { ref: KIN, chapter: "made", order: 5, role: "SIDEBAR" }]);
  const { document: shown, plan } = shownPage(document);
  const made = plan.chapters.find((chapter) => chapter.key === "made")!;
  expect(made.blocks.some((block) => block.kind === "passage" && block.asides?.some((aside) => aside.ref === KIN))).toBe(true);
  expect([...documentScopes(shown, plan, [made], false)].sort()).toEqual(["pt", "rm"]);
});

test("a crop reaches the picture: its frame takes the box's shape and the picture is centred on it", async ({ page }) => {
  const html = pageHtml(sizedDocument({ x: 0.25, y: 0.5, width: 0.5, height: 0.25 }));
  expect(home(html, COLUMN)).toContain('data-crop="" style="--kv-crop-x:0.25;--kv-crop-y:0.5;--kv-crop-w:0.5;--kv-crop-h:0.25;--kv-crop-ratio:2.6667"');
  expect(html.slice(html.indexOf(`data-component="${COLUMN}"`))).toMatch(/^[^]*?<img [^>]*style="object-position:50% 62.5%"/);
  await drawn(page, 1440, html);
  const box = await page.locator(`[data-component="${COLUMN}"] .ph`).evaluate((frame) => {
    const outer = frame.getBoundingClientRect();
    const picture = (frame.querySelector("img") as HTMLElement).getBoundingClientRect();
    return { ratio: outer.width / outer.height, left: (picture.left - outer.left) / outer.width, top: (picture.top - outer.top) / outer.height, width: picture.width / outer.width, height: picture.height / outer.height };
  });
  expect(box.ratio).toBeCloseTo(8 / 3, 2);
  expect(box.left).toBeCloseTo(-0.5, 2);
  expect(box.top).toBeCloseTo(-2, 2);
  expect(box.width).toBeCloseTo(2, 2);
  expect(box.height).toBeCloseTo(4, 2);
});

test("from 1200px the margin entry stands beside its paragraph, below 1200px inline after it, and each size has its width", async ({ page }) => {
  const html = pageHtml(sizedDocument());
  for (const width of [390, 834, 1440]) {
    await drawn(page, width, html);
    const run = `${width}`;
    expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth), run).toBeLessThanOrEqual(0);
    const place = await page.locator(`.margin-plate [data-component="${MARGIN}"]`).evaluate((node) => {
      const plate = node.getBoundingClientRect();
      const margin = (node.closest("aside") as HTMLElement).getBoundingClientRect();
      const main = (node.closest(".spread")?.querySelector(":scope > .main") as HTMLElement).getBoundingClientRect();
      return { shown: plate.width > 0 && plate.height > 0, beside: plate.left >= main.right && Math.abs(margin.top - main.top) < 12, below: margin.top >= main.bottom - 1 && Math.abs(plate.left - main.left) < 2 };
    });
    expect(place, run).toEqual({ shown: true, beside: width >= SPREAD_FROM, below: width < SPREAD_FROM });
    const widths = await page.evaluate((labels) => labels.map((label) => (document.querySelector(`[data-component="${label}"] figure`) as HTMLElement).getBoundingClientRect().width), [COLUMN, WIDE, BLEED]);
    const [column, wide, bleed] = widths;
    expect(bleed, run).toBeCloseTo(await page.evaluate(() => document.body.clientWidth), 0);
    expect(wide, run).toBeLessThan(bleed);
    expect(column, run).toBeLessThanOrEqual(wide);
    if (width >= SPREAD_FROM) expect([column <= READING_COLUMN, wide > READING_COLUMN], run).toEqual([true, true]);
  }
});

test("the figures a layout places in a chapter whose prose it leaves alone stand in the prose, after the paragraphs that tell them", () => {
  const chem = chapterOf(proseDocument(), "chem");
  expect(shape(chem.blocks)).toEqual(["passage", VAT, KILN, "passage", IRON]);
  const [head, , , tail] = chem.blocks;
  expect(head.kind === "passage" && head.pieces.map((piece) => (piece.kind === "unit" ? `${piece.ref}:${piece.role}` : piece.kind))).toEqual(["chapter-chem:title", "chemistry-1:lede", `${PULL}:pull`, "chem-vat-h:text", "paragraph"]);
  expect(head).toMatchObject({ asides: [{ after: PULL, ref: SIDE, kind: "unit" }] });
  expect(tail.kind === "passage" && tail.asides).toBeFalsy();
});

test("a pull quote is drawn as one after the chapter's lede and a sidebar sentence stands in the margin beside it", () => {
  const html = pageHtml(proseDocument());
  const lede = html.indexOf("Alum fixes the madder");
  const pull = html.indexOf('<blockquote class="kv-pull"><p>');
  const side = html.indexOf('<div class="margin-plate" data-beside="unit"><p class="kv-beside-note">');
  expect(lede).toBeGreaterThan(0);
  expect(pull).toBeGreaterThan(lede);
  expect(html.slice(pull)).toMatch(/^<blockquote class="kv-pull"><p><span class="s">The printers say the river makes the colour /);
  expect(side).toBeGreaterThan(pull);
  expect(html.slice(side)).toMatch(/^[^]*?A second bath deepens the red /);
  expect(side).toBeLessThan(html.indexOf("Indigo is reduced to leucoindigo"));
});

test("a chapter whose paragraphs the layout places keeps the layout's order exactly", () => {
  const document = proseDocument();
  withLayout(document, [...layoutEntries(document), { ref: "chem-vat", chapter: "chem", order: 6, role: "BODY" }]);
  expect(shape(chapterOf(document, "chem").blocks)).toEqual(["passage", IRON, VAT, KILN, "passage"]);
});

test("a document without layout data, or with a layout naming nothing, draws as before", () => {
  const html = pageHtml(templateDocument());
  const named = pageHtml(withLayout(templateDocument(), []));
  expect(named.replace(/<script type="application\/json" id="page-layout">[^<]*<\/script>/, "")).toBe(html);
  for (const marker of ["data-size", "data-crop", "kv-bleed", "margin-plate", "margin note keep", "kv-pull"]) expect(html, marker).not.toContain(marker);
  expect(html).toContain(`<div class="bx bx-rm my-12" data-component="${KIN}" data-component-kind="related_crafts" data-home="kind"><div class="screen"><div class="wrap kv-passage">`);
});
