import type { MonographDocument } from "@/lib/monographDocument";

export type KitDef = { scope: string | null; markup: string };
export type ScopedDefs = { scope: string | null; markup: string[] };

const REFERENCE = /(?:url\(#|<use\s[^>]*?href=["']#|"(?:xlink:)?href":"#)([A-Za-z][\w-]*)/g;
const DEFINED = /(?:\sid=["']|"id":")([A-Za-z][\w-]*)/g;

export function referencedIds(text: string): string[] {
  return [...text.matchAll(REFERENCE)].map((found) => found[1]);
}

export function definedIds(text: string): string[] {
  return [...text.matchAll(DEFINED)].map((found) => found[1]);
}

export function usedDefs(texts: readonly string[], defs: Readonly<Record<string, KitDef>>): KitDef[] {
  const own = new Set(texts.flatMap(definedIds));
  const chosen = new Map<string, KitDef>();
  const waiting = texts.flatMap(referencedIds);
  while (waiting.length) {
    const id = waiting.shift() as string;
    if (chosen.has(id) || own.has(id) || !Object.hasOwn(defs, id)) continue;
    chosen.set(id, defs[id]);
    waiting.push(...referencedIds(defs[id].markup));
  }
  return [...chosen.values()];
}

export function defsByScope(defs: readonly KitDef[]): ScopedDefs[] {
  const scopes = new Map<string | null, string[]>();
  for (const def of defs) scopes.set(def.scope, [...(scopes.get(def.scope) ?? []), def.markup]);
  return [...scopes].map(([scope, markup]) => ({ scope, markup }));
}

export function documentTexts(document: MonographDocument): string[] {
  return [JSON.stringify(document.specs), ...Object.values(document.fragments)];
}
