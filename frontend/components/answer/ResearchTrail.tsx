"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { ExternalLink, RotateCcw } from "lucide-react";

import { riseItem, staggerParent } from "@/components/guide/guideMotion";
import type { TrailEntry } from "@/lib/explainerStream";
import { reusedLabel, TRAIL_STAGE_LABEL, trailCounts } from "@/lib/explainerView";
import { cn } from "@/lib/utils";

export const LIVE_TRAIL_ROWS = 5;

const STAGE_CLASS: Record<TrailEntry["stage"], string> = {
  FOUND: "border-line-200 bg-surface-50 text-ink-500",
  READ: "border-purple-200 bg-purple-50 text-purple-700 dark:border-purple-900 dark:bg-purple-950/50 dark:text-purple-200",
  QUOTED: "border-purple-700 bg-purple-700 text-white dark:border-purple-400 dark:bg-purple-400 dark:text-purple-950"
};

function entryMeta(entry: TrailEntry): string {
  if (entry.storedAt) return reusedLabel(entry.storedAt);
  return [entry.publisher, entry.year ? String(entry.year) : null].filter(Boolean).join(" · ");
}

function TrailRow({ entry, reduce, own }: { entry: TrailEntry; reduce: boolean; own: boolean }) {
  const meta = entryMeta(entry);
  const motionProps = own ? { initial: "hidden", animate: "show" } : {};
  return (
    <motion.li variants={riseItem(reduce, 6)} {...motionProps} className="flex min-w-0 items-start gap-2.5 text-sm" data-testid="trail-entry" data-stage={entry.stage}>
      <span className={cn("mt-0.5 inline-flex min-w-[4.25rem] justify-center rounded-full border px-2 py-0.5 text-[11px] font-semibold", STAGE_CLASS[entry.stage])}>
        {TRAIL_STAGE_LABEL[entry.stage]}
      </span>
      <span className="min-w-0">
        {entry.url ? (
          <a href={entry.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-medium text-ink-900 hover:text-purple-700 hover:underline">
            <span className="line-clamp-2 break-words">{entry.title}</span>
            <ExternalLink className="h-3 w-3 shrink-0" aria-hidden />
            <span className="sr-only">(opens in a new tab)</span>
          </a>
        ) : (
          <span className="line-clamp-2 break-words font-medium text-ink-900">{entry.title}</span>
        )}
        {meta ? <span className="block text-xs text-ink-500">{meta}</span> : null}
      </span>
    </motion.li>
  );
}

export function ResearchTrail({ trail, live, reduce }: { trail: readonly TrailEntry[]; live: boolean; reduce: boolean }) {
  const [replaying, setReplaying] = useState(false);
  if (trail.length === 0) return null;
  const latest = trail.slice(-LIVE_TRAIL_ROWS).reverse();
  return (
    <section aria-label="Research trail" className="panel grid gap-3 px-4 py-3" data-testid="research-trail" data-live={live ? "true" : "false"}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="field-label mr-1">Research trail</span>
        <ul className="flex flex-wrap gap-1.5">
          {trailCounts(trail).map((count) => (
            <li key={count.group} className="inline-flex items-center gap-1 rounded-full border border-line-200 bg-surface-50 px-2.5 py-0.5 text-xs text-ink-700" data-group={count.group}>
              <b className="tabular-nums text-ink-900">{count.count}</b> {count.noun}
            </li>
          ))}
        </ul>
        {!live ? (
          <button
            type="button"
            className="ml-auto inline-flex min-h-9 items-center gap-1.5 rounded-full px-3 text-[13px] font-semibold text-purple-700 hover:bg-purple-50 dark:text-purple-300 dark:hover:bg-purple-950/40 pointer-coarse:min-h-11"
            aria-expanded={replaying}
            onClick={() => setReplaying((value) => !value)}
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden />
            {replaying ? "Hide the trail" : "Replay the trail"}
          </button>
        ) : null}
      </div>
      {live ? (
        <ol className="grid gap-2" aria-label="Latest sources">
          {latest.map((entry) => (
            <TrailRow key={entry.key} entry={entry} reduce={reduce} own />
          ))}
        </ol>
      ) : null}
      {!live && replaying ? (
        <motion.ol variants={staggerParent(reduce, 0.08)} initial="hidden" animate="show" className="grid gap-2" data-testid="trail-replay">
          {trail.map((entry) => (
            <TrailRow key={entry.key} entry={entry} reduce={reduce} own={false} />
          ))}
        </motion.ol>
      ) : null}
    </section>
  );
}
