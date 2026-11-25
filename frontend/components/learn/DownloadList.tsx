"use client";

import { useState, type RefObject } from "react";
import { Download, Loader2 } from "lucide-react";

import { FormAlert } from "@/components/auth/FormAlert";
import { AnchoredPopover } from "@/components/ui/AnchoredPopover";
import { apiErrorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

export type DownloadItem = { key: string; label: string; group?: string; run: () => Promise<unknown> };

export type DownloadListProps = {
  label: string;
  items: readonly DownloadItem[];
  failure: string;
  testId: string;
  open: boolean;
  onClose: () => void;
  anchorRef: RefObject<HTMLButtonElement | null>;
};

const ITEM =
  "flex min-h-11 w-full items-center gap-2 rounded-control px-3 text-start font-ui text-ui text-ink-1 transition-colors duration-state hover:bg-sunk hover:text-indigo-hover disabled:cursor-not-allowed disabled:text-ink-3";

function startsGroup(items: readonly DownloadItem[], index: number): boolean {
  const group = items[index].group;
  return Boolean(group) && group !== items[index - 1]?.group;
}

export function DownloadList({ label, items, failure, testId, open, onClose, anchorRef }: DownloadListProps) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function pick(item: DownloadItem) {
    setBusy(item.key);
    setError(null);
    try {
      await item.run();
      onClose();
    } catch (cause) {
      setError(apiErrorMessage(cause, failure));
    } finally {
      setBusy(null);
    }
  }

  return (
    <AnchoredPopover open={open} onClose={onClose} anchorRef={anchorRef} label={label} maxWidth={320} className="w-72 p-2">
      <ul className="grid gap-0.5" data-testid={`${testId}-items`}>
        {items.map((item, index) => (
          <li key={item.key} className={cn(startsGroup(items, index) && index > 0 && "mt-1.5 border-t border-rule pt-1.5")}>
            {startsGroup(items, index) ? <p className="kicker px-3 pb-1 pt-1">{item.group}</p> : null}
            <button type="button" className={ITEM} disabled={busy !== null} onClick={() => void pick(item)} data-testid="download-item">
              {busy === item.key ? <Loader2 className="h-4 w-4 shrink-0 motion-safe:animate-spin" aria-hidden /> : <Download className="h-4 w-4 shrink-0 text-ink-3" aria-hidden />}
              {item.label}
            </button>
          </li>
        ))}
      </ul>
      {error ? <FormAlert className="mt-2">{error}</FormAlert> : null}
    </AnchoredPopover>
  );
}
