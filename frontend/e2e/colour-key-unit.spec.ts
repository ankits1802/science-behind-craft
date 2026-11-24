import { expect, test, type Page } from "@playwright/test";
import { createElement, type ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { AuthProvider } from "../components/AuthProvider";
import { SwatchCardsView } from "../components/monograph/kinds/plates/SwatchCardsView";
import { KitMasthead } from "../components/monograph/KitMasthead";
import { MonographPage } from "../components/monograph/MonographPage";
import { ThemeProvider } from "../components/ThemeProvider";
import { swatchCardsShape } from "../lib/componentSpecsPlates";
import type { MonographComponent, MonographDocument, MonographUnit } from "../lib/monographDocument";
import { pagePlan } from "../lib/monographRenderLayout";
import { parseShape, ShapeError } from "../lib/shape";

import { generatedDocument, HERO } from "./generatedMonographFixture";

const KEY = "bagh-print/chemistry/colour-key";
const NAME = "Bagh Print";
const markup = (element: ReactElement) => renderToStaticMarkup(element);
const provided = (element: ReactElement) => markup(createElement(AuthProvider, null, createElement(ThemeProvider, null, element)));

const KEY_COMPONENT: MonographComponent = {
  label: KEY,
  chapter: "chem",
  anchor: "#bagh-print--chemistry--colour-key",
  kind: "swatch_cards",
  title: "Two colours and what gives each",
  description: "The colours the cited facts of Bagh Print name.",
  field: "CHEMISTRY",
  fields: ["CHEMISTRY", "PROCESS"],
  subjects: ["craft:Bagh-Print"]
};

const KEY_SPEC = {
  chapterNo: "u8901",
  title: "u8902",
  titleId: "colour-key-h",
  intro: "u8903",
  weave: "mb-weave",
  colours: [
    { before: { dye: "leuco", caption: "u8904" }, join: "becomes", after: { dye: "indigo", caption: "u8905" }, name: "u8906", agent: "u8907", text: "u8908", why: "u8909" },
    { after: { dye: "harda", caption: "u8910" }, name: "u8911", agent: "u8912", text: "u8913" },
    { name: "u8914", agent: "u8915", text: "u8916" }
  ]
};

function colourCards(html: string): string[] {
  return html.split('<li class="colour">').slice(1);
}

function drawnKey(spec: Record<string, unknown>): string {
  const renderUnit = (ref: string) => createElement("span", null, ref);
  return markup(createElement(SwatchCardsView, { component: KEY_COMPONENT, spec, unitRefs: [], renderUnit, renderComponent: () => null }));
}

test("a key card draws its stated change as a swatch pair, a colour a token depicts as one swatch, and any other colour in words", () => {
  const [pair, single, words] = colourCards(drawnKey(KEY_SPEC));
  expect(pair).toContain('fill="var(--dye-leuco)"');
  expect(pair).toContain('<span class="pair-arrow" aria-hidden="true">→</span>');
  expect(pair).toContain('fill="var(--dye-indigo)"');
  expect(pair).toContain('<p class="ctext"><span>u8908</span> <span>u8909</span></p>');
  expect(single).toContain('<div class="pair"><figure><div class="sq"><span class="swatch"><svg viewBox="0 0 80 80" aria-hidden="true"><rect width="80" height="80" fill="var(--dye-harda)"></rect><rect width="80" height="80" fill="url(#mb-weave)"></rect></svg></span></div><figcaption><span>u8910</span></figcaption></figure></div>');
  expect(single).not.toContain("pair-arrow");
  expect(single).toContain('<p class="ctext"><span>u8913</span></p>');
  expect(words).toBe('<h3><span>u8914</span></h3><p class="agent"><span>u8915</span></p><p class="ctext"><span>u8916</span></p></li></ul></div></section>');
  expect(drawnKey(KEY_SPEC).match(/fill="url\(#mb-weave\)"/g)).toHaveLength(3);
});

test("a key refuses a before swatch without its after swatch, and a join without a before swatch", () => {
  const named = { name: "u8906", agent: "u8907", text: "u8908" };
  const parsed = (colour: Record<string, unknown>) => parseShape(swatchCardsShape, { ...KEY_SPEC, colours: [colour] }, "refuse");
  expect(parsed(named).colours).toEqual([named]);
  expect(() => parsed({ ...named, before: { dye: "leuco", caption: "u8904" }, join: "becomes" })).toThrow(ShapeError);
  expect(() => parsed({ ...named, join: "or", after: { dye: "indigo", caption: "u8905" } })).toThrow(ShapeError);
  expect(() => parsed({ ...named, before: { dye: "leuco", caption: "u8904" }, after: { dye: "indigo", caption: "u8905" } })).toThrow(ShapeError);
  expect(() => parsed({ ...named, after: { dye: "marigold", caption: "u8905" } })).toThrow(ShapeError);
});

const plain = (text: string): MonographUnit => ({ chapter: "chem", tag: "span", field: null, nodes: [text], claimIds: [] });
const cited = (key: string, head: string, last: string, source: string): MonographUnit => ({
  chapter: "chem",
  tag: "span",
  field: "CHEMISTRY",
  nodes: [{ m: "s", c: [head, { m: "cite", key, g: [source], c: [last] }] }],
  claimIds: [`claim-${key}`]
});

function keyedDocument(): MonographDocument {
  const document = generatedDocument();
  const spec = { ...KEY_SPEC, colours: [{ after: { dye: "indigo", caption: "u8904" }, name: "u8905", agent: "u8906", text: "u8907" }, { name: "u8908", agent: "u8909", text: "u8910" }] };
  const units: Record<string, MonographUnit> = {
    u8901: plain("Colour key"),
    u8902: plain("Two colours and what gives each"),
    u8903: plain("Blue and yellow."),
    u8904: plain("Indigo dyeing"),
    u8905: plain("Blue"),
    u8906: plain("Indigo"),
    u8907: cited("u8907", "Blue in the ", "air.", "g2"),
    u8908: plain("Yellow"),
    u8909: plain("Marigold"),
    u8910: cited("u8910", "A bright ", "yellow.", "g1")
  };
  const content = document.content;
  content.units = { ...content.units, ...units };
  content.citations = { ...content.citations, u8907: [{ source: "g2", locator: "p. 4", quote: "turns blue in the air" }], u8910: [{ source: "g1", locator: "p. 5", quote: "gives a bright yellow" }] };
  content.components = [...content.components, KEY_COMPONENT];
  const at = content.layout.findIndex((entry) => entry.ref === "chapter-chem") + 1;
  const held = Object.keys(units).map((ref) => ({ chapter: "chem", kind: "unit" as const, ref, within: KEY }));
  content.layout = [...content.layout.slice(0, at), { chapter: "chem", kind: "component", ref: KEY, within: null }, ...held, ...content.layout.slice(at)];
  document.specs = { ...document.specs, [KEY]: spec };
  return document;
}

test("a generated page draws its colour key at the head of its chemistry chapter, in the approved section, with the kit's weave and its citations", () => {
  const html = provided(createElement(MonographPage, { document: keyedDocument() }));
  const chem = html.slice(html.indexOf('<section class="kv-ch" id="chem"'), html.indexOf('<section class="kv-ch" id="sources"'));
  expect(chem.indexOf(`data-component="${KEY}"`)).toBeGreaterThan(chem.indexOf('id="chem-h">The chemistry</h2>'));
  expect(chem.indexOf(`data-component="${KEY}"`)).toBeLessThan(chem.indexOf("Alum fixes the madder"));
  expect(chem).toContain(`<div class="bx bx-mb my-12" data-component="${KEY}" data-component-kind="swatch_cards" data-home="kind"><div class="screen"><section class="four" aria-labelledby="colour-key-h">`);
  expect(chem).toContain('<h2 class="t-h2" id="colour-key-h">Two colours and what gives each</h2>');
  expect(chem).toContain('fill="var(--dye-indigo)"');
  expect(chem).toContain('<li class="colour"><h3>Yellow</h3>');
  expect(chem.match(/class="kcite"/g)?.length).toBeGreaterThanOrEqual(3);
  expect(html).toContain('<pattern id="mb-weave"');
});

async function readAloud(page: Page, html: string): Promise<{ shown: number; read: number }> {
  await page.setContent(`<!doctype html><html lang="en"><body>${html}</body></html>`, { waitUntil: "domcontentloaded" });
  return page.evaluate((name) => {
    const hidden = (node: Element | null) => Boolean(node?.closest('[aria-hidden="true"]'));
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let shown = 0;
    let read = 0;
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (!(node.textContent ?? "").includes(name)) continue;
      shown += 1;
      if (!hidden(node.parentElement)) read += 1;
    }
    read += [...document.querySelectorAll("img")].filter((image) => image.alt.includes(name) && !hidden(image)).length;
    return { shown, read };
  }, NAME);
}

