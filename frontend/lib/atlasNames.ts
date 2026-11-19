import type { NativeName, NativeScript } from "@/lib/editorialText";

export const NAMES_WALL_MIN = 6;

const SCRIPTS: readonly NativeScript[] = ["Deva", "Beng", "Gujr", "Guru", "Orya", "Taml", "Mlym", "Telu", "Knda", "Aran", "Arab", "Mtei", "Olck"];

export type SourcedName = { text: string; lang: string; script: string | null; sourceId: string; sourceKind: string; reviewed: boolean };
export type NamedCraft = { slug: string; englishName: string; state: string; nativeName: NativeName };
export type NamesByState = { state: string; crafts: NamedCraft[] };

function isScript(script: string | null): script is NativeScript {
  return script !== null && (SCRIPTS as readonly string[]).includes(script);
}

export function shownName(name: SourcedName | null): NativeName | null {
  if (!name || !name.reviewed || !name.sourceId.trim() || !name.text.trim() || !isScript(name.script)) return null;
  const sourceKind = name.sourceKind.toLowerCase() === "wikidata" ? "wikidata" : "dossier";
  return { text: name.text, lang: name.lang, script: name.script, sourceId: name.sourceId, sourceKind, reviewed: true };
}

export function namesByState(names: readonly NamedCraft[]): NamesByState[] {
  const groups = new Map<string, NamedCraft[]>();
  for (const named of names) groups.set(named.state, [...(groups.get(named.state) ?? []), named]);
  return [...groups]
    .map(([state, crafts]) => ({ state, crafts: [...crafts].sort((a, b) => a.englishName.localeCompare(b.englishName, "en")) }))
    .sort((a, b) => b.crafts.length - a.crafts.length || a.state.localeCompare(b.state, "en"));
}

export function offersNamesWall(names: readonly NamedCraft[]): boolean {
  return names.length >= NAMES_WALL_MIN;
}
