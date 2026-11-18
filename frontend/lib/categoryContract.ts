import { apiFetch } from "@/lib/api";
import { answerSentenceShape, citationShape, CRAFT_PATH, INSTANT, sourceRefShape, storedLevelShape, UUID, type StoredLevel } from "@/lib/answerShapes";
import { FAMILY_PALETTES, type FamilyPalette } from "@/lib/craftCatalogueContract";
import { COVERAGE_CLASSES, CRAFT_GI_STATUSES } from "@/lib/craftPageContract";
import { mediaRefShape, termSpanShape, TERM_KEY, type MediaRef, type TermSpan } from "@/lib/explainerBlockBase";
import { DISCIPLINES, type Discipline } from "@/lib/explainerContract";
import { boolean, integer, list, matching, nullable, object, oneOf, parseShape, ShapeError, text, type Shape } from "@/lib/shape";
import type { AnswerSentence, Citation, SourceRef } from "@/lib/types";

export const CATEGORY_LIST_PATH = "/categories";
export const CATEGORY_PAGE_PATH = (slug: string) => `/categories/${encodeURIComponent(slug)}`;
export const CATEGORY_PATH = matching(/^\/categories\/\S+$/, "a category path");

export type CategoryRef = { slug: string; name: string; label: string; palette: FamilyPalette | null; path: string; craftCount: number };
export type CategorySearch = { query: string; site: string };
export type CategoryCuration = { version: number; curatedAt: string; coverage: (typeof COVERAGE_CLASSES)[number]; searched: CategorySearch[] };
export type CategoryHero = { media: MediaRef; caption: string };
export type CategorySentence = { id: string; text: string; level: StoredLevel; claimIds: string[]; terms: TermSpan[]; subCategories: string[]; crafts: string[] };
export type CategoryFact = { label: string; value: string; claimIds: string[] };
export type CategorySection = { discipline: Discipline; title: string; sentences: CategorySentence[] };
export type CategoryOverview = { lede: CategorySentence[]; keyFacts: CategoryFact[]; sections: CategorySection[] };
export type MemberCraft = { slug: string; name: string; path: string; giStatus: (typeof CRAFT_GI_STATUSES)[number] | null; catchAll: boolean; curated: boolean };
export type CategorySubCategory = {
  slug: string;
  name: string;
  label: string;
  craftCount: number;
  crafts: MemberCraft[];
  sentence: CategorySentence | null;
  openQuestion: string | null;
};
export type CategoryDiffer = { about: string; claimIds: string[] };
export type CategoryTerm = { key: string | null; label: string; names: string[]; meaning: string; language: string | null; script: string | null; claimIds: string[] };
export type CategoryPicture = { media: MediaRef; caption: string; claimIds: string[] };
export type CategoryQuestion = { key: string; question: string; settledBy: string | null; claimIds: string[]; subCategories: string[] };
export type CategoryClaim = { id: string; text: string; level: StoredLevel; discipline: Discipline; sourcesDiffer: boolean; citations: Citation[] };
export type NumberedSource = SourceRef & { number: number };
export type CategoryPage = {
  schemaVersion: 1;
  category: CategoryRef;
  curated: boolean;
  curation: CategoryCuration | null;
  hero: CategoryHero | null;
  overview: CategoryOverview;
  subCategories: CategorySubCategory[];
  sourcesDiffer: CategoryDiffer[];
  glossary: CategoryTerm[];
  pictures: CategoryPicture[];
  openQuestions: CategoryQuestion[];
  claims: CategoryClaim[];
  sources: NumberedSource[];
};
export type SubCategoryCount = { slug: string; name: string; label: string; craftCount: number };
export type CategorySummary = CategoryRef & { curated: boolean; subCategories: SubCategoryCount[]; hero: CategoryHero | null; lede: AnswerSentence | null };
export type CategoryList = { schemaVersion: 1; categories: CategorySummary[]; sources: SourceRef[] };

const COUNT: Shape<number> = {
  expected: "a whole number from 0",
  parse(value, path) {
    const whole = integer.parse(value, path);
    if (whole < 0) throw new ShapeError(path, "a whole number from 0");
    return whole;
  }
};
const CLAIM_IDS = list(UUID, 1);

