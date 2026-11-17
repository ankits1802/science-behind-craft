import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { riverBasinOf } from "@/lib/riverTopology";

const ROOT = join(__dirname, "..", "..");
const shared = (name: string): unknown => JSON.parse(readFileSync(join(ROOT, "shared", name), "utf8"));
const PHASE_B = shared("explainer.phase-b.golden.json") as { placeholders: { mainRiv: number; reachIds: number[] } };
const HALF_STEP = 0.00001;

const basin = () => riverBasinOf(shared("river.topology.golden.json"), PHASE_B.placeholders.mainRiv);

test("the geo ETL's basin file parses with every reach of the fixture's river", () => {
  const found = basin();
  expect([...found.reaches.keys()].sort((a, b) => a - b)).toEqual([1, 2, 3, 4]);
  expect(PHASE_B.placeholders.reachIds.every((id) => found.reaches.has(id))).toBe(true);
  expect(found.reaches.get(PHASE_B.placeholders.mainRiv)?.nextDown).toBe(0);
});

test("each reach of the basin file ends where the reach it flows into starts", () => {
  const found = basin();
  for (const reach of found.reaches.values()) {
    if (reach.nextDown === 0) continue;
    expect(found.reaches.get(reach.nextDown)?.line[0]).toEqual(reach.line.at(-1));
  }
});

test("the basin file decodes to the source's coordinates within half a quantization step", () => {
  const [longitude, latitude] = basin().reaches.get(1)?.line[0] ?? [Number.NaN, Number.NaN];
  expect(Math.abs(longitude - 69.6)).toBeLessThan(HALF_STEP);
  expect(Math.abs(latitude - 23.45)).toBeLessThan(HALF_STEP);
  const [outletLongitude, outletLatitude] = basin().reaches.get(3)?.line.at(-1) ?? [Number.NaN, Number.NaN];
  expect(Math.abs(outletLongitude - 69.92)).toBeLessThan(HALF_STEP);
  expect(Math.abs(outletLatitude - 23.2)).toBeLessThan(HALF_STEP);
});
