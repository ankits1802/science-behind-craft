"use client";

import { useCallback, useEffect, useState } from "react";
import { ImagePlus } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { PictureReviewCard } from "@/components/review/PictureReviewCard";
import { SegmentedChoice } from "@/components/ui/SegmentedChoice";
import { apiErrorMessage } from "@/lib/api";
import { fetchImageQueue, IMAGE_STATUS_LABELS, type ImageQueue, type ImageStatus } from "@/lib/imageContributionContract";

const STATUS_OPTIONS = (["PENDING", "APPROVED", "REJECTED", "WITHDRAWN"] as const).map((value) => ({ value, label: IMAGE_STATUS_LABELS[value] }));

export default function PictureReviewPage() {
  const [status, setStatus] = useState<ImageStatus>("PENDING");
  const [queue, setQueue] = useState<ImageQueue | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      setQueue(await fetchImageQueue(status));
      setError(null);
    } catch (cause) {
      setError(apiErrorMessage(cause, "Couldn't load the pictures. Try again."));
    } finally {
      setBusy(false);
    }
  }, [status]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <>
      <PageHeader
        title="Contributed pictures"
        description="Pictures from Researchers and above. A Professor's, Admin's or Master Admin's own picture is approved at once."
        icon={<ImagePlus className="h-5 w-5" aria-hidden />}
      />
      <div className="grid gap-4">
        <SegmentedChoice label="Status" value={status} options={STATUS_OPTIONS} onChange={(next) => setStatus(next as ImageStatus)} disabled={busy} />
        {queue ? <p role="status" className="text-ui font-ui text-ink-2">{queue.items.length} {queue.items.length === 1 ? "picture" : "pictures"}</p> : null}
        {error ? <p role="alert" className="text-ui font-ui text-error">{error}</p> : null}
        <ul className="grid gap-5">
          {queue?.items.map((item) => <PictureReviewCard key={`${item.id}-${item.status}`} item={item} onDecided={() => void load()} />)}
        </ul>
        {queue && !queue.items.length ? <p className="text-body-sm font-reading text-ink-2">Pictures in this state appear here as people give them.</p> : null}
      </div>
    </>
  );
}
