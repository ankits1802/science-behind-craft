import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { CraftScreen } from "@/components/craft/CraftScreen";
import { craftEdition } from "@/lib/craftPageContract";
import { craftPageMetadata } from "@/lib/readingMetadata";
import { serverCraftPage } from "@/lib/server/readingPages";

type CraftEditionRoute = { params: Promise<{ slug: string; edition: string }> };

async function editionOf(params: CraftEditionRoute["params"]): Promise<{ slug: string; version: number }> {
  const { slug, edition } = await params;
  const version = craftEdition(edition);
  if (version === null) notFound();
  return { slug, version };
}

export async function generateMetadata({ params }: CraftEditionRoute): Promise<Metadata> {
  const { slug, version } = await editionOf(params);
  return craftPageMetadata(await serverCraftPage(slug, version));
}

export default async function CraftEditionPage({ params }: CraftEditionRoute) {
  const { slug, version } = await editionOf(params);
  const initial = await serverCraftPage(slug, version);
  if (!initial) notFound();
  return (
    <Suspense fallback={null}>
      <CraftScreen slug={slug} initial={initial} version={version} />
    </Suspense>
  );
}
