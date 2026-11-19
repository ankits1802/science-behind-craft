import type { Metadata } from "next";
import { Suspense } from "react";

import { CraftAtlas, CraftAtlasHeader } from "@/components/crafts/CraftAtlas";
import { atlasDek } from "@/lib/atlasIndex";
import { serverAtlasNames } from "@/lib/atlasNamesServer";
import { atlasMetadata } from "@/lib/readingMetadata";
import { serverCraftCatalogue } from "@/lib/server/readingPages";

export async function generateMetadata(): Promise<Metadata> {
  return atlasMetadata(await serverCraftCatalogue());
}

export default async function CraftsPage() {
  const initial = await serverCraftCatalogue();
  const names = await serverAtlasNames(initial);
  return (
    <Suspense fallback={<CraftAtlasHeader dek={initial ? atlasDek(initial) : null} />}>
      <CraftAtlas initial={initial} names={names} />
    </Suspense>
  );
}
