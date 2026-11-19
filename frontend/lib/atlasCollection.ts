import type { PlateMaterial } from "@/components/editorial/TypographicPlate";
import type { CatalogueCraft, CraftCatalogue, CraftCatalogueCategory, CraftCatalogueSubCategory, FamilyPalette } from "@/lib/craftCatalogueContract";

export const BIG_SHELF = 50;
export const BIG_SHELF_PLATES = 8;
export const SMALL_SHELF_PLATES = 4;

const PALETTE_MATERIAL: Record<FamilyPalette, PlateMaterial> = {
  indigo: "textile",
  bronze: "metal",
  teak: "wood",
  cane: "fibre",
  terracotta: "clay",
  sandstone: "stone",
  paper: "paper",
  hide: "leather",
  lac: "misc"
};

const MISC_MATERIALS: readonly [RegExp, PlateMaterial][] = [
  [/paint/i, "paint"],
  [/instrument/i, "instr"],
  [/toy|figurine|doll/i, "toys"]
];

const CATCH_ALL_KIND = /^(more|other)\b/i;

export type AtlasPlate = {
  craft: CatalogueCraft;
  href: string;
  material: PlateMaterial;
  kicker: string | null;
  state: string | null;
  monograph: boolean;
  gi: boolean;
};

export type SubFamilyCount = { id: string; name: string; count: number };

export type AtlasShelf = {
  id: string;
  slug: string;
  name: string;
  material: PlateMaterial;
  count: number;
  subFamilies: SubFamilyCount[];
  lead: AtlasPlate | null;
  plates: AtlasPlate[];
  more: AtlasPlate[];
  big: boolean;
  leadEnd: boolean;
};

export function craftHref(craft: Pick<CatalogueCraft, "slug">): string {
  return `/crafts/${encodeURIComponent(craft.slug)}`;
}

export function categoryHref(category: Pick<CraftCatalogueCategory, "slug">): string {
  return `/categories/${encodeURIComponent(category.slug)}`;
}

export function familyName(category: Pick<CraftCatalogueCategory, "label" | "name">): string {
  return category.label ?? category.name;
}

export function subFamilyName(sub: Pick<CraftCatalogueSubCategory, "label" | "name">): string {
  return sub.label ?? sub.name;
}

export function familyMaterial(category: Pick<CraftCatalogueCategory, "palette">): PlateMaterial {
  return category.palette ? PALETTE_MATERIAL[category.palette] : "misc";
}

export function plateMaterial(family: PlateMaterial, subFamily: string | null): PlateMaterial {
  if (family !== "misc" || !subFamily) return family;
  return MISC_MATERIALS.find(([pattern]) => pattern.test(subFamily))?.[1] ?? "misc";
}

export function isCatchAllKind(sub: Pick<CraftCatalogueSubCategory, "label" | "name">): boolean {
  return CATCH_ALL_KIND.test(sub.name) || CATCH_ALL_KIND.test(sub.label ?? "");
}

export function isReaderCraft(craft: CatalogueCraft): boolean {
  return (craft.status ?? "ACTIVE") === "ACTIVE" && !craft.isCatchAll;
}

export function readerCrafts(catalogue: CraftCatalogue): CatalogueCraft[] {
  return catalogue.crafts.filter(isReaderCraft);
}

export function isMonograph(craft: CatalogueCraft): boolean {
  return craft.depth.coverage !== null;
}

export function plateOrder(a: CatalogueCraft, b: CatalogueCraft): number {
  const rank = (craft: CatalogueCraft) => (isMonograph(craft) ? 0 : craft.giStatus === "GI" ? 1 : 2);
  return rank(a) - rank(b) || a.displayName.localeCompare(b.displayName, "en");
}

function subCategoryOf(category: CraftCatalogueCategory, craft: CatalogueCraft): CraftCatalogueSubCategory | null {
  return category.subCategories.find((sub) => sub.id === craft.subCategoryId) ?? null;
}

export function atlasPlate(category: CraftCatalogueCategory, craft: CatalogueCraft): AtlasPlate {
  const sub = subCategoryOf(category, craft);
  const kind = sub ? subFamilyName(sub) : craft.kindLabel;
  return {
    craft,
    href: craftHref(craft),
    material: plateMaterial(familyMaterial(category), kind),
    kicker: sub && !isCatchAllKind(sub) ? kind : null,
    state: craft.stateOfPractice[0] ?? craft.stateOfOrigin[0] ?? null,
    monograph: isMonograph(craft),
    gi: craft.giStatus === "GI"
  };
}

