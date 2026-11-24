"use client";

import { useState } from "react";

import { HeldResult } from "@/components/contributions/HeldResult";
import { useConfirm } from "@/components/dialogs/ConfirmDialog";
import type { StatusTone } from "@/components/records/statusTone";
import { ReviewTerm } from "@/components/review/ReviewTerm";
import { StatusBadge } from "@/components/StatusBadge";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { TextLink } from "@/components/ui/TextLink";
import { apiErrorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { countsLine, decideHeldPage, HOLD_STATE_LABELS, isWaiting, type HoldDecision, type HoldState, type PageHoldView } from "@/lib/pageHoldContract";

const TONES: Record<HoldState, StatusTone> = { WAITING: "waiting", CONFIRMED: "success", DISCARDED: "neutral", EXPIRED: "neutral" };
const FAILED: Record<HoldDecision, string> = {
  CONFIRM: "Couldn't confirm the page. Reload it to see whether it went through.",
  DISCARD: "Couldn't discard the page. Try again."
};

type Decided = (next: PageHoldView) => void;

export function HeldPage({ view, onDecided }: { view: PageHoldView; onDecided: Decided }) {
  return (
    <div className="grid gap-8" data-testid="held-page" data-state={view.state}>
      <HeldSummary view={view} />
      <HeldParts view={view} />
      {isWaiting(view) ? <Decision view={view} onDecided={onDecided} /> : <HeldResult view={view} />}
    </div>
  );
}

function HeldSummary({ view }: { view: PageHoldView }) {
  return (
    <section className="grid gap-3">
      <StatusBadge tone={TONES[view.state]} label={HOLD_STATE_LABELS[view.state]} />
      <p className="max-w-measure font-reading text-body-sm text-ink-1">{view.message}</p>
      <dl className="grid gap-x-6 gap-y-2 font-ui text-label sm:grid-cols-2">
        <ReviewTerm term="The page" value={view.subject.slug} />
        {view.clientName ? <ReviewTerm term="Proposed through" value={view.clientName} /> : null}
        <ReviewTerm term="It holds" value={countsLine(view.counts)} />
        {view.decidedAt ? (
          <ReviewTerm term="Decided" value={formatDateTime(view.decidedAt)} />
        ) : (
          <ReviewTerm term={isWaiting(view) ? "Waits until" : "Expired"} value={formatDateTime(view.expiresAt)} />
        )}
      </dl>
      <p className="flex flex-wrap gap-x-6 gap-y-2 font-ui text-ui">
        <TextLink href={view.pageUrl}>Open the page as readers see it</TextLink>
        {view.previewUrl ? <TextLink href={view.previewUrl}>Open the private preview</TextLink> : null}
      </p>
    </section>
  );
}

function HeldParts({ view }: { view: PageHoldView }) {
  if (!view.parts.length) return null;
  return (
    <section className="grid gap-3" aria-labelledby="held-parts-h">
      <h2 id="held-parts-h" className="font-reading text-h3 text-ink-1">
        Its parts
      </h2>
      <ul className="grid max-w-measure gap-1 font-ui text-label text-ink-2">
        {view.parts.map((part) => (
          <li key={`${part.part}-${part.index}`} className="[overflow-wrap:anywhere]">
            {part.summary}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Decision({ view, onDecided }: { view: PageHoldView; onDecided: Decided }) {
  const confirm = useConfirm();
  const [busy, setBusy] = useState<HoldDecision | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function decide(decision: HoldDecision) {
    if (decision === "DISCARD") {
      const sure = await confirm({ title: "Discard this page?", body: "Nothing in it is proposed. The app can propose the page again.", confirmLabel: "Discard", tone: "danger" });
      if (!sure) return;
    }
    setBusy(decision);
    setError(null);
    try {
      onDecided(await decideHeldPage(view.id, decision));
    } catch (cause) {
      setError(apiErrorMessage(cause, FAILED[decision]));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="grid gap-3">
      <p className="max-w-measure font-ui text-ui text-ink-2">Confirm once: each part then goes through its own checks, as if you had proposed it yourself.</p>
      {error ? (
        <p role="alert" className="font-ui text-ui text-error">
          {error}
        </p>
      ) : null}
      <ActionGroup align="start">
        <Button type="button" variant="primary" busy={busy === "CONFIRM"} busyLabel="Proposing" disabled={busy !== null} onClick={() => void decide("CONFIRM")}>
          Confirm and propose
        </Button>
        <Button type="button" variant="danger" data-danger disabled={busy !== null} onClick={() => void decide("DISCARD")}>
          Discard
        </Button>
      </ActionGroup>
    </section>
  );
}
