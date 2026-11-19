import { isMonograph, readerCrafts } from "@/lib/atlasCollection";
import { shownName, type NamedCraft } from "@/lib/atlasNames";
import type { CatalogueCraft, CraftCatalogue } from "@/lib/craftCatalogueContract";
import { serverCraftPage } from "@/lib/server/readingPages";

async function namedCraft(craft: CatalogueCraft): Promise<NamedCraft | null> {
  const page = await serverCraftPage(craft.slug);
  const nativeName = shownName(page?.masthead.nativeName ?? null);
  if (!nativeName) return null;
  const state = craft.stateOfOrigin[0] ?? craft.stateOfPractice[0] ?? "";
  return { slug: craft.slug, englishName: craft.displayName, state, nativeName };
}

export async function serverAtlasNames(catalogue: CraftCatalogue | null): Promise<NamedCraft[]> {
  if (!catalogue) return [];
  const curated = readerCrafts(catalogue).filter(isMonograph);
  const found = await Promise.all(curated.map((craft) => namedCraft(craft).catch(() => null)));
  return found.filter((named): named is NamedCraft => named !== null);
}
