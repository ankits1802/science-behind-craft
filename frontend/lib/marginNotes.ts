import { shortTitle } from "@/lib/citationCluster";
import type { SourceRef } from "@/lib/types";

export const NOTE_GAP_PX = 8;

export type MarginNote = { number: number; title: string; year: number | null; anchorId: string };

export type CitingSentence = { anchorId: string; sourceIds: readonly string[] };

export function marginNotes(sentences: readonly CitingSentence[], numbers: ReadonlyMap<string, number>, sourcesById: ReadonlyMap<string, SourceRef>): MarginNote[] {
  const seen = new Set<string>();
  const notes: MarginNote[] = [];
  for (const sentence of sentences) {
    const fresh = [...new Set(sentence.sourceIds)].filter((id) => !seen.has(id) && numbers.has(id)).sort((a, b) => (numbers.get(a) ?? 0) - (numbers.get(b) ?? 0));
    for (const id of fresh) {
      seen.add(id);
      const source = sourcesById.get(id);
      notes.push({ number: numbers.get(id) ?? 0, title: source ? shortTitle(source.title) : "Source", year: source?.year ?? null, anchorId: sentence.anchorId });
    }
  }
  return notes;
}

export function stackNotes(wanted: readonly number[], heights: readonly number[], gap = NOTE_GAP_PX): number[] {
  const tops: number[] = [];
  let floor = Number.NEGATIVE_INFINITY;
  wanted.forEach((top, index) => {
    const placed = Math.max(top, floor);
    tops.push(placed);
    floor = placed + (heights[index] ?? 0) + gap;
  });
  return tops;
}
