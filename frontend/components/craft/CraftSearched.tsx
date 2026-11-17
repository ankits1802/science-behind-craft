"use client";

import { Search } from "lucide-react";

import type { CurationHeader } from "@/lib/craftPageContract";

export function CraftSearched({ curation }: { curation: CurationHeader | null }) {
  if (!curation || curation.coverage !== "THIN" || curation.searched.length === 0) return null;
  return (
    <section aria-labelledby="craft-searched-heading" className="panel p-5 md:p-6" data-testid="craft-searched">
      <h2 id="craft-searched-heading" className="font-display text-lg font-bold text-ink-900">
        Searched
      </h2>
      <ul className="mt-3 grid gap-2">
        {curation.searched.map((entry) => (
          <li key={`${entry.site}:${entry.query}`} className="grid grid-cols-[1rem_minmax(0,1fr)] gap-2 text-sm">
            <Search className="mt-1 h-3.5 w-3.5 text-ink-500" aria-hidden />
            <span className="min-w-0 [overflow-wrap:anywhere]">
              <span className="text-ink-900">{entry.query}</span>
              <span className="block text-xs text-ink-500">{entry.site}</span>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
