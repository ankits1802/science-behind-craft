import type { ExplainerSentence } from "@/lib/explainerBlockBase";
import type { SupplyLink, SupplyMapBlock } from "@/lib/explainerPlace";

export type LongitudeLatitudeBox = { minLongitude: number; maxLongitude: number; minLatitude: number; maxLatitude: number };
export type SupplyOrigin = { key: string; origin: string; material: string; wikidataId: string | null; place: { latitude: number; longitude: number; pin: number } | null };
export type SupplyGroup = { key: string; material: string; origins: SupplyOrigin[]; sentences: ExplainerSentence[] };

export function wikidataUrl(id: string): string {
  return `https://www.wikidata.org/wiki/${encodeURIComponent(id)}`;
}

function inBox(link: SupplyLink, box: LongitudeLatitudeBox): link is SupplyLink & { latitude: number; longitude: number; wikidataId: string } {
  const { latitude, longitude, wikidataId } = link;
  if (latitude === null || longitude === null || wikidataId === null) return false;
  return longitude >= box.minLongitude && longitude <= box.maxLongitude && latitude >= box.minLatitude && latitude <= box.maxLatitude;
}

export function supplyGroups(block: SupplyMapBlock, box: LongitudeLatitudeBox): SupplyGroup[] {
  const groups = new Map<string, SupplyGroup>();
  let pins = 0;
  for (const link of block.links) {
    const key = link.material.toLocaleLowerCase("en");
    const group = groups.get(key) ?? { key, material: link.material, origins: [], sentences: [] };
    const place = inBox(link, box) ? { latitude: link.latitude, longitude: link.longitude, pin: (pins += 1) } : null;
    group.origins.push({ key: `${key}:${link.origin.toLocaleLowerCase("en")}`, origin: link.origin, material: group.material, wikidataId: link.wikidataId, place });
    if (!group.sentences.some((sentence) => sentence.text === link.sentence.text)) group.sentences.push(link.sentence);
    groups.set(key, group);
  }
  return [...groups.values()];
}

export type PlacedOrigin = SupplyOrigin & { place: NonNullable<SupplyOrigin["place"]> };

export function placedOrigins(groups: readonly SupplyGroup[]): PlacedOrigin[] {
  return groups.flatMap((group) => group.origins.flatMap((origin) => (origin.place ? [{ ...origin, place: origin.place }] : [])));
}
