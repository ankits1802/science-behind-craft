import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { SpecDrawing } from "@/components/monograph/kinds/plates/SpecDrawing";
import { Drawing } from "@/components/monograph/kinds/science/parts/Drawing";
import { drawingShape, labelCardShape, type DrawingElement } from "@/lib/componentSpecsPlates";
import { svgNodeShape } from "@/lib/componentSpecsScienceParts";
import { DRAWING_REFUSALS, DRAWING_STYLE_PROPERTIES, drawingAttributeRefusal } from "@/lib/drawingAttributes";
import { parseShape, ShapeError, type Shape } from "@/lib/shape";

type Case = { name: string; value: string; why: string };
type Cases = { styleProperties: string[]; kept: Case[]; refused: Case[] };

const CASES = JSON.parse(readFileSync(join(__dirname, "..", "..", "shared", "drawing.attributes.golden.json"), "utf8")) as Cases;
const SHAPES: [string, Shape<unknown>][] = [
  ["a plate's drawing element", drawingShape],
  ["a science drawing node", svgNodeShape]
];
const BEACON = "background-image:url(https://attacker.example/p.png)";

function rect(attrs: Record<string, string>) {
  return { tag: "rect", attrs, children: [] };
}

function labelCard(style: string) {
  return { variant: "gi", kicker: "u0844", seal: { tag: "svg", attrs: { viewBox: "0 0 10 10", style }, children: [] }, sentence: "u0846", inset: null, facts: [{ term: "u0852", value: "u0853" }] };
}

test("both sides hold one list of the style properties a drawing may set, and none places, layers or loads", () => {
  expect([...DRAWING_STYLE_PROPERTIES].sort()).toEqual(CASES.styleProperties);
  for (const name of ["position", "inset", "z-index", "cursor", "background-image", "content"]) expect(CASES.styleProperties).not.toContain(name);
});

for (const [kind, shape] of SHAPES) {
  test(`${kind} keeps its paint, stroke, opacity, transform, text and in-drawing references`, () => {
    for (const kept of CASES.kept) {
      expect(drawingAttributeRefusal(kept.name, kept.value), kept.why).toBeNull();
      expect(() => parseShape(shape, rect({ [kept.name]: kept.value })), kept.why).not.toThrow();
    }
  });

  test(`${kind} loads nothing from another address and lays nothing over the page`, () => {
    for (const refused of CASES.refused) expect(() => parseShape(shape, rect({ [refused.name]: refused.value })), refused.why).toThrow(ShapeError);
  });
}

test("a label card's seal that would beacon every reader is refused, and a painted seal is drawn with its style", () => {
  expect(() => parseShape(labelCardShape, labelCard(BEACON))).toThrow(DRAWING_REFUSALS.load);
  expect(() => parseShape(labelCardShape, labelCard("position:fixed;inset:0;z-index:9999"))).toThrow(DRAWING_REFUSALS.style);
  const card = parseShape(labelCardShape, labelCard("fill:var(--dye-mud);opacity:1"));
  const seal = renderToStaticMarkup(createElement("div", null, createElement(SpecDrawing, { element: card.seal as DrawingElement })));
  expect(seal).toContain('style="fill:var(--dye-mud);opacity:1"');
});

test("a science scene written in capitals or as an image set is refused, and a tokened one is drawn", () => {
  for (const style of ["fill:URL(https://attacker.example/p.png)", 'fill:image-set("https://attacker.example/p.png" 1x)']) {
    expect(() => parseShape(svgNodeShape, { tag: "svg", attrs: { viewBox: "0 0 10 10", style } })).toThrow(ShapeError);
  }
  const node = parseShape(svgNodeShape, { tag: "svg", attrs: { viewBox: "0 0 10 10", style: "--k:2;transform:scaleY(1)" }, children: [{ tag: "circle", attrs: { r: "4", fill: "var(--ink-1)" } }] });
  expect(renderToStaticMarkup(createElement(Drawing, { node }))).toContain('style="--k:2;transform:scaleY(1)"');
});
