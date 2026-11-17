"use client";

import Link from "next/link";
import { Bookmark } from "lucide-react";

import { ActionGroup } from "@/components/ui/ActionGroup";
import { formatDate } from "@/lib/format";
import { hasNewerVersion, type SavedExplainer } from "@/lib/learningContract";
import { ASK_PATH, explainerHref } from "@/lib/savedView";

function SavedRow({ item, busy, onRemove }: { item: SavedExplainer; busy: boolean; onRemove: (id: string) => void }) {
  const newer = hasNewerVersion(item);
  return (
    <li className="panel grid min-w-0 gap-2 p-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-center md:gap-4 md:p-5" data-testid="saved-explainer">
      <div className="grid min-w-0 gap-1">
        <Link href={explainerHref(item.explainerId)} className="min-w-0 break-words font-display text-base font-bold text-ink-900 underline-offset-2 hover:text-purple-700 hover:underline">
          {item.question}
        </Link>
        <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-500">
          {item.craft ? <span className="font-medium text-ink-700">{item.craft.name}</span> : null}
          <span>Saved {formatDate(item.savedAt)}</span>
          <span>Version {item.latestVersion}</span>
          {newer ? (
            <span className="rounded-full border border-purple-300 bg-purple-50 px-2 py-0.5 font-semibold text-purple-800 dark:border-purple-800 dark:bg-purple-950/50 dark:text-purple-200" data-testid="saved-newer">
              Newer version
            </span>
          ) : null}
        </p>
      </div>
      <ActionGroup inline align="end">
        <button type="button" data-danger className="field-button-secondary" disabled={busy} onClick={() => onRemove(item.explainerId)} data-testid="saved-remove">
          Remove
        </button>
      </ActionGroup>
    </li>
  );
}

export function SavedList({ items, busy, onRemove }: { items: readonly SavedExplainer[]; busy: string | null; onRemove: (id: string) => void }) {
  if (items.length === 0) {
    return (
      <div className="panel grid justify-items-center gap-3 p-6 text-center" data-testid="saved-empty">
        <Bookmark className="h-5 w-5 text-purple-700 dark:text-purple-300" aria-hidden />
        <p className="text-sm text-ink-700">Nothing saved yet.</p>
        <Link href={ASK_PATH} className="field-button">
          Ask a question
        </Link>
      </div>
    );
  }
  return (
    <ul className="grid min-w-0 gap-3" data-testid="saved-list">
      {items.map((item) => (
        <SavedRow key={item.explainerId} item={item} busy={busy === item.explainerId} onRemove={onRemove} />
      ))}
    </ul>
  );
}
