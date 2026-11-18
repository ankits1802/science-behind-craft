"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, apiFetchWithHeaders } from "@/lib/api";
import {
  CRAFT_CATALOGUE_PATH,
  parseCraftCatalogue,
  type CatalogueConcept,
  type CatalogueCraft,
  type CraftCatalogue,
  type CraftCatalogueCategory,
  type CraftCatalogueSubCategory
} from "@/lib/craftCatalogueContract";

export const CRAFT_CATALOGUE_STORAGE_KEY = "kalavigyan_craft_catalogue_v2";

export const CRAFT_CATALOGUE_REVALIDATE_MS = 60_000;

export const CRAFT_NO_MATCH = (query: string) => `No craft matches “${query}”.`;
export const CRAFT_OFFLINE_FIRST_RUN = "Connect once to load the craft list.";
export const CRAFT_NOT_IN_LIST = "Pick a craft from the list.";
export const CRAFT_LIST_UNREADABLE = "The craft list could not be read.";

type Stored = { etag: string | null; fetchedAt: number; catalogue: CraftCatalogue };

export function foldCraftText(text: string | null | undefined): string {
  return (text ?? "")
    .normalize("NFKD")
    .replace(/\p{M}+/gu, "")
    .toLowerCase()
    .replace(/&/g, " and ")
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim()
    .replace(/\s+/g, " ");
}

export type CraftIndex = {
  catalogue: CraftCatalogue;
  byId: Map<string, CatalogueCraft>;
  bySlug: Map<string, CatalogueCraft>;
  subCategoryById: Map<string, CraftCatalogueSubCategory & { categoryId: string }>;
  categoryById: Map<string, CraftCatalogueCategory>;
  position: Map<string, number>;
};

const indexes = new WeakMap<CraftCatalogue, CraftIndex>();

export function craftIndex(catalogue: CraftCatalogue): CraftIndex {
  const cached = indexes.get(catalogue);
  if (cached) return cached;
  const byId = new Map<string, CatalogueCraft>();
  const bySlug = new Map<string, CatalogueCraft>();
  const position = new Map<string, number>();
  catalogue.crafts.forEach((craft, index) => {
    byId.set(craft.id, craft);
    bySlug.set(craft.slug, craft);
    position.set(craft.id, index);
  });
  const categoryById = new Map<string, CraftCatalogueCategory>();
  const subCategoryById = new Map<string, CraftCatalogueSubCategory & { categoryId: string }>();
  for (const category of catalogue.categories) {
    categoryById.set(category.id, category);
    for (const sub of category.subCategories) subCategoryById.set(sub.id, { ...sub, categoryId: category.id });
  }
  const built = { catalogue, byId, bySlug, subCategoryById, categoryById, position };
  indexes.set(catalogue, built);
  return built;
}

export function craftCategoryName(index: CraftIndex, craft: CatalogueCraft): string {
  const sub = craft.subCategoryId ? index.subCategoryById.get(craft.subCategoryId) : undefined;
  const categoryId = craft.categoryId ?? sub?.categoryId ?? null;
  const category = categoryId ? index.categoryById.get(categoryId) : undefined;
  return craft.familyLabel ?? category?.label ?? category?.name ?? "";
}

export function craftSubCategoryName(index: CraftIndex, craft: CatalogueCraft): string {
  const sub = craft.subCategoryId ? index.subCategoryById.get(craft.subCategoryId) : undefined;
  return craft.kindLabel ?? sub?.label ?? sub?.name ?? "";
}

export function craftPath(index: CraftIndex, craft: CatalogueCraft): string {
  const category = craftCategoryName(index, craft);
  const sub = craftSubCategoryName(index, craft);
  if (category && sub) return `${category} · ${sub}`;
  return category || sub || "Not on the list";
}

export function craftStatesLine(craft: CatalogueCraft): string {
  return craft.stateOfPractice.join(", ");
}

export function isReaderCraft(craft: CatalogueCraft): boolean {
  return (craft.status ?? "ACTIVE") === "ACTIVE" && !craft.isCatchAll;
}

export function readerCount(crafts: readonly CatalogueCraft[]): number {
  return crafts.filter(isReaderCraft).length;
}

export function craftSearchScore(index: CraftIndex, craft: CatalogueCraft, query: string): number | null {
  const q = foldCraftText(query);
  if (!q) return 0;
  const name = bestScore([craft.displayName, craft.name], q);
  if (name < 4) return name;
  const second = bestScore([craft.localName, craft.slug, ...craft.aliases], q);
  if (second < 4) return 10 + second;
  const third = bestScore([...craft.stateOfPractice, ...craft.stateOfOrigin, craftSubCategoryName(index, craft), craftCategoryName(index, craft)], q);
  if (third < 4) return 20 + third;
  const haystack = [
    craft.displayName,
    craft.name,
    craft.localName,
    craft.slug,
    ...craft.aliases,
    ...craft.stateOfPractice,
    ...craft.stateOfOrigin,
    craftSubCategoryName(index, craft),
    craftCategoryName(index, craft)
  ];
  return everyWord(haystack, q) ? 30 : null;
}

