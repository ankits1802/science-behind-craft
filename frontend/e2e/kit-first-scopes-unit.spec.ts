import { expect, test } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { AuthProvider } from "../components/AuthProvider";
import { KitRestSheet, KitSheetLink } from "../components/monograph/KitRestSheet";
import { MonographPage } from "../components/monograph/MonographPage";
import { ThemeProvider } from "../components/ThemeProvider";
import { firstSheetScopes, KIT_SCOPES } from "../lib/kitFirstSheet";
import { markupScopes } from "../lib/kitShellScopes";
import { kindPreviewDocument } from "../lib/kindPreview";
import { MONOGRAPH_KIT_CSS, type MonographDocument } from "../lib/monographDocument";
import type { KitScope } from "../lib/monographScopes";

import { generatedDocument } from "./generatedMonographFixture";
import { goldenDocument } from "./monographNative";
import { filedKindFixtures, phoneFixtureDocument } from "./phoneFixturePage";

const FIRST_SHEET = /<link rel="stylesheet" href="\/monographs\/kit\/first\/([^"]+)"[^>]*>/g;
const DRAWN_START = 'id="kv-main"';
const DRAWN_END = '<footer class="kv-foot"';

type Drawn = { sheets: (Set<KitScope> | null)[]; boxes: Set<KitScope>; html: string };

function drawnPage(document: MonographDocument, deferred: boolean): Drawn {
  const html = renderToStaticMarkup(createElement(AuthProvider, null, createElement(ThemeProvider, null, createElement(MonographPage, { document, deferred }))));
  const main = html.slice(html.indexOf(DRAWN_START), html.indexOf(DRAWN_END));
  return { sheets: [...html.matchAll(FIRST_SHEET)].map((found) => firstSheetScopes(found[1])), boxes: new Set(markupScopes(main)), html };
}

function pages(): [string, MonographDocument][] {
  const kinds = kindPreviewDocument(filedKindFixtures());
  return [
    ["Kutch Ajrakh", goldenDocument()],
    ["the phone fixtures", phoneFixtureDocument()],
    ["a generated page", generatedDocument()],
    ["the page of every kind", kinds]
  ];
}

test("every box a page draws on the server has its kit rules in the one first sheet the page links", () => {
  for (const [name, document] of pages()) {
    for (const deferred of [true, false]) {
      const drawn = drawnPage(document, deferred);
      expect(drawn.sheets, `${name}, deferred ${deferred}`).toHaveLength(1);
      const sheet = drawn.sheets[0] ?? new Set<KitScope>();
      expect([...drawn.boxes].filter((scope) => !sheet.has(scope)), `${name}, deferred ${deferred}`).toEqual([]);
    }
  }
});

test("a box only the deferred rest draws stays out of the first sheet, and the page drawn whole names it", () => {
  for (const document of [goldenDocument(), phoneFixtureDocument()]) {
    const [lead, whole] = [drawnPage(document, true), drawnPage(document, false)];
    const [leadSheet, wholeSheet] = [lead.sheets[0] ?? new Set<KitScope>(), whole.sheets[0] ?? new Set<KitScope>()];
    expect([...leadSheet].filter((scope) => !wholeSheet.has(scope)), document.subjectSlug).toEqual([]);
    expect(KIT_SCOPES.filter((scope) => wholeSheet.has(scope) && !leadSheet.has(scope)).length, document.subjectSlug).toBeGreaterThan(0);
    expect([...leadSheet].filter((scope) => !lead.boxes.has(scope)), `${document.subjectSlug} links rules for boxes its lead does not draw`).toEqual([]);
  }
});

test("the server links the full kit nowhere, and the kit after hydration and the drawn rest link it once", () => {
  for (const [name, document] of pages()) expect(drawnPage(document, true).html, name).not.toContain(`href="${MONOGRAPH_KIT_CSS}"`);
  expect(renderToStaticMarkup(createElement(KitRestSheet))).toBe("");
  expect(renderToStaticMarkup(createElement(KitSheetLink))).toContain(`href="${MONOGRAPH_KIT_CSS}"`);
});
