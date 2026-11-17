import type { GroupKind, PageArea, PagePlace, PlaceKind, PlaceRole } from "@/lib/craftPageContract";
import { PLACE_ROLES } from "@/lib/districtCraftsContract";

export const PLACE_ROLE_LABEL: Record<PlaceRole, string> = {
  PRACTISED: "Practised",
  ORIGIN: "Origin",
  HISTORIC_CENTRE: "Historic centre",
  MATERIAL_SOURCE: "Material source",
  MARKET: "Market",
  MIGRATED_FROM: "Migrated from",
  MIGRATED_TO: "Migrated to"
};

export const PLACE_KIND_LABEL: Record<PlaceKind, string> = {
  VILLAGE: "Village",
  TOWN: "Town",
  DISTRICT: "District",
  STATE: "State",
  COUNTRY: "Country",
  REGION: "Region",
  RIVER: "River"
};

export const GROUP_KIND_LABEL: Record<GroupKind, string> = {
  COMMUNITY: "Community",
  PERSON: "Person",
  ORGANISATION: "Organisation"
};

export const MAKING_ROLES: ReadonlySet<PlaceRole> = new Set<PlaceRole>(["PRACTISED", "ORIGIN", "HISTORIC_CENTRE", "MIGRATED_FROM", "MIGRATED_TO"]);

export type PlaceRow = {
  key: string;
  name: string;
  kind: PlaceKind;
  where: string;
  roles: PlaceRole[];
  claimIds: string[];
};

export type PlaceDistricts = { made: Set<number>; named: Map<number, string> };

function areaKey(area: PageArea | null): string {
  return area ? `${area.lgd ?? ""}:${area.name}` : "";
}

export function placeWhere(place: Pick<PagePlace, "kind" | "district" | "state" | "country">): string {
  const state = place.state?.name ?? null;
  if (place.kind === "DISTRICT") return state ?? place.country;
  if (place.kind === "STATE") return place.country;
  if (place.district) return [`${place.district.name} district`, state].filter(Boolean).join(", ");
  return [state, place.country].filter(Boolean).join(", ");
}

export function placeRows(places: readonly PagePlace[]): PlaceRow[] {
  const rows = new Map<string, PlaceRow>();
  for (const place of places) {
    const key = [place.name, place.kind, areaKey(place.district), areaKey(place.state), place.country].join("|");
    const row = rows.get(key) ?? { key: place.key, name: place.name, kind: place.kind, where: placeWhere(place), roles: [], claimIds: [] };
    if (!row.roles.includes(place.role)) row.roles.push(place.role);
    for (const id of place.claimIds) if (!row.claimIds.includes(id)) row.claimIds.push(id);
    rows.set(key, row);
  }
  return [...rows.values()].map((row) => ({ ...row, roles: [...row.roles].sort((a, b) => PLACE_ROLES.indexOf(a) - PLACE_ROLES.indexOf(b)) }));
}

export function placeDistricts(places: readonly PagePlace[]): PlaceDistricts {
  const made = new Set<number>();
  const named = new Map<number, string>();
  for (const place of places) {
    const lgd = place.district?.lgd ?? null;
    if (lgd === null || !place.district) continue;
    named.set(lgd, place.district.name);
    if (MAKING_ROLES.has(place.role)) made.add(lgd);
  }
  return { made, named };
}
