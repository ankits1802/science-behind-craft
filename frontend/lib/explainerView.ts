import type { Discipline, ExplainerBlock, ExplainerSentence, LadderStage, TermSpan, WorkingSectionState } from "@/lib/explainerContract";
import type { SectionState, SectionView } from "@/lib/explainerState";
import { TRAIL_GROUPS, TRAIL_STAGES, type TrailEntry } from "@/lib/explainerStream";
import { byCount, formatDate } from "@/lib/format";
import type { AnswerReaction, AnswerSection, Citation } from "@/lib/types";

export type UnderstoodPart = "craft" | "depth" | "language";
export type TrailGroup = (typeof TRAIL_GROUPS)[number];
export type TrailStage = (typeof TRAIL_STAGES)[number];
export type TrailCount = { group: TrailGroup; count: number; noun: string };
export type TextRange = { from: number; to: number };
export type TextPart = { text: string; marked: boolean };
export type TextSegment = { text: string; term: TermSpan | null; parts: TextPart[] };

export const DISCIPLINE_LABEL: Record<Discipline, string> = {
  OVERVIEW: "Overview",
  PROCESS: "Process",
  CHEMISTRY: "Chemistry",
  PHYSICS: "Physics",
  MATERIALS: "Materials",
  GEOGRAPHY: "Geography and water",
  GEOLOGY: "Geology and soil",
  CLIMATE: "Climate",
  ECOLOGY: "Ecology",
  BOTANY: "Botany",
  HISTORY: "History",
  ECONOMICS: "Economics",
  DESIGN: "Design",
  HEALTH: "Health"
};

export const WORKING_STATE_LABEL: Record<WorkingSectionState, string> = {
  RESEARCHING: "Researching",
  WRITING: "Writing",
  CHECKING: "Checking"
};

export function sectionAnchor(id: string): string {
  return `section-${id}`;
}

export function workingLabel(state: SectionState, streaming: boolean): string | null {
  if (!streaming || state === "READY" || state === "EMPTY") return null;
  return WORKING_STATE_LABEL[state];
}

export const TRAIL_STAGE_LABEL: Record<TrailStage, string> = { FOUND: "Found", READ: "Read", QUOTED: "Quoted" };

const TRAIL_NOUNS: Record<TrailGroup, readonly [string, string]> = {
  PAPERS: ["paper", "papers"],
  ENCYCLOPAEDIA: ["encyclopaedia article", "encyclopaedia articles"],
  DATASETS: ["dataset", "datasets"],
  WEB: ["web page", "web pages"],
  STORED: ["stored finding", "stored findings"]
};

export function stageCitations(stage: LadderStage): Citation[] {
  return [
    ...stage.sentences.flatMap((sentence) => sentence.citations),
    ...stage.materials.flatMap((material) => material.citations),
    ...stage.conditions.flatMap((condition) => condition.citations)
  ];
}

export function blockCitations(block: ExplainerBlock): Citation[] {
  if (block.kind === "prose") return block.sentences.flatMap((sentence) => sentence.citations);
  if (block.kind === "process_ladder") return block.stages.flatMap(stageCitations);
  return [];
}

export function explainerSourceNumbers(
  sections: readonly SectionView[],
  openQuestions: readonly AnswerSection[] = [],
  reactions: readonly AnswerReaction[] = []
): Map<string, number> {
  const numbers = new Map<string, number>();
  const take = (citations: readonly Citation[]) => {
    for (const citation of citations) if (!numbers.has(citation.sourceId)) numbers.set(citation.sourceId, numbers.size + 1);
  };
  for (const section of sections) for (const block of section.blocks) take(blockCitations(block));
  for (const section of openQuestions) for (const sentence of section.sentences) take(sentence.citations);
  for (const reaction of reactions) take(reaction.citations);
  return numbers;
}

export function trailCounts(trail: readonly TrailEntry[]): TrailCount[] {
  return TRAIL_GROUPS.flatMap((group) => {
    const count = trail.filter((entry) => entry.group === group).length;
    return count > 0 ? [{ group, count, noun: byCount(count, ...TRAIL_NOUNS[group]) }] : [];
  });
}

export function shownSections(sections: readonly SectionView[], streaming: boolean): SectionView[] {
  return sections.filter((section) => {
    if (section.blocks.length > 0 || section.state === "EMPTY") return true;
    return streaming && section.state !== "READY";
  });
}

export function termQuestion(label: string, craftName: string | null): string {
  return craftName ? `What is ${label} in ${craftName}?` : `What is ${label}?`;
}

export function reusedLabel(storedAt: string): string {
  return `From earlier research · ${formatDate(storedAt)}`;
}

export function showsEarlierResearch(sections: readonly SectionView[]): boolean {
  return sections.some((section) => section.blocks.some((block) => block.reuse !== null));
}

export function ladderReach(progress: number, count: number, reduce: boolean): number {
  if (count <= 0) return 0;
  if (reduce || count === 1) return count;
  const clamped = Math.min(1, Math.max(0, Number.isFinite(progress) ? progress : 0));
  return Math.floor(clamped * (count - 1) + 1e-9) + 1;
}

type TermRange = TextRange & { term: TermSpan };

function termRanges(text: string, terms: readonly TermSpan[]): TermRange[] {
  const found = terms
    .map((term) => ({ from: term.text ? text.indexOf(term.text) : -1, term }))
    .filter((range) => range.from >= 0)
    .map((range) => ({ from: range.from, to: range.from + range.term.text.length, term: range.term }))
    .sort((a, b) => a.from - b.from);
  const kept: TermRange[] = [];
  for (const range of found) {
    const last = kept.at(-1);
    if (!last || range.from >= last.to) kept.push(range);
  }
  return kept;
}

function markedParts(text: string, offset: number, mark: TextRange | null): TextPart[] {
  if (!mark || mark.to <= offset || mark.from >= offset + text.length) return [{ text, marked: false }];
  const from = Math.max(mark.from - offset, 0);
  const to = Math.min(mark.to - offset, text.length);
  const parts = [
    { text: text.slice(0, from), marked: false },
    { text: text.slice(from, to), marked: true },
    { text: text.slice(to), marked: false }
  ];
  return parts.filter((part) => part.text !== "");
}

export function sentenceSegments(text: string, terms: readonly TermSpan[], mark: TextRange | null = null): TextSegment[] {
  const segments: TextSegment[] = [];
  let at = 0;
  const cut = (to: number, term: TermSpan | null) => {
    if (to > at) segments.push({ text: text.slice(at, to), term, parts: markedParts(text.slice(at, to), at, mark) });
    at = to;
  };
  for (const range of termRanges(text, terms)) {
    cut(range.from, null);
    cut(range.to, range.term);
  }
  cut(text.length, null);
  return segments;
}

export function hasTranslatedText(sections: readonly SectionView[]): boolean {
  return sections.some(
    (section) =>
      section.original !== undefined ||
      section.blocks.some((block) => blockSentences(block).some((sentence) => sentence.translated === true))
  );
}

export function blockSentences(block: ExplainerBlock): ExplainerSentence[] {
  if (block.kind === "prose") return block.sentences;
  if (block.kind === "process_ladder") return block.stages.flatMap((stage) => stage.sentences);
  return [];
}
