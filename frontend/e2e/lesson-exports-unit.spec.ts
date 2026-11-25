import { expect, test } from "@playwright/test";

import { citationExportShape, exportLinkShape, type ExportLink } from "@/lib/lessonContract";
import { parseShape, ShapeError } from "@/lib/shape";

import { readRepo } from "./phaseBFixture";

const LINK: ExportLink = {
  schemaVersion: 1,
  format: "pptx",
  fileName: "KalaVigyan_Lesson_2026-11-18_Kutch-Ajrakh_How-Is-Kutch-Ajrakh-Made-And-Why-Does_Slides.pptx",
  url: "https://kalavigyan-media.s3.ap-south-1.amazonaws.com/exports/7/abc/KalaVigyan_Lesson.pptx?X-Amz-Signature=1",
  expiresAt: "2026-11-18T10:05:00Z"
};

test("a lesson file, an explainer PDF or a page's Word document is answered as a short-lived link with its file name", () => {
  expect(parseShape(exportLinkShape, LINK)).toEqual(LINK);
  const page = { ...LINK, format: "docx" as const, fileName: "KalaVigyan_Craft-Page_2026-11-25_Kutch-Ajrakh_Export_v1.docx" };
  expect(parseShape(exportLinkShape, page)).toEqual(page);
  expect(() => parseShape(exportLinkShape, { ...LINK, url: "http://example.org/a.pptx" })).toThrow(ShapeError);
  expect(() => parseShape(exportLinkShape, { ...LINK, fileName: "../a.pptx" })).toThrow(ShapeError);
  expect(() => parseShape(exportLinkShape, { ...LINK, format: "xlsx" })).toThrow(ShapeError);
});

test("each citation carries the day its source was read", () => {
  const citations = JSON.parse(readRepo("shared", "learning.citations.golden.json")) as { entries: { csl: Record<string, unknown> }[] };
  const parsed = parseShape(citationExportShape, citations);
  expect(parsed.entries.map((entry) => entry.csl.accessed)).toEqual(Array(6).fill({ "date-parts": [[2026, 10, 14]] }));
  expect(parsed.entries[4].apa).toContain("Retrieved October 14, 2026, from https://exhibitions-khamir.org/");
});
