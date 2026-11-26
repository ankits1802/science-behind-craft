"use client";

import { PageProposalCard } from "@/components/review/PageProposalCard";
import type { DrawnSide, PageAction, PageProposalView, PageScope } from "@/lib/pageProposalContract";

const TITLE = "Pages proposed whole";
const LEDE =
  "Each page is drawn as it stands and as it will be, chapter by chapter, with what is added, changed or removed marked. Approve or reject the whole page, one chapter or one component; every part still passes the checks its own queue runs, and your note reaches the contributor's open work.";

export type PageProposalsProps = {
  proposals: PageProposalView[];
  opened: Record<string, PageProposalView>;
  focused?: string | null;
  error: string | null;
  notice: string | null;
  linkNote?: string | null;
  onOpen: (id: string) => Promise<string | null>;
  onDecide: (id: string, scope: PageScope, action: PageAction, words: string) => Promise<string | null>;
  onDraw: (id: string, side: DrawnSide) => Promise<string | null>;
};

export function PageProposals({ proposals, opened, focused = null, error, notice, linkNote = null, onOpen, onDecide, onDraw }: PageProposalsProps) {
  if (!proposals.length && !error && !linkNote) return null;
  return (
    <section aria-labelledby="page-proposals-title" className="grid gap-4 border-t border-ink-1 pt-5" data-testid="page-proposals">
      <h2 id="page-proposals-title" className="font-headline text-h3 text-ink-1">
        {TITLE}
      </h2>
      <p className="max-w-measure font-ui text-ui text-ink-2">{LEDE}</p>
      <p role="status" className="font-ui text-label text-ink-2">
        {notice ?? ""}
      </p>
      {error ? (
        <p role="alert" className="font-ui text-ui text-error">
          {error}
        </p>
      ) : null}
      {linkNote ? (
        <p className="max-w-measure border-s-2 border-ink-1 ps-3 font-ui text-ui text-ink-1" data-testid="page-proposal-link">
          {linkNote}
        </p>
      ) : null}
      <ul className="grid gap-8">
        {proposals.map((summary) => (
          <li key={summary.id} className="border-t border-rule pt-5">
            <PageProposalCard
              summary={summary}
              opened={opened[summary.id] ?? null}
              focused={summary.id === focused}
              handlers={{
                open: () => onOpen(summary.id),
                decide: (scope, action, words) => onDecide(summary.id, scope, action, words),
                draw: (side) => onDraw(summary.id, side)
              }}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}
