"use client";

import { useRef, useState } from "react";

import { DownloadList, type DownloadItem } from "@/components/learn/DownloadList";
import { DownloadTrigger } from "@/components/learn/DownloadTrigger";
import { cn } from "@/lib/utils";

export type { DownloadItem };

export function DownloadMenu({ label, items, failure, testId, className }: { label: string; items: readonly DownloadItem[]; failure: string; testId: string; className?: string }) {
  const anchor = useRef<HTMLButtonElement | null>(null);
  const [open, setOpen] = useState(false);
  return (
    <div className={cn("grid min-w-0 justify-items-start gap-1", className)} data-testid={testId}>
      <DownloadTrigger ref={anchor} label={label} open={open} onToggle={() => setOpen((value) => !value)} />
      <DownloadList label={label} items={items} failure={failure} testId={testId} open={open} onClose={() => setOpen(false)} anchorRef={anchor} />
    </div>
  );
}
