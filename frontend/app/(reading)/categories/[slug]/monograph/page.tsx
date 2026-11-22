import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { MonographPage } from "@/components/monograph/MonographPage";
import { previewMetadata, previewStaticParams, serverMonographDocument } from "@/lib/monographRenderServer";
import type { CraftParams } from "@/lib/sitePagesContract";

type CategoryMonographRoute = { params: Promise<{ slug: string }> };

export const revalidate = 604800;
export const dynamicParams = true;

export async function generateStaticParams(): Promise<CraftParams[]> {
  return previewStaticParams("category");
}

export async function generateMetadata({ params }: CategoryMonographRoute): Promise<Metadata> {
  const { slug } = await params;
  return previewMetadata("category", slug);
}

export default async function CategoryMonographPreview({ params }: CategoryMonographRoute) {
  const { slug } = await params;
  const document = await serverMonographDocument("category", slug);
  if (!document) notFound();
  return <MonographPage document={document} />;
}