function mastheadOf(document: MonographDocument): string {
  return markup(createElement(KitMasthead, { document, label: pagePlan(document).label! }));
}

function withoutPhotograph(): MonographDocument {
  const document = generatedDocument();
  document.content.layout = document.content.layout.filter((entry) => entry.ref !== HERO && entry.within !== HERO);
  document.content.components = [];
  document.specs = {};
  return document;
}

test("the masthead names the craft once to a screen reader, with or without its photograph, as its title", async ({ page }) => {
  for (const document of [generatedDocument(), withoutPhotograph()]) {
    const html = mastheadOf(document);
    expect(await readAloud(page, html)).toEqual({ shown: 2, read: 1 });
    await expect(page.getByRole("heading", { level: 1, name: NAME })).toHaveCount(1);
  }
});

test("without a photograph the masthead draws the title and the family's plate, and no second label naming the craft", () => {
  const html = mastheadOf(withoutPhotograph());
  expect(html.match(/Bagh Print/g)).toHaveLength(2);
  expect(html).toContain('<h1 class="kv-q">Bagh Print</h1>');
  expect(html).toMatch(/<div class="kv-plate g-textile[^"]*" data-size="masthead" data-material="textile" aria-hidden="true" data-testid="typographic-plate">/);
  expect(html).toContain('<span class="kv-plate-name kv-knock" data-latin="">Bagh Print</span>');
  expect(html).toContain("Hand block printing</span>");
});
