import type { Metadata } from "next";
import { Suspense } from "react";

import { CraftScreen } from "@/components/craft/CraftScreen";
import { CraftWithoutMonograph } from "@/components/craft/CraftWithoutMonograph";
import { MonographPage } from "@/components/monograph/MonographPage";
import { craftRecordView } from "@/lib/craftRecord";
import { monographMetadata } from "@/lib/monographMetadata";
import { serverCraftDocument } from "@/lib/monographRenderServer";
import { craftPageMetadata } from "@/lib/readingMetadata";
import { serverCraftPage, serverStaticPages } from "@/lib/server/readingPages";
import { staticCraftParams, type CraftParams } from "@/lib/sitePagesContract";

type CraftRoute = { params: Promise<{ slug: string }> };

export const revalidate = 86400;
export const dynamicParams = true;

export async function generateStaticParams(): Promise<CraftParams[]> {
  return staticCraftParams(await serverStaticPages());
}

export async function generateMetadata({ params }: CraftRoute): Promise<Metadata> {
  const { slug } = await params;
  const document = await serverCraftDocument(slug);
  if (document) return monographMetadata(document);
  return craftPageMetadata(await serverCraftPage(slug));
}

export default async function CraftPage({ params }: CraftRoute) {
  const { slug } = await params;
  const document = await serverCraftDocument(slug);
  if (document) return <MonographPage document={document} />;
  const page = await serverCraftPage(slug);
  if (page && !page.curated) return <CraftWithoutMonograph record={craftRecordView(page)} />;
  return (
    <Suspense fallback={null}>
      <CraftScreen slug={slug} initial={page} />
    </Suspense>
  );
}
