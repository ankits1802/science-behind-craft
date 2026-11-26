"use client";

import { useState } from "react";

import { ComponentSlot } from "@/components/monograph/ComponentSlot";
import { CodedFigureReview } from "@/components/review/CodedFigureReview";
import { ScopeDecision } from "@/components/review/ScopeDecision";
import type { ProposalDocuments } from "@/components/review/useProposalDocuments";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { MONOGRAPH_KIT_CSS, type MonographDocument } from "@/lib/monographDocument";
import type { ChapterChanges, DrawnSide, PageAction, PageChange, PageProposalView, PageScope } from "@/lib/pageProposalContract";
import { componentScope, MARK_WORDS, SIDE_TITLES } from "@/lib/pageProposalView";

type Decide = (scope: PageScope, action: PageAction, words: string) => Promise<string | null>;

const SIDES_OF: Record<PageChange["change"], DrawnSide[]> = { ADDED: ["AFTER"], CHANGED: ["BEFORE", "AFTER"], REMOVED: ["BEFORE"] };

export function ChangedComponents({ view, chapter, docs, onDecide }: { view: PageProposalView; chapter: ChapterChanges; docs: ProposalDocuments; onDecide: Decide }) {
  const [shown, setShown] = useState(false);
  const changed = chapter.changes.filter((change) => change.kind !== "SENTENCE");
  if (!changed.length) return null;

  async function toggle() {
    const next = !shown;
    setShown(next);
    if (next) await docs.load(view.drawable);
  }

  return (
    <section className="grid gap-4" data-testid="changed-components">
      <ActionGroup align="start">
        <Button variant="quiet" aria-expanded={shown} busy={docs.busy} busyLabel="Reading" onClick={() => void toggle()}>
          {shown ? "Hide the components drawn" : `Draw the ${changed.length === 1 ? "component" : `${changed.length} components`} that change`}
        </Button>
      </ActionGroup>
      {docs.problem ? (
        <p role="alert" className="font-ui text-ui text-error">
          {docs.problem}
        </p>
      ) : null}
      {shown ? (
        <ul className="grid gap-6">
          {changed.map((change) => (
            <li key={change.ref} className="grid gap-3 border-t border-rule pt-3">
              <p className="kicker">
                {MARK_WORDS[change.change]} · {change.after ?? change.before}
              </p>
              <div className="grid gap-4 lg:grid-cols-2">
                {SIDES_OF[change.change].map((side) => (
                  <DrawnComponent key={side} side={side} label={change.ref} document={docs.documents[side]} />
                ))}
              </div>
              <ScopeDecision view={view} scope={componentScope(change.ref)} title="Decide this component" onDecide={onDecide} />
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function DrawnComponent({ side, label, document }: { side: DrawnSide; label: string; document: MonographDocument | undefined }) {
  return (
    <figure className="grid min-w-0 content-start gap-2" data-side={side}>
      <figcaption className="font-ui text-label font-semibold text-ink-1">{SIDE_TITLES[side]}</figcaption>
      {document ? (
        <div className="kv-monograph min-w-0 overflow-x-auto border-t border-ink-1 pt-3" lang={document.language}>
          <link rel="stylesheet" href={MONOGRAPH_KIT_CSS} precedence="default" />
          <ComponentSlot document={document} label={label} />
          <CodedFigureReview document={document} label={label} />
        </div>
      ) : null}
    </figure>
  );
}
