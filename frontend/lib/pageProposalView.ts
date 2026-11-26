import type {
  ChangeCount,
  ChangeKind,
  ChangeMark,
  ChapterChanges,
  DrawnPicture,
  DrawnSide,
  PageAction,
  PageDecisionBody,
  PageProposalView,
  PageScope,
  PartState,
  PartView
} from "@/lib/pageProposalContract";
import { KIND_NOUNS } from "@/lib/reviewQueueView";

export const SIDE_TITLES: Record<DrawnSide, string> = { BEFORE: "As it stands", AFTER: "As it will be" };
export const MARK_WORDS: Record<ChangeMark, string> = { ADDED: "Added", CHANGED: "Changed", REMOVED: "Removed" };
export const CHANGE_KIND_WORDS: Record<ChangeKind, string> = { SENTENCE: "Sentence", COMPONENT: "Component", PICTURE: "Picture" };
export const PART_STATE_WORDS: Record<PartState, string> = { WAITING: "Waiting", APPROVED: "Approved", REJECTED: "Rejected", CLOSED: "Closed" };
export const FIRST_SCREEN_WIDTHS = [390, 1440] as const;
export const WHOLE_PAGE: PageScope = { scope: "PAGE", chapter: null, label: null };

export type PicturePair = { key: string; caption: string; before: DrawnPicture | null; after: DrawnPicture | null };

const COUNTED: [keyof Pick<ChapterChanges, "sentences" | "components" | "pictures">, string][] = [
  ["sentences", "Sentences"],
  ["components", "Components"],
  ["pictures", "Pictures"]
];

export function countWords(numbers: ChangeCount): string {
  const said: string[] = [];
  if (numbers.added) said.push(`${numbers.added} added`);
  if (numbers.changed) said.push(`${numbers.changed} changed`);
  if (numbers.removed) said.push(`${numbers.removed} removed`);
  return said.join(", ");
}

export function changedCount(chapter: ChapterChanges): number {
  return COUNTED.reduce((total, [field]) => total + chapter[field].added + chapter[field].changed + chapter[field].removed, 0);
}

export function chapterCounts(chapter: ChapterChanges): string {
  return COUNTED.map(([field, word]) => [word, countWords(chapter[field])] as const)
    .filter(([, said]) => said)
    .map(([word, said]) => `${word}: ${said}`)
    .join(" · ");
}

export function waitingLine(view: PageProposalView): string {
  const total = view.parts.length;
  return `${view.waiting} of ${total} ${total === 1 ? "part waits" : "parts wait"} for a decision`;
}

export function chapterScope(key: string): PageScope {
  return { scope: "CHAPTER", chapter: key, label: null };
}

export function componentScope(label: string): PageScope {
  return { scope: "COMPONENT", chapter: null, label };
}

export function decisionBody(scope: PageScope, action: PageAction, words: string): PageDecisionBody {
  const note = words.trim();
  return { scope: scope.scope, chapter: scope.chapter ?? null, label: scope.label ?? null, action, note: note || null };
}

export function partsIn(view: PageProposalView, scope: PageScope): PartView[] {
  if (scope.scope === "CHAPTER") return view.parts.filter((part) => part.chapter === scope.chapter);
  if (scope.scope === "COMPONENT") return view.parts.filter((part) => part.label === scope.label);
  return view.parts;
}

export function decides(view: PageProposalView, scope: PageScope): boolean {
  return partsIn(view, scope).some((part) => part.state === "WAITING");
}

export function partLine(part: PartView): string {
  return `${KIND_NOUNS[part.kind]} · ${PART_STATE_WORDS[part.state]}`;
}

function picture(view: PageProposalView, side: DrawnSide, name: string): DrawnPicture | null {
  return view.pictures.find((found) => found.side === side && found.name === name) ?? null;
}

export function firstScreens(view: PageProposalView): PicturePair[] {
  return FIRST_SCREEN_WIDTHS.map((width) => {
    const key = `first-screen-${width}`;
    return { key, caption: `The first screen at ${width} px`, before: picture(view, "BEFORE", key), after: picture(view, "AFTER", key) };
  });
}

export function chapterPictures(view: PageProposalView, chapter: string): PicturePair | null {
  const key = `chapter-${chapter}`;
  const pair = { key, caption: "The chapter at 1440 px", before: picture(view, "BEFORE", key), after: picture(view, "AFTER", key) };
  return pair.before || pair.after ? pair : null;
}

export function emptyWords(view: PageProposalView): Record<DrawnSide, string> {
  return {
    BEFORE: view.drawable.includes("BEFORE") ? "Not drawn yet: Draw it draws the page as it stands." : "A new page: nothing stood here before it.",
    AFTER: view.drawable.includes("AFTER") ? "Not drawn yet: Draw it draws the page as it will be." : "Proposed without a preview, so only its parts are listed."
  };
}

export function sidesToDraw(view: PageProposalView): DrawnSide[] {
  return view.drawable.filter((side) => !view.pictures.some((found) => found.side === side));
}

export function drawnComponents(chapter: ChapterChanges): string[] {
  return chapter.changes.filter((change) => change.kind !== "SENTENCE").map((change) => change.ref);
}

export function withProposal(list: readonly PageProposalView[], updated: PageProposalView): PageProposalView[] {
  if (!updated.waiting) return list.filter((view) => view.id !== updated.id);
  return list.map((view) => (view.id === updated.id ? { ...updated, chapters: view.chapters } : view));
}
