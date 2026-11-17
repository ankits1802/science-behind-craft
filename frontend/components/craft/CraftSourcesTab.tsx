"use client";

import { ExternalLink } from "lucide-react";

import { sourceByline, sourceHost, sourceHref, sourceKindLabel } from "@/lib/citations";
import type { SourceGroup } from "@/lib/craftPageView";
import { countNoun } from "@/lib/format";
import type { SourceRef } from "@/lib/types";

function SourceRow({ source, number }: { source: SourceRef; number: number | undefined }) {
  const href = sourceHref(source);
  return (
    <li className="grid grid-cols-[2.25rem_minmax(0,1fr)] gap-2 text-sm" data-testid="craft-source">
      <span className="font-display font-bold tabular-nums text-purple-700 dark:text-purple-300">[{number}]</span>
      <span className="min-w-0">
        {href ? (
          <a href={href} target="_blank" rel="noopener noreferrer" className="font-medium text-ink-900 [overflow-wrap:anywhere] hover:text-purple-700 hover:underline dark:hover:text-purple-300">
            {source.title}
            <ExternalLink className="ml-1 inline h-3.5 w-3.5 align-[-2px]" aria-hidden />
            <span className="sr-only">(opens in a new tab)</span>
          </a>
        ) : (
          <span className="font-medium text-ink-900 [overflow-wrap:anywhere]">{source.title}</span>
        )}
        <span className="block text-xs text-ink-500 [overflow-wrap:anywhere]">
          {[sourceKindLabel(source.kind), sourceByline(source), sourceHost(href), source.licence].filter(Boolean).join(" · ")}
        </span>
      </span>
    </li>
  );
}

export function CraftSourcesTab({ groups, numbers }: { groups: readonly SourceGroup[]; numbers: ReadonlyMap<string, number> }) {
  return (
    <div className="grid gap-4">
      {groups.map((group) => (
        <section key={group.reliability ?? "unrated"} aria-labelledby={`sources-${group.reliability ?? "unrated"}`} className="panel p-5 md:p-6" data-testid="craft-source-group" data-reliability={group.reliability ?? ""}>
          <h2 id={`sources-${group.reliability ?? "unrated"}`} className="flex flex-wrap items-baseline gap-x-2 font-display text-base font-bold text-ink-900">
            {group.label}
            <span className="text-sm font-medium text-ink-500">{countNoun(group.sources.length, "source")}</span>
          </h2>
          <ol className="mt-3 grid gap-3">
            {group.sources.map((source) => (
              <SourceRow key={source.id} source={source} number={numbers.get(source.id)} />
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}
