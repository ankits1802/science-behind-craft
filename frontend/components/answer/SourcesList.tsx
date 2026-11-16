import { ExternalLink } from "lucide-react";

import { sourceByline, sourceHost, sourceHref } from "@/lib/citations";
import type { SourceRef } from "@/lib/types";

export type NumberedSource = { number: number; id: string; source: SourceRef | null };

export function SourcesList({ entries }: { entries: NumberedSource[] }) {
  return (
    <section className="panel p-5 md:p-6" aria-labelledby="sources-heading">
      <h2 id="sources-heading" className="font-display text-lg font-bold text-ink-900">
        Sources
      </h2>
      <ol className="mt-3 grid gap-2.5">
        {entries.map(({ number, id, source }) => {
          const href = source ? sourceHref(source) : null;
          return (
            <li key={id} id={`source-${number}`} className="grid grid-cols-[2rem_minmax(0,1fr)] gap-2 text-sm">
              <span className="font-display font-bold tabular-nums text-purple-700 dark:text-purple-300">[{number}]</span>
              <span className="min-w-0">
                {href ? (
                  <a href={href} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-medium text-ink-900 hover:text-purple-700 hover:underline">
                    {source?.title ?? "Source"}
                    <ExternalLink className="h-3.5 w-3.5 shrink-0" aria-hidden />
                    <span className="sr-only">(opens in a new tab)</span>
                  </a>
                ) : (
                  <span className="font-medium text-ink-900">{source?.title ?? "Source"}</span>
                )}
                {source ? <span className="block text-xs text-ink-500">{[sourceByline(source), sourceHost(href)].filter(Boolean).join(" · ")}</span> : null}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
