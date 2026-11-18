import { cache } from "react";

import { CRAFT_CATALOGUE_PATH, parseCraftCatalogue, type CraftCatalogue } from "@/lib/craftCatalogueContract";
import { CRAFT_PAGE_PATH, checkedCraftPage, craftPageShape, type CraftPage } from "@/lib/craftPageContract";
import { publicFetch } from "@/lib/server/serverFetch";
import { parseShape } from "@/lib/shape";

export const CRAFT_CATALOGUE_TAG = "craft-catalogue";
export const craftPageTag = (slug: string) => `craft-page:${slug}`;

export const serverCraftPage = cache(async (slug: string, version?: number): Promise<CraftPage | null> => {
  const result = await publicFetch(CRAFT_PAGE_PATH(slug, version), {
    parse: (body) => checkedCraftPage(parseShape(craftPageShape, body)),
    tags: [craftPageTag(slug)]
  });
  return result.ok ? result.body : null;
});

export const serverCraftCatalogue = cache(async (): Promise<CraftCatalogue | null> => {
  const result = await publicFetch(CRAFT_CATALOGUE_PATH, { parse: parseCraftCatalogue, tags: [CRAFT_CATALOGUE_TAG] });
  return result.ok ? result.body : null;
});
