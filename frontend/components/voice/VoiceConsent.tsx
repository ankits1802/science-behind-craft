"use client";

import { Markdown } from "@/components/Markdown";
import { ActionGroup } from "@/components/ui/ActionGroup";
import type { VoiceNotice } from "@/lib/voiceContract";

export function VoiceConsent({
  notice,
  busy,
  problem,
  onAccept,
  onDecline
}: {
  notice: VoiceNotice | null;
  busy: boolean;
  problem: string | null;
  onAccept: () => void;
  onDecline: () => void;
}) {
  if (!notice) {
    return (
      <p role="status" className="py-6 text-center text-sm text-ink-500">
        Loading…
      </p>
    );
  }
  return (
    <div className="grid gap-4" data-testid="voice-consent">
      <h3 className="font-display text-base font-bold text-ink-900">{notice.title}</h3>
      <div className="max-h-[40dvh] overflow-y-auto overscroll-contain rounded-md border border-line-200 bg-surface-50 p-3">
        <Markdown text={notice.body} />
      </div>
      {problem ? (
        <p role="alert" className="rounded-md border border-red-200 bg-error-100 px-3 py-2 text-sm text-error-600">
          {problem}
        </p>
      ) : null}
      <ActionGroup>
        <button type="button" className="field-button-secondary" onClick={onDecline}>
          Not now
        </button>
        <button type="button" className="field-button" onClick={onAccept} disabled={busy} aria-busy={busy || undefined}>
          {busy ? "Saving…" : "Agree and start"}
        </button>
      </ActionGroup>
    </div>
  );
}
