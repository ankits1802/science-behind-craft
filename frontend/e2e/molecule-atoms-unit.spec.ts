import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { Molecule3d } from "../components/monograph/kinds/science/Molecule3d";
import { KIT_DEFS } from "../generated/kitDefs";
import { molecule3dShape } from "../lib/componentSpecsScienceFigures";
import type { MonographComponent } from "../lib/monographDocument";
import { parseShape } from "../lib/shape";

import { FRONTEND } from "./moduleGraph";
import { PRIMITIVE_CSS } from "./primitivesPage";

type Node = { tag: string; attrs?: Record<string, string>; children?: (Node | string)[] };

const KIT_CSS = readFileSync(join(FRONTEND, "public", "monographs", "kit", "monograph.css"), "utf8");
const TOKENS_CSS = readFileSync(join(FRONTEND, "app", "tokens.css"), "utf8");
const ROOT_BLOCK = TOKENS_CSS.slice(TOKENS_CSS.indexOf(":root {"), TOKENS_CSS.indexOf("}", TOKENS_CSS.indexOf(":root {")));
const LIGHT = { O: "rgb(195, 71, 40)", S: "rgb(114, 118, 26)", Fe: "rgb(142, 63, 52)" };
const DARK = { O: "rgb(232, 118, 39)", S: "rgb(222, 214, 106)", Fe: "rgb(195, 105, 83)" };
const THEMES = [
  ["light", 'data-theme="light"', LIGHT],
  ["dark", 'data-theme="dark"', DARK],
  ["high contrast light", 'data-theme="light" data-high-contrast="true"', LIGHT],
  ["high contrast dark", 'data-theme="dark" data-high-contrast="true"', DARK]
] as const;
const COMPONENT: MonographComponent = {
  label: "bagru-print/chemistry/ferrous-sulphate-3d",
  chapter: "chem",
  anchor: "#bagru-print--chemistry--ferrous-sulphate-3d",
  kind: "molecule_3d",
  title: "Ferrous sulphate in three dimensions",
  description: "Turns ferrous sulphate in three dimensions.",
  field: "CHEMISTRY",
  fields: [],
  subjects: ["craft:Bagru-Print"]
};

function atom(index: number, symbol: string, cx: string, r: string): Node {
  const letter: Node = { tag: "text", attrs: { x: cx, y: "0", "font-size": "0.12", "text-anchor": "middle", "dominant-baseline": "central", fill: "var(--mol-letter)" }, children: [symbol] };
  return { tag: "g", attrs: { "data-a": String(index) }, children: [{ tag: "circle", attrs: { cx, cy: "0", r, fill: `url(#ag-${symbol})`, stroke: "var(--mol-edge)", "stroke-width": "0.005" } }, letter] };
}

function ferrousSulphate(): Record<string, unknown> {
  const bond = (index: number, d: string): Node => ({ tag: "path", attrs: { "data-b": String(index), d, stroke: "var(--mol-bond)", "stroke-width": "0.03", "stroke-linecap": "round" } });
  const drawing: Node = {
    tag: "svg",
    attrs: { viewBox: "-1 -1 2 2", "aria-hidden": "true", focusable: "false" },
    children: [{ tag: "g", attrs: { class: "mol-g" }, children: [bond(0, "M-0.5 0L0 0"), bond(1, "M0 0L0.5 0"), atom(0, "S", "-0.5", "0.14"), atom(1, "O", "0", "0.1"), atom(2, "Fe", "0.5", "0.15")] }]
  };
  const model = {
    key: "m24393",
    cid: 24393,
    yaw: 0.4,
    pitch: 0.3,
    name: "Ferrous sulphate",
    dialLabel: "Turn the Ferrous sulphate model",
    formula: ["FeSO", { text: "4", style: "sub" }],
    atoms: "4 oxygen, 1 iron and 1 sulphur atoms. Drag, or use the arrow keys, to turn it; plus and minus zoom.",
    note: "Its 3D conformer is PubChem's record.",
    drawing
  };
  const key = [
    { swatch: "--atom-o", label: "Oxygen, O" },
    { swatch: "--atom-fe", label: "Iron, Fe" },
    { swatch: "--atom-s", label: "Sulphur, S" },
    { swatch: null, label: "3D conformers computed by PubChem." }
  ];
  return { head: { figure: null, number: "u5001", title: "u5002", titleId: null, dek: null }, molecules: [model], side: [], key };
}

function page(spec: Record<string, unknown>): string {
  const defs = ["ag-O", "ag-S", "ag-Fe"].map((id) => KIT_DEFS[id].markup).join("");
  const view = renderToStaticMarkup(createElement(Molecule3d, { component: COMPONENT, spec, unitRefs: ["u5001", "u5002"], renderUnit: (ref: string) => ref, renderComponent: () => null }));
  return `<div class="bx bx-chem"><svg class="kv-defs" width="0" height="0"><defs>${defs}</defs></svg>${view}</div>`;
}

test("every atom the design colours has its token and the kit's gradient, and every kit gradient its token", () => {
  const tokens = [...ROOT_BLOCK.matchAll(/--atom-([a-z]+): /g)].map((found) => found[1]);
  const gradients = Object.keys(KIT_DEFS).filter((id) => id.startsWith("ag-"));
  expect(tokens).toEqual(expect.arrayContaining(["c", "h", "n", "o", "s", "cl", "fe", "cu", "al", "ca", "na", "k", "cr", "sn", "zn", "ag", "au", "pb", "ti", "hg"]));
  expect(gradients.map((id) => id.slice(3).toLowerCase()).sort()).toEqual([...tokens].sort());
  for (const id of gradients) {
    expect(KIT_DEFS[id].scope, id).toBe("chem");
    expect(KIT_DEFS[id].markup, id).toContain(`var(--atom-${id.slice(3).toLowerCase()})`);
  }
});

test("a molecule of sulphur, oxygen and iron parses as the view draws it", () => {
  expect(() => parseShape(molecule3dShape, ferrousSulphate())).not.toThrow();
});

test("a molecule with sulphur and a metal draws each atom in its own colour, edged and lettered, in all four themes", async ({ page: browser }) => {
  for (const [name, attrs, colours] of THEMES) {
    await browser.setContent(`<!doctype html><html lang="en" ${attrs}><head><meta charset="utf-8"><style>${PRIMITIVE_CSS}</style><style>${KIT_CSS}</style></head><body>${page(ferrousSulphate())}</body></html>`, { waitUntil: "domcontentloaded" });
    for (const [symbol, colour] of Object.entries(colours)) {
      const stop = browser.locator(`#ag-${symbol} stop`).nth(1);
      expect(await stop.evaluate((found) => getComputedStyle(found).stopColor), `${name} ${symbol}`).toBe(colour);
    }
    const fills = await browser.locator(".mol-g circle").evaluateAll((circles) => circles.map((circle) => circle.getAttribute("fill") ?? ""));
    expect(fills).toEqual(["url(#ag-S)", "url(#ag-O)", "url(#ag-Fe)"]);
    for (const fill of fills) expect(await browser.locator(fill.slice(4, -1)).count(), `${name} ${fill}`).toBe(1);
    await expect(browser.locator(".mol-g text")).toHaveText(["S", "O", "Fe"]);
    const swatch = browser.locator(".atomkey i").nth(1);
    expect(await swatch.evaluate((found) => getComputedStyle(found).backgroundColor), name).toBe(colours.Fe);
    await expect(browser.locator(".atomkey")).toContainText("Iron, Fe");
  }
});
