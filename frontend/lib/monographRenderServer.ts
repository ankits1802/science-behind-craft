import type { Metadata } from "next";
import { cache } from "react";

import type { MonographDocument } from "@/lib/monographDocument";
import { monographDocumentPath, parseMonographDocument, type MonographPreviewSubject } from "@/lib/monographDocumentShape";
import { serverStaticPages, STATIC_FETCH_TIMEOUT_MS } from "@/lib/server/readingPages";
import { publicFetch } from "@/lib/server/serverFetch";
import { STATIC_PAGE_REVALIDATE_SECONDS, type CraftParams, type StaticPages } from "@/lib/sitePagesContract";

export const PREVIEW_ROBOTS = { index: false, follow: false } as const;
export const PREVIEW_TITLE = "Monograph";

export function previewParams(pages: StaticPages | null, subject: MonographPreviewSubject): CraftParams[] {
  if (!pages) return [];
  const slugs = subject === "craft" ? pages.crafts : pages.categories;
  return [...new Set(slugs)].map((slug) => ({ slug }));
}

export async function previewStaticParams(subject: MonographPreviewSubject): Promise<CraftParams[]> {
  return previewParams(await serverStaticPages(), subject);
}

export async function previewMetadata(subject: MonographPreviewSubject, slug: string): Promise<Metadata> {
  const document = await serverMonographDocument(subject, slug);
  return { title: document?.title ?? PREVIEW_TITLE, robots: PREVIEW_ROBOTS };
}

export const monographDocumentTag = (subject: MonographPreviewSubject, slug: string) => `monograph-document:${subject}:${slug}`;

export const serverMonographDocument = cache(async (subject: MonographPreviewSubject, slug: string): Promise<MonographDocument | null> => {
  const result = await publicFetch(monographDocumentPath(subject, slug), {
    parse: parseMonographDocument,
    tags: [monographDocumentTag(subject, slug)],
    revalidateSeconds: STATIC_PAGE_REVALIDATE_SECONDS,
    deps: { timeoutMs: STATIC_FETCH_TIMEOUT_MS }
  });
  return result.ok ? result.body : null;
});
