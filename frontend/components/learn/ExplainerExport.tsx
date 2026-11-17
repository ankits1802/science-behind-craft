"use client";

import { DownloadMenu, type DownloadItem } from "@/components/learn/DownloadMenu";
import type { ExplainerRef } from "@/lib/explainerState";
import { downloadCitations, downloadExplainerPdf, FILE_FAILED } from "@/lib/lessonApi";
import { CITATION_FORMAT_LABEL, CITATION_FORMAT_ORDER } from "@/lib/lessonView";

const CITATIONS_GROUP = "Citations";

function citationItems(ref: ExplainerRef): DownloadItem[] {
  return CITATION_FORMAT_ORDER.map((format) => ({
    key: format,
    label: CITATION_FORMAT_LABEL[format],
    group: CITATIONS_GROUP,
    run: () => downloadCitations(ref.explainerId, ref.version, format)
  }));
}

export function ExplainerExport({ explainer }: { explainer: ExplainerRef }) {
  const items: DownloadItem[] = [
    { key: "pdf", label: "Report as PDF", group: "Report", run: () => downloadExplainerPdf(explainer.explainerId, explainer.version) },
    ...citationItems(explainer)
  ];
  return <DownloadMenu label="Export" items={items} failure={FILE_FAILED} testId="explainer-export" />;
}

export function CitationMenu({ explainer }: { explainer: ExplainerRef }) {
  return <DownloadMenu label={CITATIONS_GROUP} items={citationItems(explainer)} failure={FILE_FAILED} testId="citation-menu" />;
}
