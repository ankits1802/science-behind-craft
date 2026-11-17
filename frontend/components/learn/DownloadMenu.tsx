"use client";

import { useRef, useState } from "react";
import { ChevronDown, Download, Loader2 } from "lucide-react";

import { AnchoredPopover } from "@/components/ui/AnchoredPopover";
import { apiErrorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

export type DownloadItem = { key: string; label: string; group?: string; run: () => Promise<unknown> };

const ITEM =
  "flex min-h-11 w-full items-center gap-2 rounded-md px-3 text-left text-sm font-medium text-ink-900 transition hover:bg-purple-50 hover:text-purple-800 disabled:opacity-60 dark:hover:bg-purple-950/40 dark:hover:text-purple-200";

export function DownloadMenu({ label, items, failure, testId, className }: { label: string; items: readonly DownloadItem[]; failure: string; testId: string; className?: string }) {
  const anchor = useRef<HTMLButtonElement | null>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function pick(item: DownloadItem) {
    setBusy(item.key);
    setError(null);
    try {
      await item.run();
      setOpen(false);
    } catch (cause) {
      setError(apiErrorMessage(cause, failure));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className={cn("grid min-w-0 justify-items-start gap-1", className)} data-testid={testId}>
      <button ref={anchor} type="button" className="field-button-secondary min-h-10 rounded-full px-4" aria-expanded={open} aria-haspopup="dialog" onClick={() => setOpen((value) => !value)}>
        <Download className="h-4 w-4" aria-hidden />
        {label}
        <ChevronDown className="h-3.5 w-3.5" aria-hidden />
      </button>
      <AnchoredPopover open={open} onClose={() => setOpen(false)} anchorRef={anchor} label={label} maxWidth={320} className="w-72 p-2">
        <ul className="grid gap-0.5" data-testid={`${testId}-items`}>
          {items.map((item, index) => (
            <li key={item.key} className={cn(item.group && item.group !== items[index - 1]?.group && "mt-1.5 border-t border-line-200 pt-1.5")}>
              {item.group && item.group !== items[index - 1]?.group ? <p className="field-label px-3 pb-1">{item.group}</p> : null}
              <button type="button" className={ITEM} disabled={busy !== null} onClick={() => void pick(item)} data-testid="download-item">
                {busy === item.key ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" aria-hidden /> : <Download className="h-4 w-4 text-ink-500" aria-hidden />}
                {item.label}
              </button>
            </li>
          ))}
        </ul>
        {error ? (
          <p role="alert" className="mt-2 rounded-md bg-error-100 px-3 py-2 text-xs text-error-600">
            {error}
          </p>
        ) : null}
      </AnchoredPopover>
    </div>
  );
}
