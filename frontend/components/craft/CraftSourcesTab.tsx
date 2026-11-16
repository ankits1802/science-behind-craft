"use client";

import { ExternalLink } from "lucide-react";

import { NoSourceFound } from "@/components/craft/ClaimList";
import { sourceByline, sourceHost, sourceHref } from "@/lib/citations";
import type { SourceRef } from "@/lib/types";

export function CraftSourcesTab({ sources, numbers }: { sources: readonly SourceRef[]; numbers: Map<string, number> }) {
  if (sources.length === 0) {
    return (
      <div className="panel p-5">
        <NoSourceFound />
      </div>
    );
  }
  return (
    <ol className="panel grid gap-3 p-5">
      {sources.map((source) => {
        const href = sourceHref(source);
        return (
          <li key={source.id} className="grid grid-cols-[2rem_minmax(0,1fr)] gap-2 text-sm">
            <span className="font-display font-bold tabular-nums text-purple-700 dark:text-purple-300">[{numbers.get(source.id)}]</span>
            <span className="min-w-0">
              {href ? (
                <a href={href} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-medium text-ink-900 hover:text-purple-700 hover:underline">
                  {source.title}
                  <ExternalLink className="h-3.5 w-3.5 shrink-0" aria-hidden />
                </a>
              ) : (
                <span className="font-medium text-ink-900">{source.title}</span>
              )}
              <span className="block text-xs text-ink-500">{[sourceByline(source), sourceHost(href), source.licence].filter(Boolean).join(" · ")}</span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
