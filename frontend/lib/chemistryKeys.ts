import type { MonographDocument } from "@/lib/monographDocument";

export type ChemistryAsk = { equation: string; display: boolean };
export type RenderedChemistry = Readonly<Record<string, string>>;

export const NO_CHEMISTRY: RenderedChemistry = {};
const DRAWN_KINDS = new Set(["answer_block"]);
const INLINE_FIELDS = new Set(["formula"]);
const EQUATION_FIELDS = new Set(["equation"]);
const OPERATOR = /^(?:\+|=|->|<-|<->|<=>|<=>>|<<=>|→|⇌)(?:\[[^\]]*\]){0,2}$/;
const WRITTEN_TEX = /^\\ce\{/;

export function chemistryKey(equation: string, display: boolean): string {
  return `${display ? "block" : "inline"}:${equation}`;
}

export function equationPieces(equation: string): string[] {
  const trimmed = equation.trim();
  if (WRITTEN_TEX.test(trimmed)) return [trimmed];
  const pieces: string[] = [];
  let term: string[] = [];
  for (const token of trimmed.split(/\s+/)) {
    if (!OPERATOR.test(token)) {
      term.push(token);
      continue;
    }
    if (term.length) pieces.push(term.join(" "));
    term = [];
    pieces.push(token);
  }
  if (term.length) pieces.push(term.join(" "));
  return pieces;
}

function asked(value: string, displays: readonly boolean[], found: Map<string, ChemistryAsk>): void {
  const pieces = equationPieces(value);
  if (pieces.length > 1) {
    for (const piece of pieces) found.set(chemistryKey(piece, false), { equation: piece, display: false });
    return;
  }
  for (const display of displays) found.set(chemistryKey(value, display), { equation: value, display });
}

function asksOf(value: unknown, field: string | null, found: Map<string, ChemistryAsk>): void {
  if (Array.isArray(value)) {
    value.forEach((item) => asksOf(item, null, found));
    return;
  }
  if (typeof value === "string" && field !== null && value.trim()) {
    const displays = EQUATION_FIELDS.has(field) ? [true, false] : INLINE_FIELDS.has(field) ? [false] : [];
    if (displays.length) asked(value, displays, found);
    return;
  }
  if (typeof value !== "object" || value === null) return;
  for (const [key, inner] of Object.entries(value)) asksOf(inner, key, found);
}

export function chemistryAsks(value: unknown): ChemistryAsk[] {
  const found = new Map<string, ChemistryAsk>();
  asksOf(value, null, found);
  return [...found.values()];
}

export function documentChemistry(document: MonographDocument): ChemistryAsk[] {
  const drawn = document.content.components.filter((component) => DRAWN_KINDS.has(component.kind) && Object.hasOwn(document.specs, component.label));
  return chemistryAsks(drawn.map((component) => document.specs[component.label]));
}
