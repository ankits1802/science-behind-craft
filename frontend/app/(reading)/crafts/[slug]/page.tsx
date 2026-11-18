import type { Metadata } from "next";
import { Suspense } from "react";

import { CraftScreen } from "@/components/craft/CraftScreen";
import { craftPageMetadata } from "@/lib/readingMetadata";
import { serverCraftPage } from "@/lib/server/readingPages";

type CraftRoute = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: CraftRoute): Promise<Metadata> {
  const { slug } = await params;
  return craftPageMetadata(await serverCraftPage(slug));
}

export default async function CraftPage({ params }: CraftRoute) {
  const { slug } = await params;
  const initial = await serverCraftPage(slug);
  return (
    <Suspense fallback={null}>
      <CraftScreen slug={slug} initial={initial} />
    </Suspense>
  );
}
