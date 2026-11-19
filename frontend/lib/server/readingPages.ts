import { cache } from "react";

import { CRAFT_CATALOGUE_PATH, parseCraftCatalogue, type CraftCatalogue } from "@/lib/craftCatalogueContract";
import { CRAFT_PAGE_PATH, checkedCraftPage, craftPageShape, type CraftPage } from "@/lib/craftPageContract";
import { publicFetch } from "@/lib/server/serverFetch";
import { parseShape } from "@/lib/shape";
import { SITE_PAGES_PATH, STATIC_PAGE_REVALIDATE_SECONDS, parseStaticPages, type StaticPages } from "@/lib/sitePagesContract";

export const CRAFT_CATALOGUE_TAG = "craft-catalogue";
export const STATIC_PAGES_TAG = "static-pages";
export const STATIC_FETCH_TIMEOUT_MS = 10_000;
export const craftPageTag = (slug: string) => `craft-page:${slug}`;

export const serverCraftPage = cache(async (slug: string, version?: number): Promise<CraftPage | null> => {
  const result = await publicFetch(CRAFT_PAGE_PATH(slug, version), {
    parse: (body) => checkedCraftPage(parseShape(craftPageShape, body)),
    tags: [craftPageTag(slug)],
    revalidateSeconds: STATIC_PAGE_REVALIDATE_SECONDS,
    deps: { timeoutMs: STATIC_FETCH_TIMEOUT_MS }
  });
  return result.ok ? result.body : null;
});

export const serverCraftCatalogue = cache(async (): Promise<CraftCatalogue | null> => {
  const result = await publicFetch(CRAFT_CATALOGUE_PATH, { parse: parseCraftCatalogue, tags: [CRAFT_CATALOGUE_TAG] });
  return result.ok ? result.body : null;
});

export async function serverStaticPages(): Promise<StaticPages | null> {
  const result = await publicFetch(SITE_PAGES_PATH, {
    parse: parseStaticPages,
    tags: [STATIC_PAGES_TAG],
    revalidateSeconds: STATIC_PAGE_REVALIDATE_SECONDS,
    deps: { timeoutMs: STATIC_FETCH_TIMEOUT_MS }
  });
  return result.ok ? result.body : null;
}
