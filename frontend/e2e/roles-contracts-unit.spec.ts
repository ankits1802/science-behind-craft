import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { availabilityShape, parseTurnBlock, startedShape } from "@/lib/conversationContract";
import { creditPreview, firstName, profileViewShape } from "@/lib/profileContract";
import { parseShape } from "@/lib/shape";
import { contributionListShape, isOpenItem, reviewEntryShape } from "@/lib/testimonyContract";

const SHARED = join(__dirname, "..", "..", "shared");
const golden = (name: string): unknown => JSON.parse(readFileSync(join(SHARED, name), "utf8"));

test("both profile goldens parse, with only the account's own role part", () => {
  const student = parseShape(profileViewShape, golden("profile.student.golden.json"));
  expect(student.student).toEqual({ ageBand: "14_17", gender: "UNSAID", guardianConsent: "NEEDED" });
  expect(student.artisan).toBeNull();
  const artisan = parseShape(profileViewShape, golden("profile.artisan.golden.json"));
  expect(artisan.student).toBeNull();
  expect(artisan.artisan?.crafts.map((craft) => craft.slug)).toEqual(["kutch-ajrakh", "kutch-bandhani"]);
  expect(artisan.artisan?.credit.preview).toBe("Ismail, Ajrakh, Kachchh, Gujarat");
});

test("the preview of the speaker line follows the credit choice as the server writes it", () => {
  const district = { lgd: 449, name: "Kachchh", state: { lgd: 24, name: "Gujarat" } };
  expect(creditPreview("FIRST_NAME", firstName("Ismail Mohammed Khatri"), "Ajrakh", district)).toBe("Ismail, Ajrakh, Kachchh, Gujarat");
  expect(creditPreview("FULL_NAME", "Ismail Mohammed Khatri", "Ajrakh", district)).toBe("Ismail Mohammed Khatri, Ajrakh, Kachchh, Gujarat");
  expect(creditPreview("CRAFT_AND_DISTRICT", "Ismail", "Ajrakh", district)).toBe("An artisan of Ajrakh, Kachchh, Gujarat");
});

test("the conversation availability and relay start goldens parse", () => {
  const offered = parseShape(availabilityShape, golden("conversation.availability.golden.json"));
  expect(offered.configured).toBe(true);
  expect(offered.crafts).toHaveLength(2);
  const started = parseShape(startedShape, golden("conversation.started-relay.golden.json"));
  expect(started.transport).toBe("RELAY");
  if (started.transport === "RELAY") expect(started.opening.speechPath).toContain(started.conversationId);
});

test("every block of the turn golden parses into a known event", () => {
  const text = readFileSync(join(SHARED, "conversation.turn.golden.sse"), "utf8");
  const events = text.split("\n\n").filter(Boolean).map((block) => parseTurnBlock(block));
  expect(events.every((event) => event !== null)).toBe(true);
  const types = events.map((event) => event?.type);
  expect(types[0]).toBe("status");
  expect(types.at(-1)).toBe("done");
  expect(types).toContain("reply");
});

test("the contribution golden keeps a withdrawn item as a bare tombstone", () => {
  const listed = parseShape(contributionListShape, golden("testimony.contribution.golden.json"));
  expect(listed.counts).toEqual({ pending: 1, approved: 1, rejected: 0, withdrawn: 1 });
  const withdrawn = listed.items.find((item) => item.status === "WITHDRAWN");
  expect(withdrawn && Object.keys(withdrawn).sort()).toEqual(["conversationId", "id", "status", "withdrawnAt"]);
});

test("the review item golden parses as an open item with its context", () => {
  const item = parseShape(reviewEntryShape, golden("testimony.review-item.golden.json"));
  expect(isOpenItem(item)).toBe(true);
  if (isOpenItem(item)) {
    expect(item.speaker.name).toBeNull();
    expect(item.context.audio?.startMs).toBe(2000);
    expect(item.line).toBe("An artisan of Ajrakh Printing, Kachchh, Gujarat");
  }
});
