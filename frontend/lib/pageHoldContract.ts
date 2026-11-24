import { apiFetch } from "@/lib/api";
import { INSTANT, UUID } from "@/lib/answerShapes";
import { countNoun, listText } from "@/lib/format";
import { count, integer, list, nullable, object, oneOf, optional, parseShape, text, type Shape } from "@/lib/shape";
import { partReportShape, type PartReport } from "@/lib/translationContract";

export const HELD_PAGES_PATH = "/knowledge/pages/held";
export const HOLD_STATES = ["WAITING", "CONFIRMED", "DISCARDED", "EXPIRED"] as const;
export const HOLD_DECISIONS = ["CONFIRM", "DISCARD"] as const;
export const HOLD_SUBJECT_KINDS = ["craft", "family", "category"] as const;

export type HoldState = (typeof HOLD_STATES)[number];
export type HoldDecision = (typeof HOLD_DECISIONS)[number];
export type HoldSubject = { kind: (typeof HOLD_SUBJECT_KINDS)[number]; slug: string };
export type HoldCounts = { facts: number; structure: number; components: number; layout: number; pictures: number; withdrawals: number; translations: number };
export type HeldPart = { part: string; index: number; summary: string };
export type PageHeld = { id: string; confirmUrl: string; expiresAt: string };
export type PageProposalResult = {
  schemaVersion: 1;
  subject: HoldSubject;
  pageUrl: string;
  accepted: number;
  refused: number;
  parts: PartReport[];
  message: string;
  held?: PageHeld;
};
export type PageHoldView = {
  schemaVersion: 1;
  id: string;
  subject: HoldSubject;
  pageUrl: string;
  state: HoldState;
  clientName: string | null;
  createdAt: string;
  expiresAt: string;
  decidedAt: string | null;
  counts: HoldCounts;
  parts: HeldPart[];
  previewUrl: string | null;
  result: PageProposalResult | null;
  message: string;
};

export const HOLD_STATE_LABELS: Record<HoldState, string> = {
  WAITING: "Waiting for your confirmation",
  CONFIRMED: "Confirmed and proposed",
  DISCARDED: "Discarded",
  EXPIRED: "Expired"
};

const subjectShape: Shape<HoldSubject> = object<HoldSubject>({ kind: oneOf(HOLD_SUBJECT_KINDS), slug: text });

const countsShape: Shape<HoldCounts> = object<HoldCounts>({
  facts: count,
  structure: count,
  components: count,
  layout: count,
  pictures: count,
  withdrawals: count,
  translations: count
});

const resultShape: Shape<PageProposalResult> = object<PageProposalResult>({
  schemaVersion: oneOf([1] as const),
  subject: subjectShape,
  pageUrl: text,
  accepted: count,
  refused: count,
  parts: list(partReportShape),
  message: text,
  held: optional(object<PageHeld>({ id: UUID, confirmUrl: text, expiresAt: INSTANT }))
});

export const pageHoldShape: Shape<PageHoldView> = object<PageHoldView>({
  schemaVersion: oneOf([1] as const),
  id: UUID,
  subject: subjectShape,
  pageUrl: text,
  state: oneOf(HOLD_STATES),
  clientName: nullable(text),
  createdAt: INSTANT,
  expiresAt: INSTANT,
  decidedAt: nullable(INSTANT),
  counts: countsShape,
  parts: list(object<HeldPart>({ part: text, index: integer, summary: text })),
  previewUrl: nullable(text),
  result: nullable(resultShape),
  message: text
});

export function heldPagePath(id: string): string {
  return `${HELD_PAGES_PATH}/${encodeURIComponent(id)}`;
}

export function decisionPath(id: string): string {
  return `${heldPagePath(id)}/decision`;
}

export function decisionBody(decision: HoldDecision): { decision: HoldDecision } {
  return { decision };
}

export function countsLine(counts: HoldCounts): string {
  const named = [
    counts.facts ? countNoun(counts.facts, "fact") : "",
    counts.structure ? countNoun(counts.structure, "structure item") : "",
    counts.components ? countNoun(counts.components, "component") : "",
    counts.layout ? "a layout" : "",
    counts.pictures ? countNoun(counts.pictures, "picture") : "",
    counts.withdrawals ? countNoun(counts.withdrawals, "withdrawal") : "",
    counts.translations ? countNoun(counts.translations, "translated passage") : ""
  ].filter(Boolean);
  return listText(named);
}

const OUTCOME_LABELS: Record<PartReport["outcome"], string> = {
  ACCEPTED: "Accepted",
  REFUSED: "Refused",
  SHOWN: "Shown",
  LISTED: "Listed"
};

export function partLine(part: PartReport): string {
  return `${OUTCOME_LABELS[part.outcome]}: ${part.part} ${part.index + 1}`;
}

export function isWaiting(view: PageHoldView): boolean {
  return view.state === "WAITING";
}

export async function fetchHeldPage(id: string): Promise<PageHoldView> {
  return parseShape(pageHoldShape, await apiFetch<unknown>(heldPagePath(id)));
}

export async function decideHeldPage(id: string, decision: HoldDecision): Promise<PageHoldView> {
  const body = await apiFetch<unknown>(decisionPath(id), { method: "POST", body: JSON.stringify(decisionBody(decision)) });
  return parseShape(pageHoldShape, body);
}
