"use client";

import { useEffect, useState } from "react";

import { Markdown } from "@/components/Markdown";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { apiErrorMessage } from "@/lib/api";
import { agreeToRecording, fetchRecordingNotice, type RecordingNotice } from "@/lib/profileContract";

export function RecordingAgreement({ language, onDone, notNow }: { language: string; onDone: () => void; notNow?: () => void }) {
  const [notice, setNotice] = useState<RecordingNotice | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchRecordingNotice(language)
      .then(setNotice)
      .catch((cause) => setError(apiErrorMessage(cause, "Couldn't load the recording notice. Try again.")));
  }, [language]);

  async function agree() {
    if (!notice) return;
    setBusy(true);
    setError(null);
    try {
      await agreeToRecording(notice.version, language);
      onDone();
    } catch (cause) {
      setError(apiErrorMessage(cause, "Couldn't save. Try again."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4" data-testid="recording-agreement">
      {notice ? (
        <div lang={notice.language} className="max-h-80 overflow-y-auto rounded-md border border-line-200 bg-surface-50 p-4 text-sm">
          <h3 className="mb-2 font-display font-bold text-ink-900">{notice.title}</h3>
          <Markdown text={notice.body} />
        </div>
      ) : (
        <p className="text-sm text-ink-500">Loading…</p>
      )}
      {error ? (
        <p role="alert" className="text-sm text-error-600">
          {error}
        </p>
      ) : null}
      <ActionGroup>
        <Button type="button" disabled={!notice || busy} onClick={() => void agree()}>
          I agree
        </Button>
        {notNow ? (
          <Button type="button" variant="outline" disabled={busy} onClick={notNow}>
            Not now
          </Button>
        ) : null}
      </ActionGroup>
    </div>
  );
}
