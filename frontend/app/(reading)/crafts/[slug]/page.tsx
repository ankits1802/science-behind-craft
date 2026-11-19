import type { Metadata } from "next";
import { Suspense } from "react";

import { CraftScreen } from "@/components/craft/CraftScreen";
import { MonographHandover } from "@/components/craft/MonographHandover";
import { isCraftMonograph } from "@/lib/craftMonographs";
import { craftPageMetadata } from "@/lib/readingMetadata";
import { serverCraftPage, serverStaticPages } from "@/lib/server/readingPages";
import { staticCraftParams, type CraftParams } from "@/lib/sitePagesContract";

type CraftRoute = { params: Promise<{ slug: string }> };

export const revalidate = 86400;
export const dynamicParams = true;

export async function generateStaticParams(): Promise<CraftParams[]> {
  return staticCraftParams(await serverStaticPages(), isCraftMonograph);
}

export async function generateMetadata({ params }: CraftRoute): Promise<Metadata> {
  const { slug } = await params;
  if (isCraftMonograph(slug)) return {};
  return craftPageMetadata(await serverCraftPage(slug));
}

export default async function CraftPage({ params }: CraftRoute) {
  const { slug } = await params;
  if (isCraftMonograph(slug)) return <MonographHandover />;
  const initial = await serverCraftPage(slug);
  return (
    <Suspense fallback={null}>
      <CraftScreen slug={slug} initial={initial} />
    </Suspense>
  );
}
