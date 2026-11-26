"use client";

import { useId, useState } from "react";

import { ChapterChangeList } from "@/components/review/ChapterChangeList";
import { PageShots } from "@/components/review/PageShots";
import { ScopeDecision } from "@/components/review/ScopeDecision";
import { useProposalDocuments } from "@/components/review/useProposalDocuments";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/Skeleton";
import { TextLink } from "@/components/ui/TextLink";
import { formatDateTime } from "@/lib/format";
import type { DrawnSide, PageAction, PageProposalView, PageScope } from "@/lib/pageProposalContract";
import { chapterCounts, partLine, waitingLine, WHOLE_PAGE } from "@/lib/pageProposalView";
import { proposerLine } from "@/lib/reviewQueueView";

export type PageCardHandlers = {
  open: () => Promise<string | null>;
  decide: (scope: PageScope, action: PageAction, words: string) => Promise<string | null>;
  draw: (side: DrawnSide) => Promise<string | null>;
};

export function PageProposalCard({ summary, opened, handlers }: { summary: PageProposalView; opened: PageProposalView | null; handlers: PageCardHandlers }) {
  const [open, setOpen] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const panel = useId();
  const docs = useProposalDocuments(summary.id);
  const view = opened ?? summary;
  const proposer = proposerLine(view.proposer);

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next) setProblem(await handlers.open());
  }

  return (
    <article className="grid gap-5" data-testid="page-proposal-card">
      <header className="grid gap-1">
        <p className="kicker">Page proposal · {view.subject.kind}</p>
        <h3 className="font-headline text-h3 text-ink-1">
          <TextLink href={view.pageUrl}>{view.subjectName}</TextLink>
        </h3>
        <p className="font-ui text-label text-ink-3">
          <time dateTime={view.createdAt}>{formatDateTime(view.createdAt)}</time>
          {proposer ? ` · ${proposer}` : null} · {waitingLine(view)}
        </p>
      </header>
      <ul className="grid gap-1 font-ui text-label text-ink-2">
        {summary.chapters.map((chapter) => (
          <li key={chapter.key}>
            <span className="font-semibold text-ink-1">{chapter.title}</span> · {chapterCounts(chapter)}
          </li>
        ))}
      </ul>
      <ActionGroup align="start">
        <Button variant="quiet" aria-expanded={open} aria-controls={panel} onClick={() => void toggle()}>
          {open ? "Hide the page" : "Show the page as it stands and as it will be"}
        </Button>
      </ActionGroup>
      {problem ? (
        <p role="alert" className="font-ui text-ui text-error">
          {problem}
        </p>
      ) : null}
      {open ? (
        <div id={panel} className="grid gap-8">
          {opened ? (
            <>
              <PageShots view={opened} onDraw={handlers.draw} />
              <ChapterChangeList view={opened} docs={docs} onDecide={handlers.decide} />
              <PartList view={opened} />
            </>
          ) : (
            <Skeleton shape="lede" label="Opening the page proposal" />
          )}
        </div>
      ) : null}
      <ScopeDecision view={view} scope={WHOLE_PAGE} title="Decide the whole page" onDecide={handlers.decide} />
    </article>
  );
}

function PartList({ view }: { view: PageProposalView }) {
  return (
    <section className="grid gap-2" data-testid="page-parts">
      <h4 className="font-ui text-h4 text-ink-1">Each part, as its own queue checks it</h4>
      <ul className="grid gap-2">
        {view.parts.map((part) => (
          <li key={part.id} className="grid gap-0.5 border-t border-rule pt-2" data-state={part.state}>
            <p className="font-ui text-label text-ink-3">{partLine(part)}</p>
            <p className="max-w-measure font-reading text-body-sm text-ink-1">{part.title}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
