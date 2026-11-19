import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { CraftWithoutMonograph } from "@/components/craft/CraftWithoutMonograph";
import { MonographHandover } from "@/components/craft/MonographHandover";
import { MonographPage } from "@/components/monograph/MonographPage";
import { isCraftMonograph } from "@/lib/craftMonographs";
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
  return staticCraftParams(await serverStaticPages(), isCraftMonograph);
}

export async function generateMetadata({ params }: CraftRoute): Promise<Metadata> {
  const { slug } = await params;
  if (isCraftMonograph(slug)) return {};
  const document = await serverCraftDocument(slug);
  if (document) return monographMetadata(document);
  return craftPageMetadata(await serverCraftPage(slug));
}

export default async function CraftPage({ params }: CraftRoute) {
  const { slug } = await params;
  if (isCraftMonograph(slug)) return <MonographHandover />;
  const document = await serverCraftDocument(slug);
  if (document) return <MonographPage document={document} />;
  const record = await serverCraftPage(slug);
  if (!record) notFound();
  return <CraftWithoutMonograph record={craftRecordView(record)} />;
}
