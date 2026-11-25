import { ENGLISH, type MonographDocument } from "@/lib/monographDocument";

export const PAGE_EXPORT_FORMATS = ["pdf", "docx"] as const;
export const PAGE_DOWNLOAD_LABEL = "Download";
export const PAGE_DOWNLOAD_TEST_ID = "page-download";

export type PageExportFormat = (typeof PAGE_EXPORT_FORMATS)[number];
export type PageSubject = Pick<MonographDocument, "subjectKind" | "subjectSlug" | "language">;
export type PageDownloadLink = { key: PageExportFormat; label: string; path: string };

export const PAGE_EXPORT_LABEL: Readonly<Record<PageExportFormat, string>> = { pdf: "PDF", docx: "Word document" };

const SUBJECT_ROOTS: Readonly<Record<PageSubject["subjectKind"], string>> = { craft: "crafts", family: "families", category: "categories" };

export function pageSubject(document: PageSubject): PageSubject {
  return { subjectKind: document.subjectKind, subjectSlug: document.subjectSlug, language: document.language };
}

export function pageExportPath(subject: PageSubject, format: PageExportFormat): string {
  const path = `/${SUBJECT_ROOTS[subject.subjectKind]}/${encodeURIComponent(subject.subjectSlug)}/monograph/${format}`;
  return subject.language === ENGLISH ? path : `${path}?${new URLSearchParams({ lang: subject.language })}`;
}

export function pageDownloads(subject: PageSubject): PageDownloadLink[] {
  return PAGE_EXPORT_FORMATS.map((format) => ({ key: format, label: PAGE_EXPORT_LABEL[format], path: pageExportPath(subject, format) }));
}
