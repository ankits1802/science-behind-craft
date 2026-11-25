import type { MonographDocument } from "@/lib/monographDocument";
import { pieceRefs } from "@/lib/monographNotes";
import { arrangedLabels, layoutSizes, setInProse } from "@/lib/monographPlacement";
import { citedSourceKeys, nodesText } from "@/lib/monographRender";
import { componentUnits, specStrings, withAsides, type ChapterBlock, type ChapterPlan, type PagePlan, type Passage, type PassageAside, type PassagePiece } from "@/lib/monographRenderLayout";

const WORD = /[\p{L}][\p{L}-]{3,}/gu;
const SOURCE_WEIGHT = 2;
const SHARED_FLOOR = 0.5;
const COMMON = new Set([
  "about", "after", "also", "among", "another", "because", "been", "before", "being", "between", "both", "but", "called", "cloth", "could", "craft", "crafts", "does", "each", "either",
  "from", "have", "here", "into", "itself", "made", "make", "many", "more", "most", "much", "only", "other", "over", "same", "some", "such", "than", "that", "their", "them", "then",
  "there", "these", "they", "this", "those", "through", "under", "until", "used", "uses", "using", "very", "were", "what", "when", "where", "which", "while", "with", "within", "would", "your"
]);

export type Figure = { label: string; words: ReadonlySet<string>; sources: ReadonlySet<string> };
export type Paragraph = { block: number; piece: number; words: ReadonlySet<string>; sources: ReadonlySet<string> };

export function words(text: string): Set<string> {
  return new Set([...text.toLowerCase().matchAll(WORD)].map((found) => found[0].replace(/-+$/, "")).filter((word) => !COMMON.has(word)));
}

function figure(document: MonographDocument, label: string): Figure {
  const component = document.content.components.find((found) => found.label === label);
  const units = componentUnits(document, label).map((ref) => document.content.units[ref]).filter(Boolean);
  const held = Object.hasOwn(document.specs, label) ? specStrings(document.specs[label]) : [];
  const text = [component?.title ?? "", component?.description ?? "", ...units.map((unit) => nodesText(unit.nodes)), ...held].join(" ");
  return { label, words: words(text), sources: new Set(units.flatMap((unit) => citedSourceKeys(unit.nodes))) };
}

function paragraphs(document: MonographDocument, blocks: readonly ChapterBlock[]): Paragraph[] {
  const units = document.content.units;
  return blocks.flatMap((block, at) =>
    block.kind !== "passage"
      ? []
      : block.pieces.flatMap((piece, index) => {
          if (piece.kind !== "paragraph") return [];
          const nodes = piece.refs.flatMap((ref) => units[ref]?.nodes ?? []);
          return [{ block: at, piece: index, words: words(nodesText(nodes)), sources: new Set(citedSourceKeys(nodes)) }];
        })
  );
}

export function rarity(found: readonly Paragraph[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const paragraph of found) for (const word of paragraph.words) counts.set(word, (counts.get(word) ?? 0) + 1);
  return new Map([...counts].map(([word, count]) => [word, Math.log((found.length + 1) / count)]));
}

export function nearness(item: Figure, paragraph: Paragraph, weights: ReadonlyMap<string, number>): number {
  let score = 0;
  for (const word of item.words) if (paragraph.words.has(word)) score += weights.get(word) ?? 0;
  for (const source of item.sources) if (paragraph.sources.has(source)) score += SOURCE_WEIGHT;
  return score;
}

export function anchors(items: readonly Figure[], found: readonly Paragraph[]): Map<string, Paragraph> {
  const weights = rarity(found);
  const taken = new Set<Paragraph>();
  const chosen = new Map<string, Paragraph>();
  for (const item of items) {
    const ranked = found.map((paragraph) => ({ paragraph, score: nearness(item, paragraph, weights) })).filter((entry) => entry.score > 0).sort((a, b) => b.score - a.score);
    if (!ranked.length) continue;
    const free = ranked.find((entry) => !taken.has(entry.paragraph) && entry.score >= ranked[0].score * SHARED_FLOOR);
    const pick = (free ?? ranked[0]).paragraph;
    taken.add(pick);
    chosen.set(item.label, pick);
  }
  return chosen;
}

