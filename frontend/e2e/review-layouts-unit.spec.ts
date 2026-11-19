import { expect, test } from "@playwright/test";

import { CHANGES_SHOWN, changeLine, layoutActions, placeLine, subjectLine, versionLine } from "@/lib/layoutReviewView";
import { reviewQueuePageShape, type LayoutItem, type LayoutReview } from "@/lib/reviewQueueContract";
import { KIND_LABELS, KIND_NOUNS, kindTabs } from "@/lib/reviewQueueView";
import { parseShape } from "@/lib/shape";

const HERO = { ref: "kutch-ajrakh/pictures/i01", chapter: "glance", order: 1, role: "HERO", crop: { x: 0.1, y: 0, width: 0.8, height: 1 }, size: "BLEED", caption: null };
const PLATE = { ref: "kutch-ajrakh/pictures/i02", chapter: "made", order: 2, role: "PLATE", crop: null, size: null, caption: null };
const MOVED = { ref: "kutch-ajrakh/pictures/i02", chapter: "chem", order: 1, role: "FIGURE", caption: "The second wash" };

const REVIEW = {
  subject: { kind: "craft", slug: "Kutch-Ajrakh" },
  subjectName: "Kutch Ajrakh",
  pageUrl: "/crafts/Kutch-Ajrakh",
  baseVersion: 3,
  currentVersion: 3,
  stale: false,
  note: "Lead with the resist print.",
  entryCount: 2,
  changes: [
    { ref: HERO.ref, change: "ADDED", before: null, after: HERO },
    { ref: PLATE.ref, change: "CHANGED", before: PLATE, after: MOVED }
  ]
};

const ITEM = {
  id: "00000000-0000-4000-8000-000000000009",
  origin: "AGENT",
  submittedAt: "2026-11-20T09:00:00Z",
  craft: { slug: "Kutch-Ajrakh", name: "Kutch Ajrakh", path: "/crafts/Kutch-Ajrakh" },
  proposer: null,
  kind: "LAYOUTS",
  layout: REVIEW
};

const PAGE = {
  schemaVersion: 1,
  kinds: ["FACTS", "TESTIMONY", "IMAGES", "COMPONENTS", "LAYOUTS"],
  counts: { FACTS: 0, TESTIMONY: 0, IMAGES: 0, COMPONENTS: 0, LAYOUTS: 1 },
  total: 1,
  items: [ITEM],
  nextCursor: null
};

function review(changes: Partial<LayoutReview>): LayoutReview {
  return { ...(REVIEW as LayoutReview), ...changes };
}

test("a layout proposal from the server is read with its changes, and an unknown change is refused", () => {
  const page = parseShape(reviewQueuePageShape, PAGE);
  const item = page.items[0] as LayoutItem;
  expect([item.kind, item.layout.entryCount, item.layout.changes.map((change) => change.change)]).toEqual(["LAYOUTS", 2, ["ADDED", "CHANGED"]]);
  expect(item.layout.changes[1].after).toEqual(MOVED);
  const wrong = { ...ITEM, layout: { ...REVIEW, changes: [{ ref: "x", change: "SWAPPED", before: null, after: null }] } };
  expect(() => parseShape(reviewQueuePageShape, { ...PAGE, items: [wrong] })).toThrow();
});

test("the layouts tab carries its count and its own names", () => {
  expect(kindTabs(parseShape(reviewQueuePageShape, PAGE)).at(-1)?.label).toBe("Layouts (1)");
  expect([KIND_LABELS.LAYOUTS, KIND_NOUNS.LAYOUTS]).toEqual(["Layouts", "Layout proposal"]);
});

test("a proposal built on an older version can only be rejected", () => {
  expect(layoutActions(review({}))).toEqual(["approve", "reject"]);
  expect(layoutActions(review({ stale: true, currentVersion: 4 }))).toEqual(["reject"]);
});

test("each change says where the entry sat and where it goes", () => {
  expect(placeLine(HERO)).toBe("Hero in glance, place 1, bleed, cropped");
  expect(changeLine(REVIEW.changes[0] as LayoutReview["changes"][number])).toBe("Placed: Hero in glance, place 1, bleed, cropped");
  expect(changeLine(REVIEW.changes[1] as LayoutReview["changes"][number])).toBe(
    "Moved from Plate in made, place 2 to Figure in chem, place 1, caption “The second wash”"
  );
  expect(changeLine({ ref: PLATE.ref, change: "REMOVED", before: PLATE, after: null })).toBe("Taken out: was Plate in made, place 2");
});

test("the version line says what approving writes, or why it cannot", () => {
  expect(versionLine(review({}))).toBe("Built on version 3, the page's current layout; approving writes version 4.");
  expect(versionLine(review({ baseVersion: 0, currentVersion: 0 }))).toBe("The page has no layout yet; approving writes its first version.");
  expect(versionLine(review({ stale: true, currentVersion: 5 }))).toBe(
    "Built on version 3, but the page is at version 5 now, so it can only be rejected."
  );
  expect(subjectLine(review({ entryCount: 1 }))).toBe("Craft page · 1 entry");
  expect(subjectLine(review({ subject: { kind: "category", slug: "textiles" }, entryCount: 14 }))).toBe("Category page · 14 entries");
  expect(CHANGES_SHOWN).toBe(12);
});
