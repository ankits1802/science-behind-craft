import { apiFetch } from "@/lib/api";
import { CRAFT_REGION_PATH, craftRegionShape, type CraftRegion } from "@/lib/regionContract";
import { checkedRegion } from "@/lib/regionView";
import { parseShape } from "@/lib/shape";
import type { CraftMapPoint } from "@/lib/types";

export async function fetchCraftRegion(slug: string): Promise<CraftRegion> {
  return checkedRegion(parseShape(craftRegionShape, await apiFetch<unknown>(CRAFT_REGION_PATH(slug))));
}

export function fetchCraftMapPoints(): Promise<CraftMapPoint[]> {
  return apiFetch<CraftMapPoint[]>("/map/crafts");
}