const refFields = { slug: text, name: text, label: text, palette: nullable(oneOf(FAMILY_PALETTES)), path: CATEGORY_PATH, craftCount: COUNT };
const heroShape: Shape<CategoryHero> = object<CategoryHero>({ media: mediaRefShape, caption: text });
const sentenceShape: Shape<CategorySentence> = object<CategorySentence>({
  id: text,
  text,
  level: storedLevelShape,
  claimIds: CLAIM_IDS,
  terms: list(termSpanShape),
  subCategories: list(text),
  crafts: list(text)
});
const memberShape: Shape<MemberCraft> = object<MemberCraft>({
  slug: text,
  name: text,
  path: CRAFT_PATH,
  giStatus: nullable(oneOf(CRAFT_GI_STATUSES)),
  catchAll: boolean,
  curated: boolean
});
const countShape: Shape<SubCategoryCount> = object<SubCategoryCount>({ slug: text, name: text, label: text, craftCount: COUNT });

export const categoryPageShape: Shape<CategoryPage> = object<CategoryPage>({
  schemaVersion: oneOf([1] as const),
  category: object<CategoryRef>(refFields),
  curated: boolean,
  curation: nullable(
    object<CategoryCuration>({ version: COUNT, curatedAt: INSTANT, coverage: oneOf(COVERAGE_CLASSES), searched: list(object<CategorySearch>({ query: text, site: text })) })
  ),
  hero: nullable(heroShape),
  overview: object<CategoryOverview>({
    lede: list(sentenceShape),
    keyFacts: list(object<CategoryFact>({ label: text, value: text, claimIds: CLAIM_IDS })),
    sections: list(object<CategorySection>({ discipline: oneOf(DISCIPLINES), title: text, sentences: list(sentenceShape, 1) }))
  }),
  subCategories: list(
    object<CategorySubCategory>({ slug: text, name: text, label: text, craftCount: COUNT, crafts: list(memberShape), sentence: nullable(sentenceShape), openQuestion: nullable(text) })
  ),
  sourcesDiffer: list(object<CategoryDiffer>({ about: text, claimIds: list(UUID, 2) })),
  glossary: list(
    object<CategoryTerm>({ key: nullable(TERM_KEY), label: text, names: list(text), meaning: text, language: nullable(text), script: nullable(text), claimIds: list(UUID) })
  ),
  pictures: list(object<CategoryPicture>({ media: mediaRefShape, caption: text, claimIds: CLAIM_IDS })),
  openQuestions: list(object<CategoryQuestion>({ key: text, question: text, settledBy: nullable(text), claimIds: list(UUID), subCategories: list(text) })),
  claims: list(
    object<CategoryClaim>({ id: UUID, text, level: storedLevelShape, discipline: oneOf(DISCIPLINES), sourcesDiffer: boolean, citations: list(citationShape, 1) })
  ),
  sources: list({
    expected: "a numbered source",
    parse(value, path) {
      const { number, ...source } = (typeof value === "object" && value !== null ? value : {}) as Record<string, unknown>;
      return { ...sourceRefShape.parse(source, path), number: COUNT.parse(number, `${path}.number`) };
    }
  })
});

export const categoryListShape: Shape<CategoryList> = object<CategoryList>({
  schemaVersion: oneOf([1] as const),
  categories: list(
    object<CategorySummary>({ ...refFields, curated: boolean, subCategories: list(countShape), hero: nullable(heroShape), lede: nullable(answerSentenceShape) })
  ),
  sources: list(sourceRefShape)
});

export function overviewSentences(page: CategoryPage): CategorySentence[] {
  return [...page.overview.lede, ...page.overview.sections.flatMap((section) => section.sentences)];
}

export function categoryClaimIds(page: CategoryPage): string[] {
  const rows = [...page.overview.keyFacts, ...page.sourcesDiffer, ...page.glossary, ...page.pictures, ...page.openQuestions];
  return [...overviewSentences(page), ...rows].flatMap((row) => row.claimIds);
}

function once(what: string, keys: readonly string[]): void {
  if (new Set(keys).size !== keys.length) throw new ShapeError(what, "each listed once");
}

function sameSet(a: Iterable<string>, b: Iterable<string>): boolean {
  const left = new Set(a);
  const right = new Set(b);
  return left.size === right.size && [...left].every((key) => right.has(key));
}

