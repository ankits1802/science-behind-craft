import { readFileSync } from "node:fs";
import { join } from "node:path";
import { createElement } from "react";

import { expect, test } from "@playwright/test";

import { LedeBlock } from "@/components/answer/LedeBlock";
import { BUILT_FIGURE_KINDS, explainerBlockShape, ledeBlockShape, signatureFigureShape } from "@/lib/explainerContract";
import { SIGNATURE_KINDS, signatureSentences, signatureSourceIds } from "@/lib/explainerSignature";
import { parseExplainerStreamBlock } from "@/lib/explainerStream";
import { parseShape, ShapeError } from "@/lib/shape";

import { withApp } from "./explainerRender";

const SHARED = join(__dirname, "..", "..", "shared");

function golden(name: string): unknown {
  return JSON.parse(readFileSync(join(SHARED, name), "utf8"));
}

const FIGURES = golden("explainer.signature.golden.json") as Record<string, unknown>[];
const LEDE = golden("explainer.signature-lede.golden.json") as Record<string, unknown>;

test("every signature figure the backend builds parses as it is written, one of each kind in order", () => {
  expect([...BUILT_FIGURE_KINDS]).toEqual([...SIGNATURE_KINDS]);
  expect(FIGURES.map((figure) => figure.kind)).toEqual([...SIGNATURE_KINDS]);
  for (const figure of FIGURES) expect(parseShape(signatureFigureShape, figure)).toEqual(figure);
});

test("the figured lede parses as the backend writes it and its figure is the mordant bath of alum red and iron black", () => {
  const lede = parseShape(ledeBlockShape, LEDE);
  expect(lede).toEqual(LEDE);
  const figure = lede.figure;
  expect(figure?.kind).toBe("mordant_bath");
  if (figure?.kind !== "mordant_bath") return;
  expect([figure.dye, figure.fibre]).toEqual(["madder", "cotton"]);
  expect(figure.swatches.map((swatch) => [swatch.mordant, swatch.colour])).toEqual([
    ["alum", "red"],
    ["iron", "black"]
  ]);
  expect(signatureSentences(figure).map((sentence) => sentence.id)).toEqual(["lede.figure.1", "lede.figure.2"]);
});

test("the indigo vat names its compound record as a source", () => {
  const vat = parseShape(signatureFigureShape, FIGURES[0]);
  expect(vat.kind).toBe("indigo_vat");
  expect(signatureSourceIds(vat)).toHaveLength(1);
  expect(signatureSentences(vat).every((sentence) => sentence.citations.length > 0)).toBe(true);
});

test("a figure rides the lede event but never sits in a section", () => {
  for (const figure of FIGURES) {
    const event = parseExplainerStreamBlock(`event: lede\ndata: ${JSON.stringify({ block: { ...LEDE, figure } })}`);
    expect(event?.type).toBe("lede");
    expect(() => parseShape(explainerBlockShape, { ...figure, id: "s1.b9" })).toThrow(ShapeError);
  }
});

test("today's lede draws its sentences and leaves a figure it has no renderer for undrawn", () => {
  const lede = parseShape(ledeBlockShape, LEDE);
  const html = withApp(createElement(LedeBlock, { lede, reduce: true }));
  expect(html).toContain('data-testid="answer-lede"');
  expect(html).not.toContain('data-testid="explainer-block"');
  expect(html).not.toContain('class="mt-5"');
});
