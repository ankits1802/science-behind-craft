import { ApiError } from "@/lib/api";
import { listText } from "@/lib/format";
import type { ComparedCrafts } from "@/lib/learningApi";
import type { CraftRef } from "@/lib/types";

export const COMPARE_PAGE = "/compare";
export const COMPARE_PARAM = "crafts";
export const COMPARE_CRAFTS_MIN = 2;
export const COMPARE_CRAFTS_MAX = 4;
export const NOTHING_CITED = "No cited facts set these crafts side by side.";
export const UNKNOWN_CRAFT = "No craft has that address.";

const NOT_FOUND = 404;

export type CompareState = "idle" | "loading" | "unknown" | "failed" | "empty" | "shown";

export function compareState(asked: boolean, data: ComparedCrafts | null, cause: unknown): CompareState {
  if (!asked) return "idle";
  if (cause !== null && cause !== undefined) return cause instanceof ApiError && cause.status === NOT_FOUND ? "unknown" : "failed";
  if (data === null) return "loading";
  return data.comparison ? "shown" : "empty";
}

export function comparedSlugs(values: readonly string[]): string[] {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))].slice(0, COMPARE_CRAFTS_MAX);
}

export function comparable(slugs: readonly string[]): boolean {
  return slugs.length >= COMPARE_CRAFTS_MIN && slugs.length <= COMPARE_CRAFTS_MAX && new Set(slugs).size === slugs.length;
}

export function compareHref(slugs: readonly string[]): string {
  const search = new URLSearchParams(comparedSlugs(slugs).map((slug) => [COMPARE_PARAM, slug]));
  const query = search.toString();
  return query ? `${COMPARE_PAGE}?${query}` : COMPARE_PAGE;
}

export type CompareSuggestion = { label: string; href: string };

export function compareSuggestions(crafts: readonly CraftRef[], candidates: readonly CraftRef[]): CompareSuggestion[] {
  if (crafts.length >= COMPARE_CRAFTS_MIN) {
    const shown = crafts.slice(0, COMPARE_CRAFTS_MAX);
    return [{ label: `Compare ${listText(shown.map((craft) => craft.name))}`, href: compareHref(shown.map((craft) => craft.slug)) }];
  }
  const [asked] = crafts;
  if (!asked) return [];
  return candidates
    .filter((candidate) => candidate.slug !== asked.slug)
    .slice(0, COMPARE_CRAFTS_MAX - 1)
    .map((candidate) => ({ label: `Compare with ${candidate.name}`, href: compareHref([asked.slug, candidate.slug]) }));
}
