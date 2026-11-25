"use client";

import dynamic from "next/dynamic";
import { useRef, useState } from "react";

import { DownloadTrigger } from "@/components/learn/DownloadTrigger";
import { PAGE_DOWNLOAD_LABEL, PAGE_DOWNLOAD_TEST_ID, type PageSubject } from "@/lib/pageExport";

const PageDownloadList = dynamic(() => import("@/components/monograph/PageDownloadList").then((list) => list.PageDownloadList), { ssr: false });

export function PageDownload({ subject }: { subject: PageSubject }) {
  const anchor = useRef<HTMLButtonElement | null>(null);
  const [open, setOpen] = useState(false);
  const [asked, setAsked] = useState(false);

  function toggle() {
    setAsked(true);
    setOpen((value) => !value);
  }

  return (
    <>
      <DownloadTrigger ref={anchor} label={PAGE_DOWNLOAD_LABEL} open={open} onToggle={toggle} testId={PAGE_DOWNLOAD_TEST_ID} />
      {asked ? <PageDownloadList subject={subject} open={open} onClose={() => setOpen(false)} anchorRef={anchor} /> : null}
    </>
  );
}
