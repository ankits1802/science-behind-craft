"use client";

import { useEffect, useState } from "react";

import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { fetchOpenTasks, openWorkFilter, startingTasks, type OpenTask, type TaskKind, type TaskSubject } from "@/lib/ownProposalsContract";

type StartsProps = {
  kinds: readonly TaskKind[];
  subjects: readonly TaskSubject["kind"][];
  disabled: boolean;
  onPick: (task: OpenTask) => void;
};

export function OpenWorkStarts({ kinds, subjects, disabled, onPick }: StartsProps) {
  const [tasks, setTasks] = useState<OpenTask[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchOpenTasks(openWorkFilter(kinds))
      .then((found) => {
        if (!cancelled) setTasks(startingTasks(found, kinds, subjects));
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [kinds, subjects]);

  if (failed) return <p className="font-ui text-label text-ink-3">Couldn&apos;t read where help is wanted. Start from your own sources below.</p>;
  if (!tasks) return <p role="status" className="font-ui text-label text-ink-3">Reading where help is wanted</p>;
  if (!tasks.length) return null;
  return (
    <section className="grid gap-3" aria-labelledby="open-work-h" data-testid="open-work-starts">
      <h2 id="open-work-h" className="font-reading text-h3 text-ink-1">Where help is wanted</h2>
      <ul className="grid gap-3">
        {tasks.map((task) => (
          <li key={task.key} className="grid gap-2 border-t border-rule pt-3 sm:grid-cols-[1fr_auto] sm:items-center">
            <div className="grid gap-1">
              <p className="kicker">{task.subject?.name}</p>
              <p className="max-w-measure font-reading text-body-sm text-ink-1">{task.needed}</p>
            </div>
            <ActionGroup align="start" inline>
              <Button type="button" variant="quiet" size="sm" disabled={disabled} onClick={() => onPick(task)}>
                Start from this
              </Button>
            </ActionGroup>
          </li>
        ))}
      </ul>
    </section>
  );
}
