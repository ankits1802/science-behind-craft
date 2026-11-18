"use client";

import { useState } from "react";

import { RecordingAgreement } from "@/components/onboarding/RecordingAgreement";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { SearchableSelect } from "@/components/ui/SearchableSelect";
import { SegmentedChoice } from "@/components/ui/SegmentedChoice";
import { apiErrorMessage } from "@/lib/api";
import { startConversation, type ConversationAvailability, type RelayConversationStarted } from "@/lib/conversationContract";

export function ConversationSetup({
  offered,
  spoken,
  onAgreed,
  onStarted
}: {
  offered: ConversationAvailability;
  spoken: string | null;
  onAgreed: () => void;
  onStarted: (started: RelayConversationStarted) => void;
}) {
  const [craft, setCraft] = useState(offered.crafts[0]?.slug ?? "");
  const [language, setLanguage] = useState(spoken && offered.languages.some((each) => each.code === spoken) ? spoken : (offered.languages[0]?.code ?? ""));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (offered.consentRequired) return <RecordingAgreement language={language || "en"} onDone={onAgreed} />;

  async function start() {
    if (!craft || !language || !offered.noticeVersion) return;
    setBusy(true);
    setError(null);
    try {
      const started = await startConversation(craft, language, offered.noticeVersion);
      if (started.transport === "RELAY") onStarted(started);
      else setError("Couldn't start. Try again.");
    } catch (cause) {
      setError(apiErrorMessage(cause, "Couldn't start. Try again."));
    } finally {
      setBusy(false);
    }
  }

  const craftOptions = offered.crafts.map((each) => ({ value: each.slug, label: each.name }));
  const languageOptions = offered.languages.map((each) => ({ value: each.code, label: each.autonym, hint: each.label }));
  return (
    <div className="grid gap-4" data-testid="conversation-setup">
      {craftOptions.length > 1 ? (
        <div className="grid gap-1.5">
          <span className="field-label">Which craft shall we talk about?</span>
          <SegmentedChoice label="Which craft shall we talk about?" value={craft} options={craftOptions} onChange={setCraft} disabled={busy} />
        </div>
      ) : null}
      <SearchableSelect value={language} onChange={setLanguage} options={languageOptions} ariaLabel="Language" placeholder="Language" disabled={busy} />
      {error ? (
        <p role="alert" className="text-sm text-error-600">
          {error}
        </p>
      ) : null}
      <ActionGroup>
        <Button type="button" disabled={busy || !craft || !language} onClick={() => void start()}>
          {busy ? "Starting…" : "Start recording"}
        </Button>
      </ActionGroup>
    </div>
  );
}
