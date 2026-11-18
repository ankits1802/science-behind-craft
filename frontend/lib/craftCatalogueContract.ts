import { HTTPS_URL } from "@/lib/answerShapes";
import { COVERAGE_CLASSES, CRAFT_GI_STATUSES } from "@/lib/craftPageContract";
import { boolean, integer, list, nullable, object, oneOf, optional, parseShape, text, type Shape } from "@/lib/shape";

export const CRAFT_CATALOGUE_PATH = "/crafts/catalogue";
export const CATALOGUE_SCHEMA_VERSION = 2;
export const CRAFT_STATUSES = ["ACTIVE", "LEGACY", "MERGED"] as const;
export const FAMILY_PALETTES = ["indigo", "bronze", "sandstone", "teak", "hide", "cane", "terracotta", "paper", "lac"] as const;

export type GiStatus = (typeof CRAFT_GI_STATUSES)[number];
export type CraftStatus = (typeof CRAFT_STATUSES)[number];
export type CoverageClass = (typeof COVERAGE_CLASSES)[number];
export type FamilyPalette = (typeof FAMILY_PALETTES)[number];

export type CraftCatalogueSubCategory = {
  id: string;
  slug: string;
  name: string;
  label: string | null;
  sortOrder: number;
  craftCount: number;
  readerCount: number;
};

export type CraftCatalogueCategory = {
  id: string;
  slug: string;
  name: string;
  label: string | null;
  palette: FamilyPalette | null;
  sortOrder: number;
  readerCount: number;
  subCategories: CraftCatalogueSubCategory[];
};

export type CatalogueHero = {
  url: string;
  width: number | null;
  height: number | null;
  alt: string;
  author: string;
  licence: string | null;
  licenceUrl: string | null;
  site: string;
  pageUrl: string;
};

export type CatalogueDepth = {
  coverage: CoverageClass | null;
  claims: number;
  stages: number;
  pictures: number;
  places: number;
};

export type CatalogueCraft = {
  id: string;
  slug: string;
  name: string;
  displayName: string;
  localName: string | null;
  categoryId: string | null;
  subCategoryId: string | null;
  familyLabel: string | null;
  kindLabel: string | null;
  palette: FamilyPalette | null;
  sourceSerial: number | null;
  stateOfOrigin: string[];
  stateOfPractice: string[];
  giStatus: GiStatus | null;
  giYear: number | null;
  isCatchAll: boolean;
  craftCode: string | null;
  aliases: string[];
  hero: CatalogueHero | null;
  depth: CatalogueDepth;
  status?: CraftStatus;
  mergedIntoId?: string | null;
  referenceCount?: number | null;
};

export type CatalogueConcept = { key: string; label: string; names: string[]; craftSlugs: string[] };

export type CatalogueSummary = {
  crafts: number;
  giRegistered: number;
  states: number;
  placed: number;
  families: number;
  kinds: number;
};

export type CraftCatalogue = {
  schemaVersion: typeof CATALOGUE_SCHEMA_VERSION;
  version: string;
  summary: CatalogueSummary;
  categories: CraftCatalogueCategory[];
  concepts: CatalogueConcept[];
  crafts: CatalogueCraft[];
};

const subCategoryShape = object<CraftCatalogueSubCategory>({
  id: text,
  slug: text,
  name: text,
  label: nullable(text),
  sortOrder: integer,
  craftCount: integer,
  readerCount: integer
});

const categoryShape = object<CraftCatalogueCategory>({
  id: text,
  slug: text,
  name: text,
  label: nullable(text),
  palette: nullable(oneOf(FAMILY_PALETTES)),
  sortOrder: integer,
  readerCount: integer,
  subCategories: list(subCategoryShape)
});

const heroShape = object<CatalogueHero>({
  url: HTTPS_URL,
  width: nullable(integer),
  height: nullable(integer),
  alt: text,
  author: text,
  licence: nullable(text),
  licenceUrl: nullable(HTTPS_URL),
  site: text,
  pageUrl: HTTPS_URL
});

const depthShape = object<CatalogueDepth>({
  coverage: nullable(oneOf(COVERAGE_CLASSES)),
  claims: integer,
  stages: integer,
  pictures: integer,
  places: integer
});

const craftShape = object<CatalogueCraft>({
  id: text,
  slug: text,
  name: text,
  displayName: text,
  localName: nullable(text),
  categoryId: nullable(text),
  subCategoryId: nullable(text),
  familyLabel: nullable(text),
  kindLabel: nullable(text),
  palette: nullable(oneOf(FAMILY_PALETTES)),
  sourceSerial: nullable(integer),
  stateOfOrigin: list(text),
  stateOfPractice: list(text),
  giStatus: nullable(oneOf(CRAFT_GI_STATUSES)),
  giYear: nullable(integer),
  isCatchAll: boolean,
  craftCode: nullable(text),
  aliases: list(text),
  hero: nullable(heroShape),
  depth: depthShape,
  status: optional(oneOf(CRAFT_STATUSES)),
  mergedIntoId: optional(nullable(text)),
  referenceCount: optional(nullable(integer))
});

const conceptShape = object<CatalogueConcept>({ key: text, label: text, names: list(text), craftSlugs: list(text, 1) });

export const catalogueSummaryShape = object<CatalogueSummary>({
  crafts: integer,
  giRegistered: integer,
  states: integer,
  placed: integer,
  families: integer,
  kinds: integer
});

export const craftCatalogueShape: Shape<CraftCatalogue> = object<CraftCatalogue>({
  schemaVersion: oneOf([CATALOGUE_SCHEMA_VERSION] as const),
  version: text,
  summary: catalogueSummaryShape,
  categories: list(categoryShape),
  concepts: list(conceptShape),
  crafts: list(craftShape)
});

export function parseCraftCatalogue(raw: unknown): CraftCatalogue {
  return parseShape(craftCatalogueShape, raw);
}