export function conceptSearchScore(concept: CatalogueConcept, query: string): number | null {
  const q = foldCraftText(query);
  if (!q) return null;
  const label = bestScore([concept.label], q);
  if (label < 4) return label;
  const named = bestScore(concept.names, q);
  if (named < 4) return 10 + named;
  return everyWord([concept.label, ...concept.names], q) ? 30 : null;
}

export type ConceptHit = { concept: CatalogueConcept; crafts: CatalogueCraft[] };

export type CatalogueSearch = { concepts: ConceptHit[]; crafts: CatalogueCraft[] };

export function searchCatalogue(catalogue: CraftCatalogue, query: string): CatalogueSearch {
  if (!foldCraftText(query)) return { concepts: [], crafts: catalogue.crafts.slice() };
  const index = craftIndex(catalogue);
  const concepts = matchingConcepts(catalogue, query).map((concept) => ({
    concept,
    crafts: concept.craftSlugs.map((slug) => index.bySlug.get(slug)).filter((craft): craft is CatalogueCraft => craft !== undefined)
  }));
  const found = matchingCrafts(index, query);
  const seen = new Set(found.map((craft) => craft.id));
  for (const craft of concepts.flatMap((hit) => hit.crafts)) {
    if (seen.has(craft.id)) continue;
    seen.add(craft.id);
    found.push(craft);
  }
  return { concepts, crafts: found };
}

export function withinCategory(found: CatalogueSearch, categoryId: string): CatalogueSearch {
  if (!categoryId) return found;
  const inCategory = (craft: CatalogueCraft) => craft.categoryId === categoryId;
  const concepts = found.concepts
    .map((hit) => ({ concept: hit.concept, crafts: hit.crafts.filter(inCategory) }))
    .filter((hit) => hit.crafts.length > 0);
  return { concepts, crafts: found.crafts.filter(inCategory) };
}

export type CraftGroup = { key: string; heading: string; crafts: CatalogueCraft[] };

export function groupCrafts(catalogue: CraftCatalogue, crafts: readonly CatalogueCraft[]): CraftGroup[] {
  const index = craftIndex(catalogue);
  const groups = new Map<string, CraftGroup>();
  for (const craft of crafts) {
    const key = craft.subCategoryId ?? craft.categoryId ?? "none";
    let group = groups.get(key);
    if (!group) {
      group = { key, heading: craftPath(index, craft), crafts: [] };
      groups.set(key, group);
    }
    group.crafts.push(craft);
  }
  return [...groups.values()];
}

export function findCraftByText(catalogue: CraftCatalogue, text: string | null | undefined): CatalogueCraft | null {
  const q = foldCraftText(text);
  if (!q) return null;
  const exact = catalogue.crafts.filter((craft) => [craft.name, craft.displayName, craft.slug].some((name) => foldCraftText(name) === q));
  if (exact.length === 1) return exact[0];
  if (exact.length > 1) return null;
  const alias = catalogue.crafts.filter((craft) => craft.aliases.some((a) => foldCraftText(a) === q));
  return alias.length === 1 ? alias[0] : null;
}

export function catalogueCountLine(catalogue: CraftCatalogue): string {
  const { crafts, giRegistered, states } = catalogue.summary;
  return `${crafts} ${crafts === 1 ? "craft" : "crafts"} · ${giRegistered} GI-registered · ${states} ${states === 1 ? "state" : "states"}`;
}

export function placedCountLine(catalogue: CraftCatalogue): string {
  const { placed, states } = catalogue.summary;
  return `${placed} ${placed === 1 ? "craft" : "crafts"} placed in ${states} ${states === 1 ? "state" : "states"}`;
}

export function shownCountLine(catalogue: CraftCatalogue, shown: readonly CatalogueCraft[]): string {
  const total = catalogue.summary.crafts;
  const line = `Showing ${readerCount(shown)} of ${total} ${total === 1 ? "craft" : "crafts"}`;
  const others = shown.filter((craft) => craft.isCatchAll).length;
  return others ? `${line} and ${others} “Other” ${others === 1 ? "entry" : "entries"}` : line;
}

function bestScore(texts: readonly (string | null | undefined)[], query: string): number {
  return Math.min(4, ...texts.map((text) => appSearchScore(foldCraftText(text), query)));
}

function everyWord(texts: readonly (string | null | undefined)[], query: string): boolean {
  const words = query.split(" ");
  if (words.length < 2) return false;
  const haystack = foldCraftText(texts.join(" "));
  return words.every((word) => haystack.includes(word));
}

function matchingCrafts(index: CraftIndex, query: string): CatalogueCraft[] {
  const scored: { craft: CatalogueCraft; score: number; at: number }[] = [];
  for (const craft of index.catalogue.crafts) {
    const score = craftSearchScore(index, craft, query);
    if (score === null) continue;
    scored.push({ craft, score, at: index.position.get(craft.id) ?? 0 });
  }
  scored.sort((a, b) => a.score - b.score || a.at - b.at);
  return scored.map((row) => row.craft);
}

