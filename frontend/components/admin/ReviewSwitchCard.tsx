"use client";

import { useEffect, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { SegmentedChoice } from "@/components/ui/SegmentedChoice";
import { Skeleton } from "@/components/ui/Skeleton";
import { apiErrorMessage } from "@/lib/api";
import { canReviewContributions } from "@/lib/permissions";
import {
  defaultHint,
  fetchReviewSwitch,
  isDefault,
  MODE_LABELS,
  ORIGIN_COPY,
  PROPOSAL_ORIGINS,
  setReviewSwitch,
  SWITCH_MODES,
  type ProposalOrigin,
  type ReviewSwitch,
  type ReviewSwitchView,
  type SwitchMode
} from "@/lib/reviewSwitchContract";

const MODE_OPTIONS = SWITCH_MODES.map((value) => ({ value, label: MODE_LABELS[value] }));
const LOAD_FAILED = "Couldn't read the review settings. Reload the page to try again.";
const SAVE_FAILED = "Couldn't change the review setting. Try again.";

export function ReviewSwitchCard() {
  const { user } = useAuth();
  const allowed = canReviewContributions(user);
  const [view, setView] = useState<ReviewSwitchView | null>(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!allowed) return;
    let cancelled = false;
    fetchReviewSwitch()
      .then((found) => {
        if (!cancelled) setView(found);
      })
      .catch((cause) => {
        if (!cancelled) setError(apiErrorMessage(cause, LOAD_FAILED));
      });
    return () => {
      cancelled = true;
    };
  }, [allowed]);

  if (!allowed) return null;

  async function change(next: Partial<ReviewSwitch>) {
    setBusy(true);
    setSaved(false);
    setError(null);
    try {
      setView(await setReviewSwitch(next));
      setSaved(true);
    } catch (cause) {
      setError(apiErrorMessage(cause, SAVE_FAILED));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="review-switch-title" className="mt-section grid gap-5 border-t border-rule pt-6" data-testid="review-switch">
      <div className="grid max-w-measure gap-2">
        <h2 id="review-switch-title" className="font-headline text-h3 text-ink-1">
          Review of new facts
        </h2>
        <p className="font-ui text-ui text-ink-2">
          Every new fact passes the automatic checks first. Choose whether it then goes live and is reviewed after, or waits for a Professor or Admin. A Professor&apos;s, Admin&apos;s or Master Admin&apos;s own fact is approved at once either way.
        </p>
      </div>
      {view ? <SwitchRows view={view} busy={busy} onChange={(origin, mode) => void change({ [origin]: mode })} /> : null}
      {!view && !error ? <Skeleton shape="lede" label="Reading the review settings" /> : null}
      {view ? (
        <ActionGroup align="start">
          <Button variant="quiet" disabled={busy || isDefault(view)} onClick={() => void change(view.defaults)}>
            Restore the defaults
          </Button>
        </ActionGroup>
      ) : null}
      <p role="status" className="font-ui text-label text-ink-2">
        {saved && !busy ? "Saved." : ""}
      </p>
      {error ? (
        <p role="alert" className="font-ui text-ui text-error">
          {error}
        </p>
      ) : null}
    </section>
  );
}

function SwitchRows({ view, busy, onChange }: { view: ReviewSwitchView; busy: boolean; onChange: (origin: ProposalOrigin, mode: SwitchMode) => void }) {
  return (
    <dl className="grid gap-5">
      {PROPOSAL_ORIGINS.map((origin) => (
        <div key={origin} className="grid gap-2 border-t border-rule pt-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:gap-6">
          <dt className="grid gap-1">
            <span className="font-ui text-h4 text-ink-1">{ORIGIN_COPY[origin].label}</span>
            <span className="font-ui text-label text-ink-2">{ORIGIN_COPY[origin].covers}</span>
            <span className="font-ui text-caption text-ink-3">{defaultHint(view, origin)}</span>
          </dt>
          <dd>
            <SegmentedChoice
              label={`${ORIGIN_COPY[origin].label}: when a new fact goes live`}
              value={view.current[origin]}
              options={MODE_OPTIONS}
              onChange={(next) => onChange(origin, next as SwitchMode)}
              disabled={busy}
            />
          </dd>
        </div>
      ))}
    </dl>
  );
}
