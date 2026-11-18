"use client";

import { useCallback, useEffect, useState } from "react";
import { MessageSquareQuote } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { ReviewCard } from "@/components/review/ReviewCard";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { SegmentedChoice } from "@/components/ui/SegmentedChoice";
import { apiErrorMessage } from "@/lib/api";
import { fetchReviewPage, isOpenItem, STATUS_LABELS, type ContributionStatus, type ReviewPage } from "@/lib/testimonyContract";

const STATUS_OPTIONS = (["PENDING", "APPROVED", "REJECTED", "WITHDRAWN"] as const).map((value) => ({ value, label: STATUS_LABELS[value] }));

export default function TestimonyReviewPage() {
  const [status, setStatus] = useState<ContributionStatus>("PENDING");
  const [page, setPage] = useState<ReviewPage | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (cursor: string | null, kept: ReviewPage | null) => {
    setBusy(true);
    setError(null);
    try {
      let next = await fetchReviewPage(status, cursor);
      let items = kept ? [...kept.items, ...next.items] : next.items;
      while (kept && next.nextCursor) {
        next = await fetchReviewPage(status, next.nextCursor);
        items = [...items, ...next.items];
      }
      setPage({ ...next, items });
    } catch (cause) {
      setError(apiErrorMessage(cause, "Couldn't load the queue. Try again."));
    } finally {
      setBusy(false);
    }
  }, [status]);

  useEffect(() => {
    void load(null, null);
  }, [load]);

  const shown = page?.items.length ?? 0;
  return (
    <>
      <PageHeader title="Artisan testimony" icon={<MessageSquareQuote className="h-5 w-5" aria-hidden />} />
      <div className="grid gap-4">
        <SegmentedChoice label="Status" value={status} options={STATUS_OPTIONS} onChange={(next) => setStatus(next as ContributionStatus)} disabled={busy} />
        {page ? <p className="text-sm text-ink-600" data-testid="review-count">Showing {shown} of {page.total}</p> : null}
        {error ? <p role="alert" className="text-sm text-error-600">{error}</p> : null}
        <ul className="grid gap-3">
          {page?.items.map((item) =>
            isOpenItem(item) ? (
              <ReviewCard key={`${item.id}-${item.version}`} item={item} onDecided={() => void load(null, null)} />
            ) : (
              <li key={item.id} className="rounded-md border border-line-200 bg-card p-4 text-sm text-ink-600">
                {STATUS_LABELS[item.status]} · {item.craft.name}
              </li>
            )
          )}
        </ul>
        {page && !page.items.length ? <p className="text-sm text-ink-500">Nothing here.</p> : null}
        {page?.nextCursor ? (
          <ActionGroup>
            <Button type="button" variant="outline" disabled={busy} onClick={() => void load(page.nextCursor, page)}>
              Show all {page.total}
            </Button>
          </ActionGroup>
        ) : null}
      </div>
    </>
  );
}
