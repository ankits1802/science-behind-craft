import { list, object, text, type Shape } from "@/lib/shape";

export type DesignNote = { chapter: string; where: string; problem: string; fix: string };
export type DesignCritique = { verdict: string; notes: DesignNote[] };

export const designNoteShape: Shape<DesignNote> = object<DesignNote>({ chapter: text, where: text, problem: text, fix: text });
export const designCritiqueShape: Shape<DesignCritique> = object<DesignCritique>({ verdict: text, notes: list(designNoteShape) });

export const CRITIQUE_TITLE = "The agent's design critique";
export const CRITIQUE_LEAD = "What the proposer's AI judged in the pictures of its last preview, chapter by chapter. Its own feedback, never a check.";
export const NO_NOTES = "It read every chapter and would change nothing.";

export function chapterLabel(chapter: string): string {
  const words = chapter.replace(/[_-]+/g, " ").trim();
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : chapter;
}

export function noteHeading(note: DesignNote): string {
  return `${chapterLabel(note.chapter)}: ${note.where}`;
}

export function notesLine(critique: DesignCritique): string {
  const count = critique.notes.length;
  if (count === 0) return NO_NOTES;
  return count === 1 ? "1 note, in reading order." : `${count} notes, in reading order.`;
}
