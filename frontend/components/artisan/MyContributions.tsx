"use client";

import { useState } from "react";

import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { apiErrorMessage } from "@/lib/api";
import { STATUS_LABELS, withdrawContribution, type Contribution, type ContributionList } from "@/lib/testimonyContract";

const REVIEWERS: Record<string, string> = { PROFESSOR: "a professor", ADMIN: "an administrator", MASTER_ADMIN: "an administrator" };

function Item({ item, onChanged }: { item: Contribution; onChanged: () => void }) {
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function withdraw() {
    try {
      await withdrawContribution(item.id);
      onChanged();
    } catch (cause) {
      setError(apiErrorMessage(cause, "Couldn't take it back. Try again."));
    } finally {
      setAsking(false);
    }
  }

  const reviewer = item.reviewerRole ? REVIEWERS[item.reviewerRole] : null;
  return (
    <li className="grid gap-1.5 rounded-md border border-line-200 bg-card p-4" data-testid="contribution">
      <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">
        {STATUS_LABELS[item.status]} · {item.craft.name} · {item.locator}
      </p>
      {item.quote ? <p lang={item.language} className="text-sm text-ink-900">“{item.quote}”</p> : null}
      {item.english && item.english !== item.quote ? <p className="text-sm text-ink-700">{item.english}</p> : null}
      {item.claimText ? <p className="text-sm text-ink-600">{item.claimText}</p> : null}
      {reviewer ? <p className="text-xs text-ink-500">Reviewed by {reviewer}</p> : null}
      {item.reviewNote ? <p className="text-sm text-ink-700">{item.reviewNote}</p> : null}
      {asking ? <p className="text-sm text-ink-900">Take this back? It will no longer be shown anywhere.</p> : null}
      {error ? <p role="alert" className="text-sm text-error-600">{error}</p> : null}
      {item.status !== "REJECTED" ? (
        <ActionGroup align="start">
          {asking ? (
            <>
              <Button type="button" variant="destructive" size="sm" onClick={() => void withdraw()}>
                Take back
              </Button>
              <Button type="button" variant="outline" size="sm" onClick={() => setAsking(false)}>
                Keep
              </Button>
            </>
          ) : (
            <Button type="button" variant="outline" size="sm" onClick={() => setAsking(true)}>
              Withdraw
            </Button>
          )}
        </ActionGroup>
      ) : null}
    </li>
  );
}

export function MyContributions({ listed, onChanged }: { listed: ContributionList; onChanged: () => void }) {
  const shown = listed.items.filter((item): item is Contribution => item.status !== "WITHDRAWN");
  const { pending, approved, rejected, withdrawn } = listed.counts;
  return (
    <section className="grid gap-3" data-testid="my-contributions">
      <h2 className="font-display text-lg font-bold text-ink-900">What you shared</h2>
      <p className="text-sm text-ink-600">
        {pending} waiting · {approved} shown · {rejected} not shown · {withdrawn} taken back
      </p>
      {shown.length ? (
        <ul className="grid gap-3">
          {shown.map((item) => (
            <Item key={item.id} item={item} onChanged={onChanged} />
          ))}
        </ul>
      ) : (
        <p className="text-sm text-ink-500">Nothing yet.</p>
      )}
    </section>
  );
}
