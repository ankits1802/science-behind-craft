"use client";

import { useState } from "react";
import { Share2, Undo2 } from "lucide-react";

import { MediaActionButton } from "@/components/ui/MediaActionButton";
import { ApiError, apiErrorMessage } from "@/lib/api";
import type { MediaShareAction } from "@/lib/mediaContract";
import { isUnexpected, type ShareStep } from "@/lib/mediaView";

const SHARE_FAILED = "Couldn't change sharing. Try again.";

const SPOKEN: Record<ShareStep["label"], (noun: string) => string> = {
  Share: (noun) => `Share this ${noun} on the craft page`,
  "Stop sharing": (noun) => `Stop sharing this ${noun}`,
  Withdraw: (noun) => `Withdraw your share of this ${noun}`
};

export function MediaShareButton({
  step,
  noun,
  onShare,
  onProblem
}: {
  step: ShareStep;
  noun: string;
  onShare: (action: MediaShareAction) => Promise<void>;
  onProblem: (message: string | null) => void;
}) {
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    onProblem(null);
    try {
      await onShare(step.action);
    } catch (error) {
      if (isUnexpected(error)) console.error(error);
      onProblem(error instanceof ApiError ? apiErrorMessage(error, SHARE_FAILED) : SHARE_FAILED);
    } finally {
      setBusy(false);
    }
  };

  const Icon = step.action === "SHARE" ? Share2 : Undo2;
  return (
    <MediaActionButton
      label={busy ? "Saving…" : step.label}
      icon={<Icon className="h-4 w-4" aria-hidden />}
      onClick={() => void run()}
      disabled={busy}
      accessibleLabel={busy ? undefined : SPOKEN[step.label](noun)}
    />
  );
}
