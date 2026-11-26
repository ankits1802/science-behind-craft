import { apiFetch } from "@/lib/api";
import { INSTANT, UUID } from "@/lib/answerShapes";
import type { MonographDocument } from "@/lib/monographDocument";
import { monographDocumentShape } from "@/lib/monographDocumentShape";
import { boolean, count, list, nullable, object, oneOf, optional, parseShape, positive, text, type Shape } from "@/lib/shape";

export const PAGE_PROPOSALS_PATH = "/review-queue/pages";
export const DRAWN_SIDES = ["BEFORE", "AFTER"] as const;
export const SCOPES = ["PAGE", "CHAPTER", "COMPONENT"] as const;
export const PART_STATES = ["WAITING", "APPROVED", "REJECTED", "CLOSED"] as const;
export const PART_OUTCOMES = ["APPLIED", "REFUSED", "SKIPPED"] as const;
export const CHANGE_MARKS = ["ADDED", "CHANGED", "REMOVED"] as const;
export const CHANGE_KINDS = ["SENTENCE", "COMPONENT", "PICTURE"] as const;
export const PART_KINDS = ["fact", "structure", "picture", "component", "layout"] as const;
export const PART_QUEUES = ["FACTS", "STRUCTURE", "IMAGES", "COMPONENTS", "LAYOUTS"] as const;
export const PAGE_ACTIONS = ["approve", "reject"] as const;

export type DrawnSide = (typeof DRAWN_SIDES)[number];
export type Scope = (typeof SCOPES)[number];
export type PartState = (typeof PART_STATES)[number];
export type ChangeMark = (typeof CHANGE_MARKS)[number];
export type ChangeKind = (typeof CHANGE_KINDS)[number];
export type PageAction = (typeof PAGE_ACTIONS)[number];

export type PageScope = { scope: Scope; chapter?: string | null; label?: string | null };
export type ChangeCount = { added: number; changed: number; removed: number };
export type PageChange = { kind: ChangeKind; change: ChangeMark; ref: string; before: string | null; after: string | null; componentKind?: string; movedFrom?: string };
export type ChapterChanges = { key: string; title: string; sentences: ChangeCount; components: ChangeCount; pictures: ChangeCount; changes: PageChange[] };
export type PartView = { part: (typeof PART_KINDS)[number]; kind: (typeof PART_QUEUES)[number]; id: string; chapter: string | null; label: string | null; title: string; state: PartState };
export type PartOutcome = { part: (typeof PART_KINDS)[number]; kind: (typeof PART_QUEUES)[number]; id: string; title: string; outcome: (typeof PART_OUTCOMES)[number]; message: string };
export type PageDecision = { action: PageAction; scope: Scope; chapter?: string; label?: string; note: string | null; decidedAt: string; outcomes: PartOutcome[] };
export type DrawnPicture = { side: DrawnSide; name: string; caption: string; width: number; height: number; url: string };
export type PageProposalView = {
  schemaVersion: 1;
  id: string;
  subject: { kind: "craft" | "family" | "category"; slug: string };
  subjectName: string;
  pageUrl: string;
  origin: string;
  proposer: { name: string; role: string } | null;
  createdAt: string;
  waiting: number;
  parts: PartView[];
  chapters: ChapterChanges[];
  pictures: DrawnPicture[];
  drawable: DrawnSide[];
  decisions: PageDecision[];
  whole: boolean;
};
export type PageProposalList = { schemaVersion: 1; proposals: PageProposalView[] };
export type PageDrawing = { side: DrawnSide; drawn: boolean; message: string; pictures: DrawnPicture[]; problems: string[] };
export type PageDecisionReply = { schemaVersion: 1; decision: PageDecision; message: string; open: boolean };
export type PageDecisionBody = PageScope & { action: PageAction; note: string | null };

