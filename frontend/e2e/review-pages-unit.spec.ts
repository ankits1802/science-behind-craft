import { expect, test } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { ChapterChangeList } from "@/components/review/ChapterChangeList";
import { PageShots } from "@/components/review/PageShots";
import type { ProposalDocuments } from "@/components/review/useProposalDocuments";
import { pageProposalListShape, pageProposalShape, type PageProposalView } from "@/lib/pageProposalContract";
import { chapterCounts, chapterScope, componentScope, decides, decisionBody, partsIn, sidesToDraw, waitingLine, withProposal, WHOLE_PAGE } from "@/lib/pageProposalView";
import { parseShape } from "@/lib/shape";
import { parseStagedBatch } from "@/lib/stagedReviewContract";

const ID = "00000000-0000-4000-8000-000000000301";
const FACT = "00000000-0000-4000-8000-000000000302";
const TABLE = "00000000-0000-4000-8000-000000000303";
const LAYOUT = "00000000-0000-4000-8000-000000000304";
const LABEL = "sanganeri-hand-block-printing/chemistry/two-mordants-one-bath";
const BEFORE_TEXT = "Alum fixes the red where the block printed it.";
const AFTER_TEXT = "Alum fixes the red, and iron turns the same bath black, where each block printed.";
const none = { added: 0, changed: 0, removed: 0 };

function picture(side: "BEFORE" | "AFTER", name: string) {
  return { side, name, caption: `${name} as drawn`, width: 390, height: 844, url: `/api/review-queue/pages/${ID}/pictures/${side}/${name}` };
}

const PROPOSAL = {
  schemaVersion: 1,
  id: ID,
  subject: { kind: "craft", slug: "Sanganeri-Hand-Block-Printing" },
  subjectName: "Sanganeri Hand Block Printing",
  pageUrl: "https://kalavigyan.example/crafts/Sanganeri-Hand-Block-Printing",
  origin: "AGENT",
  proposer: { name: "Meera Contributor", role: "RESEARCHER" },
  createdAt: "2026-11-26T09:00:00Z",
  waiting: 2,
  parts: [
    { part: "fact", kind: "FACTS", id: FACT, chapter: "chem", label: null, title: AFTER_TEXT, state: "WAITING" },
    { part: "component", kind: "COMPONENTS", id: TABLE, chapter: "chem", label: LABEL, title: "Black and red from one dye bath", state: "APPROVED" },
    { part: "layout", kind: "LAYOUTS", id: LAYOUT, chapter: null, label: null, title: "The page's layout", state: "WAITING" }
  ],
  chapters: [
    {
      key: "chem",
      title: "The chemistry",
      sentences: { added: 0, changed: 1, removed: 0 },
      components: { added: 1, changed: 0, removed: 0 },
      pictures: none,
      changes: [
        { kind: "COMPONENT", change: "ADDED", ref: LABEL, before: null, after: "Black and red from one dye bath", componentKind: "reaction_player" },
        { kind: "SENTENCE", change: "CHANGED", ref: "chemistry-ab12", before: BEFORE_TEXT, after: AFTER_TEXT }
      ]
    }
  ],
  pictures: [picture("BEFORE", "first-screen-390"), picture("AFTER", "first-screen-390"), picture("BEFORE", "chapter-chem"), picture("AFTER", "chapter-chem")],
  drawable: ["BEFORE", "AFTER"],
  decisions: [],
  whole: true
};

const DOCS: ProposalDocuments = { documents: {}, busy: false, problem: null, load: async () => undefined };

function view(changes: Partial<PageProposalView> = {}): PageProposalView {
  return { ...parseShape(pageProposalShape, PROPOSAL), ...changes };
}

test("a proposal with a change is read with both versions, and a mark the web does not know is refused", () => {
  const read = view();
  expect(read.chapters[0].changes.map((change) => [change.kind, change.change])).toEqual([
    ["COMPONENT", "ADDED"],
    ["SENTENCE", "CHANGED"]
  ]);
  expect(read.pictures.map((shot) => shot.side)).toEqual(["BEFORE", "AFTER", "BEFORE", "AFTER"]);
  const wrong = { ...PROPOSAL, chapters: [{ ...PROPOSAL.chapters[0], changes: [{ ...PROPOSAL.chapters[0].changes[1], change: "MOVED" }] }] };
  expect(() => parseShape(pageProposalShape, wrong)).toThrow();
  expect(parseShape(pageProposalListShape, { schemaVersion: 1, proposals: [PROPOSAL] }).proposals).toHaveLength(1);
});

