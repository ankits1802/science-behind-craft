import type { CraftLink } from "@/lib/answerShapes";
import { craftStatesLine } from "@/lib/craftCatalogue";
import type { CraftCatalogue } from "@/lib/craftCatalogueContract";
import type { Understood } from "@/lib/explainerContract";

export const ANY_CRAFT = "Any craft";
export const ANY_CRAFT_VALUE = "*";

export type CraftOption = { value: string; label: string; hint?: string };

export type CraftPick = { craftSlug: string | null; anyCraft: boolean };

export type CraftOffer = {
  noneLabel: string;
  detected: readonly CraftLink[];
  candidates: readonly CraftLink[];
};

export const DETECT_CRAFT: CraftPick = { craftSlug: null, anyCraft: false };
const ANY: CraftPick = { craftSlug: null, anyCraft: true };

export function namesLine(names: readonly string[]): string {
  if (names.length <= 1) return names.join("");
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}

export function detectedLabel(crafts: readonly CraftLink[]): string {
  return `${namesLine(crafts.map((craft) => craft.name))} · detected`;
}

export function craftOffer(understood: Understood | null, pick: CraftPick): CraftOffer {
  if (pick.craftSlug || !understood) return { noneLabel: ANY_CRAFT, detected: [], candidates: [] };
  const { crafts, candidates } = understood;
  if (crafts.length === 0) return { noneLabel: ANY_CRAFT, detected: [], candidates };
  return { noneLabel: detectedLabel(crafts), detected: crafts, candidates };
}

export function craftPickOf(value: string): CraftPick {
  if (value === "") return DETECT_CRAFT;
  return value === ANY_CRAFT_VALUE ? ANY : { craftSlug: value, anyCraft: false };
}

export function craftValue(pick: CraftPick, offer: CraftOffer): string {
  if (pick.craftSlug) return pick.craftSlug;
  return pick.anyCraft && offer.detected.length > 0 ? ANY_CRAFT_VALUE : "";
}

export function samePick(a: CraftPick, b: CraftPick): boolean {
  return a.craftSlug === b.craftSlug && a.anyCraft === b.anyCraft;
}

export function pickForQuestion(pick: CraftPick, asked: string, question: string): CraftPick {
  return pick.anyCraft && asked.trim() !== question.trim() ? DETECT_CRAFT : pick;
}

function knownName(understood: Understood | null, slug: string): string | null {
  const named = [...(understood?.crafts ?? []), ...(understood?.candidates ?? [])].find((craft) => craft.slug === slug);
  return named?.name ?? null;
}

export function craftOptions(catalogue: Pick<CraftCatalogue, "crafts"> | null, pick: CraftPick, understood: Understood | null): CraftOption[] {
  const listed: CraftOption[] = (catalogue?.crafts ?? [])
    .filter((craft) => craft.status !== "MERGED")
    .map((craft) => {
      const states = craftStatesLine(craft);
      return states ? { value: craft.slug, label: craft.displayName, hint: states } : { value: craft.slug, label: craft.displayName };
    });
  const special: CraftOption[] = craftOffer(understood, pick).detected.length > 0 ? [{ value: ANY_CRAFT_VALUE, label: ANY_CRAFT }] : [];
  const picked = pick.craftSlug;
  if (!picked || listed.some((option) => option.value === picked)) return [...special, ...listed];
  return [...special, { value: picked, label: knownName(understood, picked) ?? picked }, ...listed];
}
