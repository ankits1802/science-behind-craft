import { expect, test } from "@playwright/test";

import { chapterLabel, designCritiqueShape, NO_NOTES, noteHeading, notesLine } from "@/lib/designCritique";
import { reviewQueuePageShape, type LayoutItem } from "@/lib/reviewQueueContract";
import { parseShape } from "@/lib/shape";

const CRITIQUE = {
  verdict: "The making chapter is a wall of prose.",
  notes: [
    { chapter: "made", where: "the eight paragraphs on washing", problem: "A wall of text with no figure beside it.", fix: "Step through the washes with a stage player." },
    { chapter: "why-kachchh", where: "Figure 4, the map", problem: "It frames all of India.", fix: "Frame it to the district the story is about." }
  ]
};

const REVIEW = {
  subject: { kind: "craft", slug: "Sanganeri-Hand-Block-Printing" },
  subjectName: "Sanganeri Hand Block Printing",
  pageUrl: "/crafts/Sanganeri-Hand-Block-Printing",
  baseVersion: 0,
  currentVersion: 0,
  stale: false,
  note: null,
  entryCount: 0,
  changes: []
};

function page(layout: object) {
  return {
    schemaVersion: 1,
    kinds: ["LAYOUTS"],
    counts: { LAYOUTS: 1 },
    total: 1,
    items: [
      {
        id: "00000000-0000-4000-8000-000000000011",
        origin: "AGENT",
        submittedAt: "2026-11-26T09:00:00Z",
        craft: { slug: "Sanganeri-Hand-Block-Printing", name: "Sanganeri Hand Block Printing", path: "/crafts/Sanganeri-Hand-Block-Printing" },
        proposer: null,
        kind: "LAYOUTS",
        layout
      }
    ],
    nextCursor: null
  };
}

test("a layout proposal carries the agent's critique to the reviewer, and reads whole without one", () => {
  const carried = parseShape(reviewQueuePageShape, page({ ...REVIEW, critique: CRITIQUE })).items[0] as LayoutItem;
  expect(carried.layout.critique).toEqual(CRITIQUE);
  const bare = parseShape(reviewQueuePageShape, page({ ...REVIEW, critique: null })).items[0] as LayoutItem;
  expect(bare.layout.critique).toBeNull();
  const older = parseShape(reviewQueuePageShape, page(REVIEW)).items[0] as LayoutItem;
  expect(older.layout.critique).toBeUndefined();
});

test("a critique off its shape is refused", () => {
  expect(() => parseShape(designCritiqueShape, { notes: [] })).toThrow();
  expect(() => parseShape(designCritiqueShape, { verdict: "Set well.", notes: [{ chapter: "made", where: "x" }] })).toThrow();
});

test("each note is headed by its chapter in words and the count reads in order", () => {
  expect(noteHeading(CRITIQUE.notes[1])).toBe("Why kachchh: Figure 4, the map");
  expect(chapterLabel("opening")).toBe("Opening");
  expect(notesLine(CRITIQUE)).toBe("2 notes, in reading order.");
  expect(notesLine({ verdict: "One.", notes: [CRITIQUE.notes[0]] })).toBe("1 note, in reading order.");
  expect(notesLine({ verdict: "Set well.", notes: [] })).toBe(NO_NOTES);
});