function matchingConcepts(catalogue: CraftCatalogue, query: string): CatalogueConcept[] {
  const scored: { concept: CatalogueConcept; score: number; at: number }[] = [];
  catalogue.concepts.forEach((concept, at) => {
    const score = conceptSearchScore(concept, query);
    if (score !== null) scored.push({ concept, score, at });
  });
  scored.sort((a, b) => a.score - b.score || a.at - b.at);
  return scored.map((row) => row.concept);
}

let memory: Stored | null = null;
let inFlight: Promise<CraftCatalogue> | null = null;
const listeners = new Set<(catalogue: CraftCatalogue) => void>();

function readStored(): Stored | null {
  if (memory) return memory;
  try {
    if (typeof window === "undefined") return null;
    const text = window.localStorage.getItem(CRAFT_CATALOGUE_STORAGE_KEY);
    if (!text) return null;
    const parsed = JSON.parse(text) as Partial<Stored>;
    memory = { etag: typeof parsed.etag === "string" ? parsed.etag : null, fetchedAt: 0, catalogue: parseCraftCatalogue(parsed.catalogue) };
    return memory;
  } catch {
    return null;
  }
}

function writeStored(next: Stored) {
  memory = next;
  try {
    window.localStorage.setItem(CRAFT_CATALOGUE_STORAGE_KEY, JSON.stringify(next));
  } catch {
  }
  for (const listener of listeners) listener(next.catalogue);
}

function readCatalogue(body: unknown): CraftCatalogue {
  try {
    return parseCraftCatalogue(body);
  } catch (error) {
    console.error("craft catalogue off its contract", error);
    throw new Error(CRAFT_LIST_UNREADABLE);
  }
}

export function peekCraftCatalogue(): CraftCatalogue | null {
  return readStored()?.catalogue ?? null;
}

export function loadCraftCatalogue(options: { force?: boolean } = {}): Promise<CraftCatalogue> {
  const stored = readStored();
  if (stored && !options.force && Date.now() - stored.fetchedAt < CRAFT_CATALOGUE_REVALIDATE_MS) {
    return Promise.resolve(stored.catalogue);
  }
  if (inFlight) return inFlight;
  const headers: Record<string, string> = {};
  if (stored?.etag) headers["If-None-Match"] = stored.etag;
  inFlight = apiFetchWithHeaders<unknown>(CRAFT_CATALOGUE_PATH, { headers })
    .then(({ body, headers: answer }) => {
      const catalogue = readCatalogue(body);
      writeStored({ etag: answer.get("etag"), fetchedAt: Date.now(), catalogue });
      return catalogue;
    })
    .catch((error: unknown) => {
      if (stored && error instanceof ApiError && error.status === 304) {
        writeStored({ ...stored, fetchedAt: Date.now() });
        return stored.catalogue;
      }
      if (stored) return stored.catalogue;
      if (error instanceof Error && error.message === CRAFT_LIST_UNREADABLE) throw error;
      if (!(error instanceof ApiError)) throw new Error(CRAFT_OFFLINE_FIRST_RUN);
      throw error;
    })
    .finally(() => {
      inFlight = null;
    });
  return inFlight;
}

export function invalidateCraftCatalogue() {
  if (memory) memory = { ...memory, fetchedAt: 0 };
}

export async function loadFullCraftCatalogue(): Promise<CraftCatalogue> {
  const { body } = await apiFetchWithHeaders<unknown>(`${CRAFT_CATALOGUE_PATH}?includeInactive=true`);
  return readCatalogue(body);
}

export type CraftCatalogueState = {
  catalogue: CraftCatalogue | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
};

export function useCraftCatalogue(): CraftCatalogueState {
  const [catalogue, setCatalogue] = useState<CraftCatalogue | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const run = useCallback((force: boolean) => {
    let cancelled = false;
    setLoading(true);
    loadCraftCatalogue({ force })
      .then((next) => {
        if (cancelled) return;
        setCatalogue(next);
        setError(null);
      })
      .catch((reason: unknown) => {
        if (cancelled) return;
        setError(reason instanceof Error ? reason.message : CRAFT_OFFLINE_FIRST_RUN);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const listener = (next: CraftCatalogue) => setCatalogue(next);
    listeners.add(listener);
    const stored = peekCraftCatalogue();
    if (stored) setCatalogue(stored);
    const cancel = run(false);
    return () => {
      listeners.delete(listener);
      cancel();
    };
  }, [run]);

  const reload = useCallback(() => {
    run(true);
  }, [run]);

  return { catalogue, error, loading, reload };
}

export function appSearchScore(title: string, query: string): number {
  const t = title.trim().toLowerCase();
  const q = query.trim().toLowerCase();
  if (!q) return 4;
  if (t === q) return 0;
  if (t.startsWith(q)) return 1;
  if (t.split(/[^\p{L}\p{N}]+/u).some((word) => word && word.startsWith(q))) return 2;
  if (t.includes(q)) return 3;
  return 4;
}
