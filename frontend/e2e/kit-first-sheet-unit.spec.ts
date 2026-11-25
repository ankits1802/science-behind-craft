import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { GET } from "../app/monographs/kit/first/[sheet]/route";
import { firstSheet, firstSheetHref, firstSheetName, firstSheetScopes, KIT_SCOPES, selectorScopes } from "../lib/kitFirstSheet";
import type { KitScope } from "../lib/monographScopes";
import nextConfig, { FIRST_SHEET_ROUTES, SERVED_KIT_CSS } from "../next.config";

import { FRONTEND } from "./moduleGraph";

const KIT = readFileSync(join(FRONTEND, SERVED_KIT_CSS), "utf8");
const UNDRAWN_OUTSIDE_NOT = /\.bx-(chem|pt|rm|mb|ask|sa)(?![\w-])/g;

const SAMPLE = [
  ":root { --gap: 1px; }",
  ".kicker { margin: var(--gap); }",
  ".bx-chem .rx { display: grid; }",
  ".bx-pt .stage, .bx-chem .stage { margin: 0; }",
  ".bx-rm .toast:not(.bx-pt) { inset: 0; }",
  ".x:not(.bx-pt) { gap: 1px; }",
  "@keyframes kv-dip { from { clip-path: inset(100% 0 0 0); } }",
  "@property --vat { syntax: '<number>'; inherits: true; initial-value: 0; }",
  "@media (min-width: 640px) {\n  .bx-pt .stage { gap: 2px; }\n  .kicker { gap: 3px; }\n}",
  "@media (min-width: 768px) {\n  .bx-rm .toast { gap: 4px; }\n}",
  '.kv-open-k span + span::before { content: "\\00B7{"; }',
  ""
].join("\n");

function drawn(...scopes: KitScope[]): Set<KitScope> {
  return new Set(scopes);
}

function scopesLeft(sheet: string, undrawn: readonly KitScope[]): string[] {
  const left: string[] = [];
  for (const found of sheet.matchAll(UNDRAWN_OUTSIDE_NOT)) {
    const before = sheet.slice(Math.max(0, (found.index ?? 0) - 60), found.index);
    const negated = before.lastIndexOf(":not(") > before.lastIndexOf(")");
    if (!negated && undrawn.includes(found[1] as KitScope)) left.push(found[0]);
  }
  return left;
}

function inOrder(sheet: string, kit: string): boolean {
  let from = 0;
  for (const line of sheet.split("\n").filter((text) => text.trim())) {
    const at = kit.indexOf(line, from);
    if (at < 0) return false;
    from = at + line.length;
  }
  return true;
}

test("a rule that needs a box the page does not draw is left out, and every rule it may still match is kept", () => {
  const sheet = firstSheet(SAMPLE, drawn("chem"));
  expect(sheet).toContain(".kicker { margin: var(--gap); }");
  expect(sheet).toContain(".bx-chem .rx { display: grid; }");
  expect(sheet).toContain(".bx-pt .stage, .bx-chem .stage { margin: 0; }");
  expect(sheet).toContain(".x:not(.bx-pt) { gap: 1px; }");
  expect(sheet).toContain("@keyframes kv-dip");
  expect(sheet).toContain("@property --vat");
  expect(sheet).toContain("@media (min-width: 640px) {\n  .kicker { gap: 3px; }\n}");
  expect(sheet).toContain('content: "\\00B7{"');
  expect(sheet).not.toContain(".bx-rm .toast");
  expect(sheet).not.toContain(".bx-pt .stage { gap: 2px; }");
  expect(sheet).not.toContain("min-width: 768px");
});

test("drawing every box gives the kit back byte for byte, and no box gives its unscoped rules alone", () => {
  expect(firstSheet(SAMPLE, new Set(KIT_SCOPES))).toBe(SAMPLE);
  expect(firstSheet(KIT, new Set(KIT_SCOPES))).toBe(KIT);
  const bare = firstSheet(SAMPLE, drawn());
  expect(bare).toContain(".x:not(.bx-pt) { gap: 1px; }");
  expect(scopesLeft(bare, KIT_SCOPES)).toEqual([]);
});

test("the kit's first sheet for a masthead and the chemistry keeps their rules and the page-wide ones in the kit's order, and no other box's", () => {
  const sheet = firstSheet(KIT, drawn("mb", "chem"));
  expect(firstSheet(sheet, drawn("mb", "chem"))).toBe(sheet);
  expect(inOrder(sheet, KIT)).toBe(true);
  for (const kept of [".bx[hidden] { display: none; }", ".bx-mb .pop[hidden]{ display: none; }", ".bx-chem .pop[hidden]{ display: none; }", ".bx-rm .toast-zone, #toasts {"]) expect(sheet, kept).toContain(kept);
  for (const left of [".bx-pt .stage[hidden]{ display: none; }", ".bx-pt .pop[hidden]{ display: none; }"]) expect(sheet, left).not.toContain(left);
  expect(sheet.length).toBeLessThan(KIT.length * 0.5);
  expect(firstSheet(KIT, drawn("mb")).length).toBeLessThan(sheet.length);
});

test("a selector needs the boxes it names outside a negation, never one it only excludes", () => {
  expect(selectorScopes(":root .bx-chem .rx")).toEqual(["chem"]);
  expect(selectorScopes(".bx-pt .a .bx-rm .b")).toEqual(["pt", "rm"]);
  expect(selectorScopes(".x:not(.bx-pt):where(.bx-rm .y)")).toEqual([]);
  expect(selectorScopes(".bx-chem-legend .x")).toEqual([]);
});

test("a first sheet is named by its boxes in the kit's order, and only that name is served", () => {
  expect(firstSheetName(drawn("mb", "chem"))).toBe("chem-mb.css");
  expect(firstSheetHref(drawn())).toBe("/monographs/kit/first/none.css");
  expect(firstSheetScopes("chem-mb.css")).toEqual(drawn("chem", "mb"));
  expect(firstSheetScopes("none.css")).toEqual(drawn());
  for (const refused of ["mb-chem.css", "chem-chem.css", "chem-ink.css", "chem-mb", "chem-mb.js", "../monograph.css"]) expect(firstSheetScopes(refused), refused).toBeNull();
});

test("the route serves the named first sheet as CSS and refuses any other name", async () => {
  const served = await GET(new Request("http://localhost/monographs/kit/first/chem-mb.css"), { params: Promise.resolve({ sheet: "chem-mb.css" }) });
  expect(served.status).toBe(200);
  expect(served.headers.get("content-type")).toBe("text/css; charset=utf-8");
  expect(await served.text()).toBe(firstSheet(KIT, drawn("mb", "chem")));
  const refused = await GET(new Request("http://localhost/monographs/kit/first/mb-chem.css"), { params: Promise.resolve({ sheet: "mb-chem.css" }) });
  expect(refused.status).toBe(404);
});

test("the served kit the route reads is traced into the route's function, and no other route's", () => {
  expect(nextConfig.outputFileTracingIncludes).toEqual({ [FIRST_SHEET_ROUTES]: [SERVED_KIT_CSS] });
  expect(firstSheetHref(drawn("mb")).startsWith(FIRST_SHEET_ROUTES.slice(0, -1))).toBe(true);
  expect(readFileSync(join(FRONTEND, "app", "monographs", "kit", "first", "[sheet]", "route.ts"), "utf8")).toContain('join(process.cwd(), "public", "monographs", "kit", "monograph.css")');
});