function trailing(blocks: readonly ChapterBlock[]): string[] {
  const out: string[] = [];
  for (let at = blocks.length - 1; at >= 0; at -= 1) {
    const block = blocks[at];
    if (block.kind !== "component") break;
    out.unshift(block.label);
  }
  return out;
}

export type NearPlacing = { arranged: ReadonlySet<string>; loose: ReadonlySet<string>; beside: (label: string) => boolean };

const NO_ASIDES: readonly PassageAside[] = [];

export function interleaved(block: Passage, anchored: ReadonlyMap<number, readonly string[]>, beside: (label: string) => boolean = () => false): ChapterBlock[] {
  const out: ChapterBlock[] = [];
  const asides = [...(block.asides ?? NO_ASIDES)];
  let pieces: PassagePiece[] = [];
  const flush = () => {
    if (!pieces.length) return;
    const refs = new Set(pieces.flatMap(pieceRefs));
    const shown: Passage = out.some((found) => found.kind === "passage") ? { kind: "passage", head: false, pieces, notes: [] } : { kind: "passage", head: block.head, pieces, notes: block.notes };
    out.push(withAsides(shown, asides.filter((aside) => refs.has(aside.after))));
    pieces = [];
  };
  block.pieces.forEach((piece, index) => {
    pieces.push(piece);
    const labels = anchored.get(index) ?? [];
    const refs = pieceRefs(piece);
    const after = refs[refs.length - 1] ?? "";
    asides.push(...labels.filter(beside).map((label): PassageAside => ({ after, ref: label, kind: "component" })));
    const apart = labels.filter((label) => !beside(label));
    if (!apart.length) return;
    flush();
    apart.forEach((label) => out.push({ kind: "component", label }));
  });
  flush();
  return out;
}

function rebuilt(blocks: readonly ChapterBlock[], chosen: ReadonlyMap<string, Paragraph>, beside: (label: string) => boolean): ChapterBlock[] {
  const byBlock = new Map<number, Map<number, string[]>>();
  for (const [label, paragraph] of chosen) {
    const pieces = byBlock.get(paragraph.block) ?? new Map<number, string[]>();
    pieces.set(paragraph.piece, [...(pieces.get(paragraph.piece) ?? []), label]);
    byBlock.set(paragraph.block, pieces);
  }
  return blocks.flatMap((block, at) => {
    if (block.kind === "component" && chosen.has(block.label)) return [];
    if (block.kind !== "passage") return [block];
    const anchored = byBlock.get(at);
    return anchored ? interleaved(block, anchored, beside) : [block];
  });
}

export function followed(moved: readonly string[], chosen: ReadonlyMap<string, Paragraph>, loose: ReadonlySet<string>, first: Paragraph): Map<string, Paragraph> {
  const placed = new Map<string, Paragraph>();
  let previous: Paragraph | null = null;
  for (const label of moved) {
    const pick: Paragraph | null = chosen.get(label) ?? (loose.has(label) ? (previous ?? first) : null);
    if (!pick) continue;
    placed.set(label, pick);
    previous = pick;
  }
  return placed;
}

export function nearPlacing(document: MonographDocument): NearPlacing {
  const sizes = layoutSizes(document);
  return { arranged: arrangedLabels(document), loose: setInProse(document), beside: (label) => sizes.get(label) === "MARGIN" };
}

export function figuresNearText(document: MonographDocument, chapter: ChapterPlan, placing: NearPlacing = nearPlacing(document)): ChapterPlan {
  const moved = trailing(chapter.blocks).filter((label) => placing.loose.has(label) || !placing.arranged.has(label));
  const found = paragraphs(document, chapter.blocks);
  if (!moved.length || !found.length) return chapter;
  const chosen = followed(moved, anchors(moved.map((label) => figure(document, label)), found), placing.loose, found[0]);
  if (!chosen.size) return chapter;
  return { ...chapter, blocks: rebuilt(chapter.blocks, chosen, placing.beside) };
}

export function placedPlan(document: MonographDocument, plan: PagePlan): PagePlan {
  if (document.shell !== null) return plan;
  const placing = nearPlacing(document);
  return { ...plan, chapters: plan.chapters.map((chapter) => figuresNearText(document, chapter, placing)) };
}
