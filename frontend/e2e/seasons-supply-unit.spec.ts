import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";
import { createElement } from "react";

import { SeasonsStrip } from "@/components/answer/place/SeasonsStrip";
import { BLOCK_SHAPES, BUILT_BLOCK_KINDS, explainerBlockShape } from "@/lib/explainerContract";
import type { SeasonsBlock } from "@/lib/explainerPlace";
import { parseShape } from "@/lib/shape";

import { withReading } from "./explainerRender";

const FIXTURE = JSON.parse(readFileSync(join(__dirname, "..", "..", "shared", "explainer.phase-b.golden.json"), "utf8")) as {
  sections: { blocks: { id: string }[] }[];
};
const STAGE = "6b0f7a52-5d55-5c8e-9d6e-7b1a3c2e9f10";

function fixtureBlock(id: string): Record<string, unknown> {
  const found = FIXTURE.sections.flatMap((section) => section.blocks).find((block) => block.id === id);
  if (!found) throw new Error(`the phase B fixture has block ${id}`);
  return structuredClone(found) as Record<string, unknown>;
}

test("seasons and supply maps are built kinds the explainer parser admits", () => {
  const built: readonly string[] = BUILT_BLOCK_KINDS;
  expect(built).toContain("seasons");
  expect(built).toContain("supply_map");
  for (const id of ["s3.b1", "s6.b1"]) expect(parseShape(explainerBlockShape, fixtureBlock(id))).toEqual(fixtureBlock(id));
});

test("a stage with no dated claim is listed without months, and a mapped season fills its months with its chip", () => {
  const block = parseShape(BLOCK_SHAPES.seasons, fixtureBlock("s3.b1"));
  const [first] = block.rows;
  const second = { ...first, sentence: { ...first.sentence, id: "s3.b1.2" } };
  const strip: SeasonsBlock = { ...block, rows: [{ ...first, stageId: STAGE, label: "Pa (alum mordant printing for red)", months: [], season: null }, { ...second, months: [6, 7, 8, 9] }] };
  const html = withReading(createElement(SeasonsStrip, { block: parseShape(BLOCK_SHAPES.seasons, strip) }));
  expect(html.match(/data-testid="season-row"/g)).toHaveLength(2);
  expect(html.match(/data-testid="month-cells"/g)).toHaveLength(1);
  expect(html.match(/data-testid="season-chip"[^>]*>Monsoon</g)).toHaveLength(1);
  const cells = [...html.matchAll(/data-on="(true|false)"/g)].map((found) => found[1] === "true");
  expect(cells.map((on, index) => (on ? index + 1 : 0)).filter(Boolean)).toEqual([6, 7, 8, 9]);
  expect(html).toContain("Pa (alum mordant printing for red)");
  for (const row of strip.rows) expect(html).toContain(row.sentence.text);
});
