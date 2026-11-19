import type { Metadata } from "next";
import { cache } from "react";

import type { MonographDocument } from "@/lib/monographDocument";
import { monographDocumentPath, parseMonographDocument, versionedDocumentPath, type MonographPreviewSubject } from "@/lib/monographDocumentShape";
import { serverStaticPages, STATIC_FETCH_TIMEOUT_MS } from "@/lib/server/readingPages";
import { publicFetch } from "@/lib/server/serverFetch";
import { STATIC_PAGE_REVALIDATE_SECONDS, type CraftParams, type StaticPages } from "@/lib/sitePagesContract";

export const PREVIEW_ROBOTS = { index: false, follow: false } as const;
export const PREVIEW_TITLE = "Monograph";
export const DOCUMENT_UNAVAILABLE = "The monograph could not be read";
const NOT_FOUND = 404;

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

export const serverCraftDocument = cache(async (slug: string, version: number | null = null): Promise<MonographDocument | null> => {
  const result = await publicFetch(versionedDocumentPath(monographDocumentPath("craft", slug), version), {
    parse: parseMonographDocument,
    tags: [monographDocumentTag("craft", slug)],
    revalidateSeconds: STATIC_PAGE_REVALIDATE_SECONDS,
    deps: { timeoutMs: STATIC_FETCH_TIMEOUT_MS }
  });
  if (result.ok) return result.body;
  if (result.status === NOT_FOUND) return null;
  throw new Error(`${DOCUMENT_UNAVAILABLE}: ${result.failure}`);
});