export const pageScopeShape: Shape<PageScope> = object<PageScope>({ scope: oneOf(SCOPES), chapter: optional(nullable(text)), label: optional(nullable(text)) });
const changeCountShape = object<ChangeCount>({ added: count, changed: count, removed: count });
const changeShape = object<PageChange>({
  kind: oneOf(CHANGE_KINDS),
  change: oneOf(CHANGE_MARKS),
  ref: text,
  before: nullable(text),
  after: nullable(text),
  componentKind: optional(text),
  movedFrom: optional(text)
});
const chapterShape = object<ChapterChanges>({ key: text, title: text, sentences: changeCountShape, components: changeCountShape, pictures: changeCountShape, changes: list(changeShape) });
const partShape = object<PartView>({ part: oneOf(PART_KINDS), kind: oneOf(PART_QUEUES), id: UUID, chapter: nullable(text), label: nullable(text), title: text, state: oneOf(PART_STATES) });
const outcomeShape = object<PartOutcome>({ part: oneOf(PART_KINDS), kind: oneOf(PART_QUEUES), id: UUID, title: text, outcome: oneOf(PART_OUTCOMES), message: text });
const decisionShape = object<PageDecision>({
  action: oneOf(PAGE_ACTIONS),
  scope: oneOf(SCOPES),
  chapter: optional(text),
  label: optional(text),
  note: nullable(text),
  decidedAt: INSTANT,
  outcomes: list(outcomeShape)
});
const pictureShape = object<DrawnPicture>({ side: oneOf(DRAWN_SIDES), name: text, caption: text, width: positive, height: positive, url: text });

export const pageProposalShape: Shape<PageProposalView> = object<PageProposalView>({
  schemaVersion: oneOf([1] as const),
  id: UUID,
  subject: object<PageProposalView["subject"]>({ kind: oneOf(["craft", "family", "category"] as const), slug: text }),
  subjectName: text,
  pageUrl: text,
  origin: text,
  proposer: nullable(object<{ name: string; role: string }>({ name: text, role: text })),
  createdAt: INSTANT,
  waiting: count,
  parts: list(partShape),
  chapters: list(chapterShape),
  pictures: list(pictureShape),
  drawable: list(oneOf(DRAWN_SIDES)),
  decisions: list(decisionShape),
  whole: boolean
});
export const pageProposalListShape: Shape<PageProposalList> = object<PageProposalList>({ schemaVersion: oneOf([1] as const), proposals: list(pageProposalShape) });
export const pageDrawingShape: Shape<PageDrawing> = object<PageDrawing>({ side: oneOf(DRAWN_SIDES), drawn: boolean, message: text, pictures: list(pictureShape), problems: list(text) });
export const pageDecisionReplyShape: Shape<PageDecisionReply> = object<PageDecisionReply>({ schemaVersion: oneOf([1] as const), decision: decisionShape, message: text, open: boolean });

const proposalPath = (id: string) => `${PAGE_PROPOSALS_PATH}/${encodeURIComponent(id)}`;

export async function fetchPageProposals(): Promise<PageProposalList> {
  return parseShape(pageProposalListShape, await apiFetch<unknown>(PAGE_PROPOSALS_PATH));
}

export async function fetchPageProposal(id: string): Promise<PageProposalView> {
  return parseShape(pageProposalShape, await apiFetch<unknown>(proposalPath(id)));
}

export async function fetchProposalDocument(id: string, side: DrawnSide): Promise<MonographDocument> {
  return parseShape(monographDocumentShape, await apiFetch<unknown>(`${proposalPath(id)}/documents/${side}`));
}

export async function drawProposalSide(id: string, side: DrawnSide): Promise<PageDrawing> {
  return parseShape(pageDrawingShape, await apiFetch<unknown>(`${proposalPath(id)}/draw`, { method: "POST", body: JSON.stringify({ side }) }));
}

export async function decidePageProposal(id: string, body: PageDecisionBody): Promise<PageDecisionReply> {
  return parseShape(pageDecisionReplyShape, await apiFetch<unknown>(`${proposalPath(id)}/decide`, { method: "POST", body: JSON.stringify(body) }));
}
