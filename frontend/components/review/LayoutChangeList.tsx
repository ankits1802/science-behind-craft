"use client";

import { useId, useState } from "react";

import { TextLink } from "@/components/ui/TextLink";
import { CHANGES_SHOWN, changeLine } from "@/lib/layoutReviewView";
import type { LayoutChange } from "@/lib/reviewQueueContract";

export function LayoutChangeList({ changes }: { changes: LayoutChange[] }) {
  const [expanded, setExpanded] = useState(false);
  const listId = useId();
  if (!changes.length) {
    return <p className="font-ui text-ui text-ink-2">It places everything as the page&apos;s current layout does.</p>;
  }
  const shown = expanded ? changes : changes.slice(0, CHANGES_SHOWN);
  return (
    <section className="grid gap-2">
      <h4 className="font-ui text-h4 text-ink-1">Changes to the layout</h4>
      <ul id={listId} className="grid gap-3">
        {shown.map((change) => (
          <li key={change.ref} className="grid gap-0.5">
            <p className="font-code text-label text-ink-1 [overflow-wrap:anywhere]">{change.ref}</p>
            <p className="font-ui text-label text-ink-2">{changeLine(change)}</p>
          </li>
        ))}
      </ul>
      {changes.length > CHANGES_SHOWN ? (
        <TextLink standalone onClick={() => setExpanded((open) => !open)} expanded={expanded} controls={listId}>
          {expanded ? `Show the first ${CHANGES_SHOWN}` : `Show all ${changes.length} changes`}
        </TextLink>
      ) : null}
    </section>
  );
}
