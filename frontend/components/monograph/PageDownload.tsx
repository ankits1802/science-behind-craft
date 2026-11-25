"use client";

import { useRef, useState, type ComponentType } from "react";
import { AlertCircle } from "lucide-react";

import { DownloadTrigger } from "@/components/learn/DownloadTrigger";
import type { PageDownloadListProps } from "@/components/monograph/PageDownloadList";
import { PAGE_DOWNLOAD_BUSY, PAGE_DOWNLOAD_FAILED, PAGE_DOWNLOAD_LABEL, PAGE_DOWNLOAD_TEST_ID, type PageSubject } from "@/lib/pageExport";

type ListView = ComponentType<PageDownloadListProps>;
type ListState = { status: "rest" | "opening" | "failed"; List: ListView | null };

export const PAGE_DOWNLOAD_FAILED_TEST_ID = "page-download-failed";

const AT_REST: ListState = { status: "rest", List: null };

const loadList = (): Promise<ListView> => import("@/components/monograph/PageDownloadList").then((list) => list.PageDownloadList);

export function PageDownloadFailed() {
  return (
    <p role="alert" className="inline-flex items-start gap-2 font-ui text-label text-ink-1" data-testid={PAGE_DOWNLOAD_FAILED_TEST_ID}>
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-error" aria-hidden />
      {PAGE_DOWNLOAD_FAILED}
    </p>
  );
}

export function PageDownload({ subject }: { subject: PageSubject }) {
  const anchor = useRef<HTMLButtonElement | null>(null);
  const [open, setOpen] = useState(false);
  const [list, setList] = useState<ListState>(AT_REST);

  function press() {
    if (list.List) {
      setOpen((value) => !value);
      return;
    }
    setList({ status: "opening", List: null });
    loadList().then(
      (List) => {
        setList({ status: "rest", List });
        setOpen(true);
      },
      (cause: unknown) => {
        console.error(cause);
        setList({ status: "failed", List: null });
      }
    );
  }

  return (
    <>
      <DownloadTrigger ref={anchor} label={PAGE_DOWNLOAD_LABEL} busy={list.status === "opening"} busyLabel={PAGE_DOWNLOAD_BUSY} open={open} onToggle={press} testId={PAGE_DOWNLOAD_TEST_ID} />
      {list.List ? <list.List subject={subject} open={open} onClose={() => setOpen(false)} anchorRef={anchor} /> : null}
      {list.status === "failed" ? <PageDownloadFailed /> : null}
    </>
  );
}
