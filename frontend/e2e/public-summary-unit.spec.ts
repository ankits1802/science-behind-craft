import { expect, test } from "@playwright/test";

import { parsePublicSummary, publicSummaryShape, PUBLIC_SUMMARY_PATH, summarySentences } from "@/lib/publicSummaryContract";
import { parseShape, ShapeError } from "@/lib/shape";

import { readRepo } from "./phaseBFixture";

type Golden = Record<string, unknown> & { sources: unknown[]; featured: unknown[] };

function golden(): Golden {
  return JSON.parse(readRepo("shared", "public.summary.golden.json")) as Golden;
}

test("the public summary parses exactly as the backend writes it", () => {
  const raw = golden();
  expect(parseShape(publicSummaryShape, raw) as unknown).toEqual(raw);
  const summary = parsePublicSummary(raw);
  expect(PUBLIC_SUMMARY_PATH).toBe("/public/summary");
  expect(summary.featured.map((entry) => entry.craft.slug)).toEqual(["Kutch-Ajrakh", "Bastar-Dhokra", "Tikuli-Painting"]);
  expect(summary.featured.map((entry) => entry.hero === null)).toEqual([false, false, true]);
  expect(summary.specimen?.sentence.citations.every((citation) => citation.quote)).toBe(true);
  expect(summarySentences(summary)).toHaveLength(4);
});

test("a summary whose sources are out of citation order or carry an extra featured craft is refused", () => {
  const reordered = golden();
  reordered.sources = [...reordered.sources].reverse();
  expect(() => parsePublicSummary(reordered)).toThrow(ShapeError);
  const crowded = golden();
  crowded.featured = [...crowded.featured, crowded.featured[0]];
  expect(() => parsePublicSummary(crowded)).toThrow(ShapeError);
});
