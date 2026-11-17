import type { UserRole } from "@/lib/types";

export const DESKTOP_NAV_MIN_WIDTH = 1024;
export const NO_LAYER_LABEL = "Craft places";
export const CITED_CONTENT = [
  "[data-level]",
  '[data-testid="answer-sentence"]',
  '[data-testid="source-passage"]',
  '[id^="source-"]',
  "blockquote"
].join(", ");
export const OVERFLOW_LIMIT = 12;

const TEXT_LIMIT = 200;
const CONTEXT_CHARS = 30;

export const GAP_COPY_PATTERNS: readonly RegExp[] = [
  /\bcoming soon\b/gi,
  /\bnot (?:yet )?available\b/gi,
  /\b(?:isn['’]t|aren['’]t|wasn['’]t) (?:yet )?available\b/gi,
  /\bnot (?:yet )?built\b/gi,
  /\b(?:isn['’]t|hasn['’]t been|wasn['’]t) built\b/gi,
  /\bnot (?:yet )?implemented\b/gi,
  /\bnot (?:yet )?supported\b/gi,
  /\bunder construction\b/gi,
  /\bwork in progress\b/gi,
  /\bnot (?:yet )?(?:wired|hooked) up\b/gi,
  /\bstay tuned\b/gi,
  /\bin a (?:future|later) (?:release|version|phase|update)\b/gi
];

export type NavExpectation = { bar: string[]; menu: string[]; depths: string[] };

const LEARNER_BAR = ["Ask", "Crafts", "Map"];
const LEARNER_MENU = ["Ask", "Crafts", "Map", "Settings"];
const EVERY_DEPTH = ["Basic", "Detailed", "Expert"];

export const NAV_BY_ROLE: Partial<Record<UserRole, NavExpectation>> = {
  STUDENT: { bar: LEARNER_BAR, menu: LEARNER_MENU, depths: EVERY_DEPTH },
  RESEARCHER: { bar: LEARNER_BAR, menu: LEARNER_MENU, depths: EVERY_DEPTH }
};

export function navExpectation(role: UserRole): NavExpectation | null {
  return NAV_BY_ROLE[role] ?? null;
}

export function clip(text: string, limit = TEXT_LIMIT): string {
  const flat = text.replace(/\s+/g, " ").trim();
  return flat.length > limit ? `${flat.slice(0, limit - 1)}…` : flat;
}

export function gapCopyFindings(text: string): string[] {
  const found = new Set<string>();
  for (const pattern of GAP_COPY_PATTERNS) {
    for (const match of text.matchAll(pattern)) {
      const before = text.slice(Math.max(0, match.index - CONTEXT_CHARS), match.index);
      const after = text.slice(match.index + match[0].length, match.index + match[0].length + CONTEXT_CHARS);
      const head = match.index > CONTEXT_CHARS ? before.replace(/^\S*\s?/, "") : before;
      const tail = match.index + match[0].length + CONTEXT_CHARS < text.length ? after.replace(/\s?\S*$/, "") : after;
      found.add(clip(`${head}${match[0]}${tail}`));
    }
  }
  return [...found];
}

export function labelProblems(where: string, expected: readonly string[], actual: readonly string[]): string[] {
  const shown = actual.map((label) => label.replace(/\s+/g, " ").trim()).filter(Boolean);
  const same = shown.length === expected.length && expected.every((label, index) => label === shown[index]);
  if (same) return [];
  return [`${where} shows [${shown.join(", ")}]; this role should see [${expected.join(", ")}]`];
}
