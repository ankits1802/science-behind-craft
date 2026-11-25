"use client";

import type { RefObject } from "react";

import { DownloadList, type DownloadItem } from "@/components/learn/DownloadList";
import { downloadExportFile, FILE_FAILED } from "@/lib/lessonApi";
import { PAGE_DOWNLOAD_LABEL, PAGE_DOWNLOAD_TEST_ID, pageDownloads, type PageSubject } from "@/lib/pageExport";

export type PageDownloadListProps = { subject: PageSubject; open: boolean; onClose: () => void; anchorRef: RefObject<HTMLButtonElement | null> };

export function pageDownloadItems(subject: PageSubject): DownloadItem[] {
  return pageDownloads(subject).map((link) => ({ key: link.key, label: link.label, run: () => downloadExportFile(link.path) }));
}

export function PageDownloadList({ subject, open, onClose, anchorRef }: PageDownloadListProps) {
  return <DownloadList label={PAGE_DOWNLOAD_LABEL} items={pageDownloadItems(subject)} failure={FILE_FAILED} testId={PAGE_DOWNLOAD_TEST_ID} open={open} onClose={onClose} anchorRef={anchorRef} />;
}
