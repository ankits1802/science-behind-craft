"use client";

import { useEffect, useRef, useState } from "react";

import { LiveAlert } from "@/components/auth/FormAlert";
import { useAuth } from "@/components/AuthProvider";
import { TwoStepCodeEntry, type TwoStepCodeEntryHandle, type TwoStepCodeKind } from "@/components/TwoStepCodeEntry";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { isCompleteCode } from "@/components/ui/otpCode";
import { ApiError } from "@/lib/api";
import { isUnreachable } from "@/lib/failureTriage";
import { CHALLENGE_ENDED_DETAIL } from "@/lib/twoFactor";
import type { User } from "@/lib/types";

function challengeError(err: unknown): string {
  if (isUnreachable(err)) return "Couldn't connect. Check your connection and try again.";
  return err instanceof Error ? err.message : "That code didn't work. Try again.";
}

export function TwoStepChallengeForm({
  challengeToken,
  onSignedIn,
  onCancel
}: {
  challengeToken: string;
  onSignedIn: (account: User) => void | Promise<void>;
  onCancel: () => void;
}) {
  const { verifyTwoFactor } = useAuth();
  const [kind, setKind] = useState<TwoStepCodeKind>("totp");
  const useRecovery = kind === "recovery";
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorKey, setErrorKey] = useState(0);
  const [dead, setDead] = useState(false);
  const box = useRef<TwoStepCodeEntryHandle | null>(null);

  useEffect(() => {
    box.current?.focus();
  }, []);

  async function submit(entered: string) {
    const typed = entered.trim();
    if (!typed || busy || dead) return;
    if (!useRecovery && !isCompleteCode(typed)) return;
    setBusy(true);
    setError(null);
    try {
      const account = await verifyTwoFactor(challengeToken, typed);
      await onSignedIn(account);
    } catch (err) {
      setCode("");
      setErrorKey((key) => key + 1);
      if (err instanceof ApiError && err.status === 401 && err.message === CHALLENGE_ENDED_DETAIL) setDead(true);
      setError(challengeError(err));
      box.current?.focus();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-5">
      <div className="min-w-0">
        <h2 className="font-headline text-h3 text-ink-1">Two-step verification</h2>
        <p className="mt-1 font-ui text-ui text-ink-2">
          {useRecovery ? "Enter one of the recovery codes you saved. Each code works once." : "Enter the 6-digit code from your authenticator app."}
        </p>
      </div>

      <LiveAlert message={error} />

      {dead ? (
        <ActionGroup fill>
          <Button type="button" variant="primary" onClick={onCancel}>
            Sign in again
          </Button>
        </ActionGroup>
      ) : (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void submit(code);
          }}
          className="grid gap-4"
        >
          <TwoStepCodeEntry
            ref={box}
            idPrefix="two-step"
            kind={kind}
            onKindChange={(next) => {
              setKind(next);
              setError(null);
            }}
            value={code}
            onChange={setCode}
            onComplete={(full) => void submit(full)}
            allowRecovery
            totpLabel="6-digit code"
            error={Boolean(error)}
            errorKey={errorKey}
            disabled={busy}
          />
          <ActionGroup fill>
            <Button type="submit" variant="primary" busy={busy} busyLabel="Checking" disabled={useRecovery ? !code.trim() : !isCompleteCode(code)}>
              Verify
            </Button>
          </ActionGroup>
        </form>
      )}

      <ActionGroup align="start" inline>
        <Button type="button" variant="text" onClick={onCancel}>
          Back to sign in
        </Button>
      </ActionGroup>
    </div>
  );
}