test("the page draws both versions side by side and marks what changed in each chapter", () => {
  const shots = renderToStaticMarkup(createElement(PageShots, { view: view(), onDraw: async () => null }));
  expect(shots).toContain(`src="/api/review-queue/pages/${ID}/pictures/BEFORE/first-screen-390"`);
  expect(shots).toContain(`src="/api/review-queue/pages/${ID}/pictures/AFTER/first-screen-390"`);
  expect(shots).toContain('loading="lazy"');
  expect(shots).toContain("As it stands");
  expect(shots).toContain("As it will be");
  expect(shots).not.toContain("Draw it");
  const chapters = renderToStaticMarkup(createElement(ChapterChangeList, { view: view(), docs: DOCS, onDecide: async () => null }));
  expect(chapters).toContain('data-change="CHANGED"');
  expect(chapters).toContain('data-change="ADDED"');
  expect(chapters).toContain("Changed · Sentence");
  expect(chapters).toContain(BEFORE_TEXT);
  expect(chapters).toContain(AFTER_TEXT);
  expect(chapters).toContain(`pictures/AFTER/chapter-chem`);
  expect(chapters).toContain("Decide the chapter The chemistry");
  expect(chapterCounts(view().chapters[0])).toBe("Sentences: 1 changed · Components: 1 added");
});

test("a proposal without stored pictures still opens, and offers to draw each version it keeps", () => {
  const bare = view({ pictures: [] });
  expect(sidesToDraw(bare)).toEqual(["BEFORE", "AFTER"]);
  const markup = renderToStaticMarkup(createElement(PageShots, { view: bare, onDraw: async () => null }));
  expect(markup).toContain("Draw it");
  expect(markup).toContain("Not drawn yet: Draw it draws the page as it will be.");
  const fresh = renderToStaticMarkup(createElement(PageShots, { view: view({ pictures: [], drawable: ["AFTER"] }), onDraw: async () => null }));
  expect(fresh).toContain("A new page: nothing stood here before it.");
  expect(sidesToDraw(view())).toEqual([]);
});

test("a chapter's decision reaches only that chapter's parts, and a decided part is not offered again", () => {
  const read = view();
  expect(partsIn(read, chapterScope("chem")).map((part) => part.id)).toEqual([FACT, TABLE]);
  expect(partsIn(read, componentScope(LABEL)).map((part) => part.id)).toEqual([TABLE]);
  expect(partsIn(read, WHOLE_PAGE)).toHaveLength(3);
  expect([decides(read, chapterScope("chem")), decides(read, componentScope(LABEL)), decides(read, chapterScope("why"))]).toEqual([true, false, false]);
  expect(decisionBody(chapterScope("chem"), "approve", "  ")).toEqual({ scope: "CHAPTER", chapter: "chem", label: null, action: "approve", note: null });
  expect(decisionBody(WHOLE_PAGE, "reject", " The red needs its source. ")).toEqual({ scope: "PAGE", chapter: null, label: null, action: "reject", note: "The red needs its source." });
  expect(waitingLine(read)).toBe("2 of 3 parts wait for a decision");
});

test("a decided page leaves the list once nothing in it waits", () => {
  const read = view();
  expect(withProposal([read], { ...read, waiting: 1 })[0].waiting).toBe(1);
  expect(withProposal([read], { ...read, waiting: 0 })).toEqual([]);
});

test("a page decision an Admin's AI staged reads with its scope, for a person to confirm", () => {
  const batch = parseStagedBatch({
    id: "00000000-0000-4000-8000-000000000401",
    status: "OPEN",
    clientName: "Claude",
    proposedBy: "Admin Reviewer",
    createdAt: "2026-11-26T09:00:00Z",
    expiresAt: "2026-11-29T09:00:00Z",
    decidedBy: null,
    decidedAt: null,
    refresh: null,
    items: [
      {
        id: "00000000-0000-4000-8000-000000000402",
        position: 0,
        label: "Page proposal for Sanganeri Hand Block Printing: the chapter chem",
        decision: { kind: "PAGES", id: ID, action: "approve", reason: "Every chemistry sentence is quoted.", craft: null, family: null, source: null, page: { scope: "CHAPTER", chapter: "chem", label: null } },
        state: "STAGED",
        applied: null,
        outcome: null
      }
    ]
  });
  expect(batch.items[0].decision.page).toEqual({ scope: "CHAPTER", chapter: "chem", label: null });
});
