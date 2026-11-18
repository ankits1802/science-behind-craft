import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { categoryClaimIds, overviewSentences, parseCategoryList, parseCategoryPage, type CategoryList, type CategoryPage } from "@/lib/categoryContract";
import { ShapeError } from "@/lib/shape";

const SHARED = join(__dirname, "..", "..", "shared");
const OUTSIDE = "00000000-0000-4000-8000-000000000001";

function golden<T>(name: string): T {
  return JSON.parse(readFileSync(join(SHARED, name), "utf8")) as T;
}

const curated = (): CategoryPage => golden<CategoryPage>("category.page.golden.json");
const uncurated = (): CategoryPage => golden<CategoryPage>("category.page.not-curated.golden.json");
const listing = (): CategoryList => golden<CategoryList>("category.list.golden.json");

function refusedPage(edit: (page: CategoryPage) => void): () => CategoryPage {
  return () => {
    const page = curated();
    edit(page);
    return parseCategoryPage(page);
  };
}

test("the three category goldens parse exactly as the backend wrote them", () => {
  expect(parseCategoryPage(curated())).toEqual(curated());
  expect(parseCategoryPage(uncurated())).toEqual(uncurated());
  expect(parseCategoryList(listing())).toEqual(listing());
});

test("the curated Leather page cites every sentence and numbers its sources from one", () => {
  const page = parseCategoryPage(curated());
  expect([page.category.label, page.category.craftCount, page.curation?.coverage]).toEqual(["Leather", 6, "THIN"]);
  expect(page.subCategories.map((sub) => [sub.slug, sub.craftCount, sub.sentence?.id === page.overview.lede[1].id])).toEqual([
    ["Leather-Footwear", 3, true],
    ["Leather-Other-Articles", 3, true]
  ]);
  expect(page.sources.map((source) => source.number)).toEqual(page.sources.map((_, index) => index + 1));
  expect(new Set(categoryClaimIds(page))).toEqual(new Set(page.claims.map((claim) => claim.id)));
  expect(overviewSentences(page).every((sentence) => sentence.claimIds.length > 0)).toBe(true);
  expect(page.hero?.media.id).toBe(page.pictures[0].media.id);
});

test("a category without a dossier lists its sub-categories and counts only", () => {
  const page = parseCategoryPage(uncurated());
  expect([page.curated, page.curation, page.hero, page.claims.length, page.sources.length]).toEqual([false, null, null, 0, 0]);
  expect(page.subCategories.map((sub) => sub.slug)).toEqual(["Paper-Crafts"]);
});

test("the list counts all nine categories and quotes a lede only for a curated one", () => {
  const list = parseCategoryList(listing());
  expect(list.categories).toHaveLength(9);
  expect(list.categories.filter((category) => category.lede).map((category) => category.slug)).toEqual(["Leather-Craft-Category"]);
  expect(list.sources.length).toBeGreaterThan(0);
});

test("the client refuses a page that names what it does not list", () => {
  expect(refusedPage((page) => (page.overview.keyFacts[0].claimIds = [OUTSIDE]))).toThrow(ShapeError);
  expect(refusedPage((page) => (page.claims[0].citations[0].sourceId = OUTSIDE))).toThrow(/sources/);
  expect(refusedPage((page) => (page.sources[0].number = 2))).toThrow(/number 1/);
  expect(refusedPage((page) => page.overview.lede[1].crafts.push("Kutch-Ajrakh"))).toThrow(/crafts and sub-categories/);
  expect(refusedPage((page) => (page.subCategories[0].craftCount = 4))).toThrow(ShapeError);
  expect(refusedPage((page) => (page.subCategories[0].openQuestion = "O09"))).toThrow(/open question/);
  expect(refusedPage((page) => (page.curation = null))).toThrow(/header/);
});

test("the client refuses a list that quotes an uncurated category or an uncited source", () => {
  const extra = listing();
  extra.sources.push({ ...extra.sources[0], id: OUTSIDE });
  expect(() => parseCategoryList(extra)).toThrow(/ledes cite/);
  const borrowed = listing();
  const leather = borrowed.categories.find((category) => category.curated);
  borrowed.categories[0] = { ...borrowed.categories[0], curated: false, lede: leather?.lede ?? null };
  expect(() => parseCategoryList(borrowed)).toThrow(/no lede/);
});