function checkClaimsAndSources(page: CategoryPage): void {
  once("claims", page.claims.map((claim) => claim.id));
  if (!sameSet(categoryClaimIds(page), page.claims.map((claim) => claim.id))) throw new ShapeError("claims", "exactly the claims the page's parts cite");
  once("sources", page.sources.map((source) => source.id));
  page.sources.forEach((source, index) => {
    if (source.number !== index + 1) throw new ShapeError(`source ${source.id}`, `number ${index + 1}`);
  });
  const cited = page.claims.flatMap((claim) => claim.citations.map((citation) => citation.sourceId));
  if (!sameSet(cited, page.sources.map((source) => source.id))) throw new ShapeError("sources", "exactly the sources the claims cite");
}

function checkReferences(page: CategoryPage): void {
  const sentences = overviewSentences(page);
  once("sentences", sentences.map((sentence) => sentence.id));
  const members = new Set(page.subCategories.flatMap((sub) => sub.crafts.map((craft) => craft.slug)));
  const subs = new Set(page.subCategories.map((sub) => sub.slug));
  for (const sentence of sentences) {
    if (sentence.level === "HYPOTHESIS") throw new ShapeError(`sentence ${sentence.id}`, "a sentence resting on facts");
    if (!sentence.crafts.every((slug) => members.has(slug)) || !sentence.subCategories.every((slug) => subs.has(slug))) throw new ShapeError(`sentence ${sentence.id}`, "crafts and sub-categories the page lists");
  }
  const questions = new Set(page.openQuestions.map((question) => question.key));
  for (const sub of page.subCategories) {
    if (sub.craftCount !== sub.crafts.filter((craft) => !craft.catchAll).length) throw new ShapeError(`sub-category ${sub.slug}`, "a count without the catch-all rows");
    if (sub.sentence && (!sub.sentence.subCategories.includes(sub.slug) || !sentences.some((sentence) => sentence.id === sub.sentence?.id))) throw new ShapeError(`sub-category ${sub.slug}`, "an overview sentence that covers it");
    if (sub.openQuestion && !questions.has(sub.openQuestion)) throw new ShapeError(`sub-category ${sub.slug}`, "an open question the page lists");
  }
  if (page.hero && !page.pictures.some((picture) => picture.media.id === page.hero?.media.id)) throw new ShapeError("hero", "one of the page's pictures");
}

export function checkedCategoryPage(page: CategoryPage): CategoryPage {
  if (page.curated !== (page.curation !== null)) throw new ShapeError("curation", "a header exactly when the page is curated");
  if (page.category.craftCount !== page.subCategories.reduce((sum, sub) => sum + sub.craftCount, 0)) throw new ShapeError("category.craftCount", "the sum of its sub-categories");
  once("subCategories", page.subCategories.map((sub) => sub.slug));
  checkClaimsAndSources(page);
  checkReferences(page);
  return page;
}

export function checkedCategoryList(listing: CategoryList): CategoryList {
  once("categories", listing.categories.map((category) => category.slug));
  once("sources", listing.sources.map((source) => source.id));
  for (const category of listing.categories) {
    if (category.craftCount !== category.subCategories.reduce((sum, sub) => sum + sub.craftCount, 0)) throw new ShapeError(`${category.slug}.craftCount`, "the sum of its sub-categories");
    if (!category.curated && (category.lede || category.hero)) throw new ShapeError(category.slug, "no lede and no hero until it is curated");
  }
  const cited = listing.categories.flatMap((category) => category.lede?.citations.map((citation) => citation.sourceId) ?? []);
  if (!sameSet(cited, listing.sources.map((source) => source.id))) throw new ShapeError("sources", "exactly the sources the ledes cite");
  return listing;
}

export function parseCategoryPage(raw: unknown): CategoryPage {
  return checkedCategoryPage(parseShape(categoryPageShape, raw));
}

export function parseCategoryList(raw: unknown): CategoryList {
  return checkedCategoryList(parseShape(categoryListShape, raw));
}

export async function fetchCategoryList(): Promise<CategoryList> {
  return parseCategoryList(await apiFetch<unknown>(CATEGORY_LIST_PATH));
}

export async function fetchCategoryPage(slug: string): Promise<CategoryPage> {
  return parseCategoryPage(await apiFetch<unknown>(CATEGORY_PAGE_PATH(slug)));
}