export function familyCrafts(catalogue: CraftCatalogue, category: CraftCatalogueCategory): CatalogueCraft[] {
  const subs = new Set(category.subCategories.map((sub) => sub.id));
  return catalogue.crafts
    .filter((craft) => isReaderCraft(craft) && (craft.categoryId === category.id || (craft.subCategoryId !== null && subs.has(craft.subCategoryId))))
    .sort(plateOrder);
}

export function subFamilyCounts(category: CraftCatalogueCategory): SubFamilyCount[] {
  return category.subCategories
    .filter((sub) => sub.readerCount > 0)
    .sort((a, b) => b.readerCount - a.readerCount || a.sortOrder - b.sortOrder)
    .map((sub) => ({ id: sub.id, name: subFamilyName(sub), count: sub.readerCount }));
}

export function shelfLead(crafts: readonly CatalogueCraft[]): CatalogueCraft | null {
  return crafts.find((craft) => craft.hero !== null) ?? null;
}

export function sortedFamilies(catalogue: CraftCatalogue): CraftCatalogueCategory[] {
  return catalogue.categories.filter((category) => category.readerCount > 0).sort((a, b) => a.sortOrder - b.sortOrder);
}

export function familyShelf(catalogue: CraftCatalogue, category: CraftCatalogueCategory, at: number): AtlasShelf {
  const crafts = familyCrafts(catalogue, category);
  const lead = shelfLead(crafts);
  const big = category.readerCount >= BIG_SHELF;
  const rest = crafts.filter((craft) => craft !== lead).slice(0, big ? BIG_SHELF_PLATES : SMALL_SHELF_PLATES);
  return {
    id: category.id,
    slug: category.slug,
    name: familyName(category),
    material: familyMaterial(category),
    count: category.readerCount,
    subFamilies: subFamilyCounts(category),
    lead: lead ? atlasPlate(category, lead) : null,
    plates: rest.map((craft) => atlasPlate(category, craft)),
    more: [],
    big,
    leadEnd: at % 2 === 1
  };
}

export function familyShelves(catalogue: CraftCatalogue): AtlasShelf[] {
  return sortedFamilies(catalogue).map((category, at) => familyShelf(catalogue, category, at));
}

export function subFamilyShelves(catalogue: CraftCatalogue, category: CraftCatalogueCategory): AtlasShelf[] {
  const crafts = familyCrafts(catalogue, category);
  return subFamilyCounts(category).map((sub, at) => {
    const own = crafts.filter((craft) => craft.subCategoryId === sub.id);
    const lead = shelfLead(own);
    const big = sub.count >= BIG_SHELF;
    const plates = own.filter((craft) => craft !== lead).map((craft) => atlasPlate(category, craft));
    const shown = big ? BIG_SHELF_PLATES : SMALL_SHELF_PLATES;
    return {
      id: sub.id,
      slug: category.slug,
      name: sub.name,
      material: plateMaterial(familyMaterial(category), sub.name),
      count: sub.count,
      subFamilies: [],
      lead: lead ? atlasPlate(category, lead) : null,
      plates: plates.slice(0, shown),
      more: plates.slice(shown),
      big,
      leadEnd: at % 2 === 1
    };
  });
}

export function findFamily(catalogue: CraftCatalogue, slug: string): CraftCatalogueCategory | null {
  const wanted = slug.toLowerCase();
  return catalogue.categories.find((category) => category.slug.toLowerCase() === wanted) ?? null;
}

export function shelfSubLine(subFamilies: readonly SubFamilyCount[]): string {
  return subFamilies.map((sub) => `${sub.name} ${sub.count}`).join(" · ");
}

function inSentence(name: string): string {
  return /^[A-Z][a-z]/.test(name) ? name.charAt(0).toLowerCase() + name.slice(1) : name;
}

export function indexSubLine(subFamilies: readonly SubFamilyCount[]): string {
  return subFamilies.map((sub, at) => `${at === 0 ? sub.name : inSentence(sub.name)} ${sub.count}`).join(", ");
}
