import { expect, test } from "@playwright/test";

import { CHECK_STATE_LABELS, PICTURE_CHECK_ACTIONS, VERDICT_LABELS, verdictByLine } from "@/lib/pictureCheckView";
import { reviewQueuePageShape, type PictureCheckItem } from "@/lib/reviewQueueContract";
import { KIND_LABELS, KIND_NOUNS } from "@/lib/reviewQueueView";
import { parseShape } from "@/lib/shape";
import { STAGED_KIND_ACTIONS, STAGED_KIND_LABELS } from "@/lib/stagedReviewView";

const MEDIA = {
  id: "00000000-0000-4000-8000-000000000201",
  display: "INLINE",
  provider: "wikimedia_commons",
  pageUrl: "https://commons.wikimedia.org/wiki/File:Ajrakh.jpg",
  imageUrl: "https://upload.wikimedia.org/wikipedia/commons/2/2a/Ajrakh.jpg",
  width: 960,
  height: 640,
  title: "Ajrakh printing in Dhamadka",
  alt: "A printer pressing a carved block on cloth",
  author: "A. Photographer",
  site: "commons.wikimedia.org",
  credit: "A. Photographer, CC BY-SA 4.0",
  licence: "CC BY-SA 4.0",
  licenceUrl: null,
  sourceId: null,
  retrievedAt: "2026-11-20T09:00:00Z"
};

const SHOWS = { verdict: "SHOWS", reason: "A printer pressing a resist block on cotton", by: "Meera", ruling: false, trusted: false, at: "2026-11-24T09:00:00Z" };
const REFUSES = { verdict: "DOES_NOT_SHOW", reason: "A shop's photograph of a finished stole", by: "Arjun", ruling: false, trusted: true, at: "2026-11-24T10:00:00Z" };

const ITEM = {
  id: "00000000-0000-4000-8000-000000000200",
  origin: "AGENT",
  submittedAt: "2026-11-20T09:00:00Z",
  craft: { slug: "Kutch-Ajrakh", name: "Kutch Ajrakh", path: "/crafts/Kutch-Ajrakh" },
  proposer: null,
  kind: "PICTURE_CHECKS",
  check: { media: MEDIA, factId: "00000000-0000-4000-8000-000000000202", fact: "Ajrakh is printed with a resist.", state: "IN_REVIEW", verdicts: [SHOWS, REFUSES] }
};

const PAGE = { schemaVersion: 1, kinds: ["FACTS", "PICTURE_CHECKS"], counts: { FACTS: 0, PICTURE_CHECKS: 1 }, total: 1, items: [ITEM], nextCursor: null };

test("a searched picture whose looks disagree is read with its picture, its fact and every look", () => {
  const page = parseShape(reviewQueuePageShape, PAGE);
  const item = page.items[0] as PictureCheckItem;
  expect([page.kinds, item.kind, item.check.state, item.check.verdicts.map((verdict) => verdict.verdict)]).toEqual([
    ["FACTS", "PICTURE_CHECKS"],
    "PICTURE_CHECKS",
    "IN_REVIEW",
    ["SHOWS", "DOES_NOT_SHOW"]
  ]);
  const unknownWord = { ...ITEM, check: { ...ITEM.check, verdicts: [{ ...SHOWS, verdict: "MAYBE" }] } };
  expect(() => parseShape(reviewQueuePageShape, { ...PAGE, items: [unknownWord] })).toThrow();
});

test("an Admin approves or rejects a picture check, on the page or staged over MCP", () => {
  expect(PICTURE_CHECK_ACTIONS).toEqual(["approve", "reject"]);
  expect(STAGED_KIND_ACTIONS.PICTURE_CHECKS).toEqual(["approve", "reject"]);
  expect([KIND_LABELS.PICTURE_CHECKS, KIND_NOUNS.PICTURE_CHECKS, STAGED_KIND_LABELS.PICTURE_CHECKS]).toEqual([
    "Picture checks",
    "Searched picture beside a fact",
    "Searched picture beside a fact"
  ]);
});

test("each look says what it found, who looked and how far their word goes", () => {
  expect([VERDICT_LABELS.SHOWS, VERDICT_LABELS.DOES_NOT_SHOW]).toEqual(["Shows what the fact says", "Does not show it"]);
  expect(CHECK_STATE_LABELS.IN_REVIEW).toBe("Hidden from this fact until an Admin decides");
  expect(verdictByLine({ ...REFUSES, verdict: "DOES_NOT_SHOW" })).toContain("Arjun, an account that publishes at once");
  expect(verdictByLine({ ...SHOWS, verdict: "SHOWS", by: null, ruling: true })).toContain("A removed account, an Admin's decision");
});
