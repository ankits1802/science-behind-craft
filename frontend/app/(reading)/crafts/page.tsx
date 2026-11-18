import type { Metadata } from "next";
import { Suspense } from "react";

import { CraftAtlas, CraftAtlasHeader } from "@/components/crafts/CraftAtlas";
import { atlasMetadata } from "@/lib/readingMetadata";
import { serverCraftCatalogue } from "@/lib/server/readingPages";

export async function generateMetadata(): Promise<Metadata> {
  return atlasMetadata(await serverCraftCatalogue());
}

export default async function CraftsPage() {
  const initial = await serverCraftCatalogue();
  return (
    <Suspense fallback={<CraftAtlasHeader />}>
      <CraftAtlas initial={initial} />
    </Suspense>
  );
}
