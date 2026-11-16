import { apiFetch } from "@/lib/api";
import { checkedProcess } from "@/lib/processView";
import { CRAFT_REGION_PATH, craftRegionShape, type CraftRegion } from "@/lib/regionContract";
import { checkedRegion, STATE_PLACE_NOTE } from "@/lib/regionView";
import { craftProcessShape, SCIENCE_PROCESS_PATH, type CraftProcess } from "@/lib/scienceContract";
import { parseShape } from "@/lib/shape";
import type { CraftFacetClaim, CraftLocation, CraftMapPoint, CraftProfile, SourceRef } from "@/lib/types";

export const CRAFT_TABS = ["overview", "region", "process", "materials", "sources"] as const;
export type CraftTab = (typeof CRAFT_TABS)[number];

export const CRAFT_TAB_LABEL: Record<CraftTab, string> = {
  overview: "Overview",
  region: "Region",
  process: "Process",
  materials: "Materials",
  sources: "Sources"
};

export function isCraftTab(value: string | null | undefined): value is CraftTab {
  return CRAFT_TABS.includes(value as CraftTab);
}

export function fetchCraftProfile(slug: string): Promise<CraftProfile> {
  return apiFetch<CraftProfile>(`/crafts/${encodeURIComponent(slug)}/profile`);
}

export async function fetchCraftProcess(slug: string): Promise<CraftProcess> {
  return checkedProcess(parseShape(craftProcessShape, await apiFetch<unknown>(SCIENCE_PROCESS_PATH(slug))));
}

export async function fetchCraftRegion(slug: string): Promise<CraftRegion> {
  return checkedRegion(parseShape(craftRegionShape, await apiFetch<unknown>(CRAFT_REGION_PATH(slug))));
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

export type CraftSources = { ordered: SourceRef[]; numbers: Map<string, number>; byId: Map<string, SourceRef> };

export function craftSources(profile: CraftProfile, process: CraftProcess | null, region: CraftRegion | null): CraftSources {
  const numbers = profileSourceNumbers(profile);
  const byId = new Map(profile.sources.map((source) => [source.id, source]));
  for (const source of [...(process?.sources ?? []), ...(region?.sources ?? [])]) {
    if (!byId.has(source.id)) byId.set(source.id, source);
    if (!numbers.has(source.id)) numbers.set(source.id, numbers.size + 1);
  }
  const ordered = [...byId.values()].sort((a, b) => (numbers.get(a.id) ?? 0) - (numbers.get(b.id) ?? 0));
  return { ordered, numbers, byId };
}

export function locationCaption(location: CraftLocation): string {
  if (location.precision === "STATE") return STATE_PLACE_NOTE;
  if (location.precision === "DISTRICT") return location.stateName ? `District · ${location.stateName}` : "District";
  return [location.districtName, location.stateName].filter(Boolean).join(", ");
}
