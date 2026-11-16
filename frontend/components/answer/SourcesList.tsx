import { ExternalLink } from "lucide-react";

import { sourceByline, sourceHost, sourceHref } from "@/lib/citations";
import type { SourceRef } from "@/lib/types";

export type NumberedSource = { number: number; id: string; source: SourceRef | null };

export function SourcesList({
  entries,
  idPrefix = "source",
  compact = false,
  flashIds
}: {
  entries: NumberedSource[];
  idPrefix?: string;
  compact?: boolean;
  flashIds?: ReadonlySet<string>;
}) {
  const headingId = `${idPrefix}s-heading`;
  return (
    <section className={compact ? "grid gap-2" : "panel p-5 md:p-6"} aria-labelledby={headingId}>
      <h2 id={headingId} className={compact ? "field-label" : "font-display text-lg font-bold text-ink-900"}>
        Sources
      </h2>
      <ol className={compact ? "grid gap-2" : "mt-3 grid gap-2.5"}>
        {entries.map(({ number, id, source }) => {
          const href = source ? sourceHref(source) : null;
          return (
            <li
              key={id}
              id={`${idPrefix}-${number}`}
              data-flash={flashIds?.has(id) ? "true" : undefined}
              className="fr-flash-row grid grid-cols-[2rem_minmax(0,1fr)] gap-2 rounded-sm text-sm"
            >
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
