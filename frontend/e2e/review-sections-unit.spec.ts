import { expect, test } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { QueueItemView, type QueueHandlers } from "@/components/review/QueueItemView";
import { countsLine } from "@/lib/pageHoldContract";
import { PART_KINDS, PART_QUEUES } from "@/lib/pageProposalContract";
import { reviewQueuePageShape, type SectionItem } from "@/lib/reviewQueueContract";
import { KIND_LABELS, KIND_NOUNS, kindTabs } from "@/lib/reviewQueueView";
import type { SectionReview } from "@/lib/sectionReviewContract";
import { NO_PUBLISHED, publishedTitle, sectionActions, sectionHeadline, sectionWritesLine } from "@/lib/sectionReviewView";
import { parseShape } from "@/lib/shape";
import { STAGED_KIND_ACTIONS, STAGED_KIND_LABELS } from "@/lib/stagedReviewView";

const ALUM = { id: "00000000-0000-4000-8000-0000000000a1", text: "Alum is printed on the cloth before the madder bath." };
const MADDER = { id: "00000000-0000-4000-8000-0000000000a2", text: "Madder gives a red colour on cotton." };
const PROPOSED = [
  { text: "Alum is printed on the cloth before it goes into the madder bath.", facts: [ALUM] },
  { text: "Madder gives the cotton its red.", facts: [MADDER] }
];
const PUBLISHED = [{ text: "Madder gives a red colour on cotton.", facts: [MADDER] }];

const REVIEW = {
  subject: { kind: "craft", slug: "Sanganeri-Hand-Block-Printing" },
  subjectName: "Sanganeri Hand Block Printing",
  pageUrl: "/crafts/Sanganeri-Hand-Block-Printing",
  field: "CHEMISTRY",
  proposed: PROPOSED,
  published: PUBLISHED,
  publishedVersion: 2,
  note: "The chemistry field held its facts as a list.",
  taskKey: "SECTION:craft:Sanganeri-Hand-Block-Printing:CHEMISTRY",
  checks: [
    { check: "HELD", passed: true, reasons: ["every fact the section cites is a shown fact of this page"] },
    { check: "FAITHFUL", passed: true, reasons: ["the judge (judge-model-1) found nothing a sentence says that its facts do not"] }
  ],
  stale: null
};

const ITEM = {
  id: "00000000-0000-4000-8000-000000000031",
  origin: "AGENT",
  submittedAt: "2026-11-28T09:00:00Z",
  craft: { slug: "Sanganeri-Hand-Block-Printing", name: "Sanganeri Hand Block Printing", path: "/crafts/Sanganeri-Hand-Block-Printing" },
  proposer: null,
  kind: "SECTIONS",
  section: REVIEW
};

const PAGE = { schemaVersion: 1, kinds: ["STRUCTURE", "SECTIONS"], counts: { STRUCTURE: 0, SECTIONS: 1 }, total: 1, items: [ITEM], nextCursor: null };
const HANDLERS: QueueHandlers = { decide: async () => null, decidedElsewhere: () => undefined };

function review(changes: Partial<SectionReview>): SectionReview {
  return { ...(REVIEW as SectionReview), ...changes };
}

test("a section proposal from the server is read and drawn beside the published section with every fact it cites", () => {
  const page = parseShape(reviewQueuePageShape, PAGE);
  const item = page.items[0] as SectionItem;
  expect([item.kind, item.section.field, item.section.proposed.length]).toEqual(["SECTIONS", "CHEMISTRY", 2]);
  const markup = renderToStaticMarkup(createElement(QueueItemView, { item, handlers: HANDLERS }));
  expect(markup).toContain('data-testid="section-review-card"');
  expect(markup).toContain("The chemistry section");
  expect(markup).toContain("Alum is printed on the cloth before it goes into the madder bath.");
  expect(markup).toContain("Published now, version 2");
  expect(markup.match(/Madder gives a red colour on cotton\./g)?.length).toBe(3);
  expect(markup).toContain("Section proposal");
  expect(kindTabs(page).map((tab) => tab.label)).toEqual(["All (1)", "Structure (0)", "Sections (1)"]);
});

test("a section with nothing published and a section whose facts moved on are read for what they are", () => {
  const fresh = review({ published: [], publishedVersion: null });
  expect([publishedTitle(fresh), sectionHeadline(fresh)]).toEqual(["Published now", "The chemistry section"]);
  const markup = renderToStaticMarkup(createElement(QueueItemView, { item: { ...(ITEM as SectionItem), section: fresh }, handlers: HANDLERS }));
  expect(markup).toContain(NO_PUBLISHED);
  expect(sectionActions(fresh)).toEqual(["approve", "reject"]);
  expect(sectionWritesLine(fresh)).toContain("keeps the replaced one in the record");
  const stale = review({ stale: "sentence 2 cites a fact this page no longer shows" });
  expect(sectionActions(stale)).toEqual(["reject"]);
  expect(sectionWritesLine(stale)).toBe("The page has moved on, so it can only be rejected: sentence 2 cites a fact this page no longer shows.");
});

test("a section item missing its published side is refused, not read as empty", () => {
  const partial = Object.fromEntries(Object.entries(REVIEW).filter(([key]) => key !== "published"));
  expect(() => parseShape(reviewQueuePageShape, { ...PAGE, items: [{ ...ITEM, section: partial }] })).toThrow();
});

test("a staged section decision is approved or rejected, and a page proposal names its section part and queue", () => {
  expect(STAGED_KIND_ACTIONS.SECTIONS).toEqual(["approve", "reject"]);
  expect(STAGED_KIND_LABELS.SECTIONS).toBe(KIND_NOUNS.SECTIONS);
  expect(KIND_LABELS.SECTIONS).toBe("Sections");
  expect(PART_KINDS.indexOf("section")).toBe(PART_QUEUES.indexOf("SECTIONS"));
});

test("a held page counts its written sections, and a hold from before them still reads", () => {
  const none = { facts: 0, structure: 0, components: 0, layout: 0, pictures: 0, withdrawals: 0, translations: 0 };
  expect(countsLine({ ...none, facts: 1, sections: 2 })).toBe("1 fact and 2 written sections");
  expect(countsLine({ ...none, facts: 1 })).toBe("1 fact");
});
