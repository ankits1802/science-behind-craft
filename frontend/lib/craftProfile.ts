import { apiFetch } from "@/lib/api";
import type { CraftFacetClaim, CraftLocation, CraftMapPoint, CraftProfile } from "@/lib/types";

export const CRAFT_TABS = ["overview", "map", "process", "materials", "science", "sources"] as const;
export type CraftTab = (typeof CRAFT_TABS)[number];

export const CRAFT_TAB_LABEL: Record<CraftTab, string> = {
  overview: "Overview",
  map: "Map",
  process: "Process",
  materials: "Materials",
  science: "Science",
  sources: "Sources"
};

export function isCraftTab(value: string | null | undefined): value is CraftTab {
  return CRAFT_TABS.includes(value as CraftTab);
}

export function fetchCraftProfile(slug: string): Promise<CraftProfile> {
  return apiFetch<CraftProfile>(`/crafts/${encodeURIComponent(slug)}/profile`);
}

export function fetchCraftMapPoints(): Promise<CraftMapPoint[]> {
  return apiFetch<CraftMapPoint[]>("/map/crafts");
}

export function profileSourceNumbers(profile: CraftProfile): Map<string, number> {
  const numbers = new Map<string, number>();
  const take = (claims: readonly CraftFacetClaim[]) => {
    for (const claim of claims) for (const citation of claim.citations) if (!numbers.has(citation.sourceId)) numbers.set(citation.sourceId, numbers.size + 1);
  };
  take(profile.overview);
  for (const stage of profile.stages) take(stage.claims);
  for (const material of profile.materials) take(material.claims);
  for (const reaction of profile.science) for (const citation of reaction.citations) if (!numbers.has(citation.sourceId)) numbers.set(citation.sourceId, numbers.size + 1);
  for (const source of profile.sources) if (!numbers.has(source.id)) numbers.set(source.id, numbers.size + 1);
  return numbers;
}

export function locationCaption(location: CraftLocation): string {
  if (location.precision === "STATE") return "Practised across the state";
  if (location.precision === "DISTRICT") return location.stateName ? `District · ${location.stateName}` : "District";
  return [location.districtName, location.stateName].filter(Boolean).join(", ");
}
