"use client";

import { EvidenceSignalBadge } from "@/components/answer/EvidenceBadge";
import { ClaimList } from "@/components/craft/ClaimList";
import { usePageClaims } from "@/components/craft/CraftClaims";
import type { DifferRow } from "@/lib/craftPageContract";

function DifferItem({ row }: { row: DifferRow }) {
  const sides = usePageClaims(row.claimIds);
  return (
    <li className="grid min-w-0 gap-2.5 rounded-md border border-line-200 bg-surface-50 p-3.5" data-testid="craft-differ-row">
      <p className="flex flex-wrap items-center gap-2 text-sm font-semibold text-ink-900">
        <span className="min-w-0 [overflow-wrap:anywhere]">{row.about}</span>
        <EvidenceSignalBadge signal="SOURCES_DIFFER" />
      </p>
      <ClaimList claims={sides} size="compact" />
    </li>
  );
}

export function SourcesDiffer({ rows }: { rows: readonly DifferRow[] }) {
  if (rows.length === 0) return null;
  return (
    <section aria-labelledby="craft-differ-heading" className="panel p-5 md:p-6" data-testid="craft-sources-differ">
      <h2 id="craft-differ-heading" className="font-display text-lg font-bold text-ink-900">
        Where sources differ
      </h2>
      <ul className="mt-4 grid gap-3">
        {rows.map((row) => (
          <DifferItem key={row.about} row={row} />
        ))}
      </ul>
    </section>
  );
}
