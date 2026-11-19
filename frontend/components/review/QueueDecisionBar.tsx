"use client";

import { useState } from "react";

import { Field, TextInput } from "@/components/FormControls";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { REASON_MAX, type QueueAction } from "@/lib/reviewQueueContract";
import { ACTION_LABELS, isDestructive, reasonProblem } from "@/lib/reviewQueueView";

const REASON_HINT = "Required to reject or retract, and kept privately with the decision. Optional when approving.";

export function QueueDecisionBar({
  actions,
  onDecide
}: {
  actions: QueueAction[];
  onDecide: (action: QueueAction, words: string) => Promise<string | null>;
}) {
  const [words, setWords] = useState("");
  const [running, setRunning] = useState<QueueAction | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const ordered = [...actions.filter((action) => !isDestructive(action)), ...actions.filter(isDestructive)];

  async function decide(action: QueueAction) {
    const found = reasonProblem(action, words);
    setProblem(found);
    setFailure(null);
    if (found) return;
    setRunning(action);
    const refused = await onDecide(action, words);
    setRunning(null);
    setFailure(refused);
  }

  return (
    <div className="grid gap-3">
      <Field label="Reason" hint={REASON_HINT} error={problem ?? undefined}>
        <TextInput value={words} maxLength={REASON_MAX} onChange={(event) => setWords(event.target.value)} />
      </Field>
      {failure ? (
        <p role="alert" className="font-ui text-ui text-error">
          {failure}
        </p>
      ) : null}
      <ActionGroup align="start">
        {ordered.map((action) => (
          <Button
            key={action}
            variant={isDestructive(action) ? "danger" : "quiet"}
            data-danger={isDestructive(action) ? "" : undefined}
            busy={running === action}
            busyLabel="Saving"
            disabled={running !== null && running !== action}
            onClick={() => void decide(action)}
          >
            {ACTION_LABELS[action]}
          </Button>
        ))}
      </ActionGroup>
    </div>
  );
}
