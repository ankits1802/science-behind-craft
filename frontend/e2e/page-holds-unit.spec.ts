import { expect, test } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { HeldPage } from "@/components/contributions/HeldPage";
import { ConfirmProvider } from "@/components/dialogs/ConfirmDialog";
import {
  countsLine,
  decisionBody,
  decisionPath,
  heldPagePath,
  HOLD_STATE_LABELS,
  isWaiting,
  pageHoldShape,
  partLine,
  type HoldCounts,
  type PageHoldView
} from "@/lib/pageHoldContract";
import { canAccessRoute, ROUTE_GUARDS } from "@/lib/permissions";
import { parseShape, ShapeError } from "@/lib/shape";
import type { User } from "@/lib/types";

const HOLD = "6f1c2a4e-8d3b-4c5a-9e7f-0a1b2c3d4e51";
const SITE = "https://kalavigyan.example";
const NONE: HoldCounts = { facts: 0, structure: 0, components: 0, layout: 0, pictures: 0, withdrawals: 0, translations: 0 };
const WAITING: PageHoldView = {
  schemaVersion: 1,
  id: HOLD,
  subject: { kind: "craft", slug: "Sanganeri-Hand-Block-Printing" },
  pageUrl: `${SITE}/crafts/Sanganeri-Hand-Block-Printing`,
  state: "WAITING",
  clientName: "Claude",
  createdAt: "2026-11-24T09:00:00Z",
  expiresAt: "2026-11-27T09:00:00Z",
  decidedAt: null,
  counts: { ...NONE, facts: 2, components: 1, layout: 1, withdrawals: 1 },
  parts: [
    { part: "fact", index: 0, summary: "CHEMISTRY: Alum fixes the madder red on the cotton." },
    { part: "withdrawal", index: 0, summary: "withdraw sanganeri-hand-block-printing/history/plain-timeline" }
  ],
  previewUrl: `${SITE}/preview/token`,
  result: null,
  message: "Nothing is proposed or shown until you press Confirm. Discard it to propose nothing."
};
const CONFIRMED: PageHoldView = {
  ...WAITING,
  state: "CONFIRMED",
  decidedAt: "2026-11-24T10:00:00Z",
  previewUrl: null,
  result: {
    schemaVersion: 1,
    subject: WAITING.subject,
    pageUrl: WAITING.pageUrl,
    accepted: 1,
    refused: 1,
    parts: [
      { part: "component", index: 0, outcome: "ACCEPTED", status: "PENDING", id: "p1", message: "Stored for review." },
      { part: "layout", index: 0, outcome: "REFUSED", status: null, id: null, message: "The layout of the page is at version 2, not 1." }
    ],
    message: "1 of 2 parts of the bundle were accepted and 1 refused, each with its reason."
  },
  message: "Confirmed: each part went through its own checks."
};

const RESEARCHER: User = { id: "r", email: "r@example.org", name: "R", role: "RESEARCHER", capabilities: ["PROPOSE_KNOWLEDGE"] };
const STUDENT: User = { id: "s", email: "s@example.org", name: "S", role: "STUDENT", capabilities: [] };

test("a held page parses exactly as the backend serves it, waiting or confirmed", () => {
  expect(parseShape(pageHoldShape, WAITING)).toEqual(WAITING);
  const served = { ...CONFIRMED, result: { ...CONFIRMED.result, parts: CONFIRMED.result!.parts.map((part) => ({ ...part, upload: null })) } };
  expect(parseShape(pageHoldShape, served)).toEqual(CONFIRMED);
  expect(isWaiting(WAITING)).toBe(true);
  expect(isWaiting(CONFIRMED)).toBe(false);
});

test("a held page off its contract is refused", () => {
  expect(() => parseShape(pageHoldShape, { ...WAITING, state: "PUBLISHED" })).toThrow(ShapeError);
  expect(() => parseShape(pageHoldShape, { ...WAITING, schemaVersion: 2 })).toThrow(ShapeError);
  expect(() => parseShape(pageHoldShape, { ...WAITING, expiresAt: "in three days" })).toThrow(ShapeError);
  expect(() => parseShape(pageHoldShape, { ...WAITING, counts: { ...WAITING.counts, layout: -1 } })).toThrow(ShapeError);
  expect(() => parseShape(pageHoldShape, { ...WAITING, ownerEmail: "x@example.org" }, "refuse")).toThrow(ShapeError);
});

test("the person decides once, on the hold's own decision path", () => {
  expect(heldPagePath(HOLD)).toBe(`/knowledge/pages/held/${HOLD}`);
  expect(decisionPath(HOLD)).toBe(`/knowledge/pages/held/${HOLD}/decision`);
  expect(decisionBody("CONFIRM")).toEqual({ decision: "CONFIRM" });
  expect(decisionBody("DISCARD")).toEqual({ decision: "DISCARD" });
});

test("the counts line names each kind of part the page holds", () => {
  expect(countsLine(WAITING.counts)).toBe("2 facts, 1 component, a layout and 1 withdrawal");
  expect(countsLine({ ...NONE, structure: 2, translations: 1 })).toBe("2 structure items and 1 translated passage");
  expect(partLine(CONFIRMED.result!.parts[1])).toBe("Refused: layout 1");
  expect(HOLD_STATE_LABELS.EXPIRED).toBe("Expired");
});

test("a waiting page offers confirm and discard, and a confirmed one shows each part's outcome", () => {
  const waiting = renderToStaticMarkup(createElement(ConfirmProvider, null, createElement(HeldPage, { view: WAITING, onDecided: () => undefined })));
  expect(waiting).toContain("Confirm and propose");
  expect(waiting).toContain("Discard");
  expect(waiting).toContain("Open the private preview");
  expect(waiting).toContain("Claude");
  const confirmed = renderToStaticMarkup(createElement(ConfirmProvider, null, createElement(HeldPage, { view: CONFIRMED, onDecided: () => undefined })));
  expect(confirmed).not.toContain("Confirm and propose");
  expect(confirmed).toContain("Accepted: component 1");
  expect(confirmed).toContain("The layout of the page is at version 2, not 1.");
  expect(confirmed).not.toContain("Open the private preview");
});

test("only a Researcher or above opens a held page", () => {
  const gates = Object.fromEntries(ROUTE_GUARDS.map((guard) => [guard.path, guard.gate]));
  expect(gates["/contributions/pages"]).toBe("require(PROPOSE_KNOWLEDGE)");
  const path = `/contributions/pages/${HOLD}`;
  expect([canAccessRoute(RESEARCHER, path), canAccessRoute(STUDENT, path)]).toEqual([true, false]);
});
