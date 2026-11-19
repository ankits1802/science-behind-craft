"use client";

import { useEffect, useRef, useState } from "react";

import { FormAlert } from "@/components/auth/FormAlert";
import { PasswordField } from "@/components/auth/PasswordField";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { isUnreachable } from "@/lib/failureTriage";
import {
  PASSWORD_CHANGE_PROMPT,
  PASSWORD_CHANGE_SESSIONS,
  currentPasswordRefused,
  newPasswordProblem
} from "@/lib/passwordChange";
import { MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH, changeOwnPassword, passwordRuleLine } from "@/lib/signIn";

function changeError(err: unknown): string {
  if (isUnreachable(err)) return "Couldn't connect. Check your connection and try again.";
  return err instanceof Error ? err.message : "Could not set the password.";
}

export function FirstPasswordGate({
  currentPassword,
  onDone,
  onSignOut
}: {
  currentPassword: string;
  onDone: () => void;
  onSignOut: () => void;
}) {
  const [current, setCurrent] = useState(currentPassword);
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentRefusals, setCurrentRefusals] = useState(0);
  const currentBox = useRef<HTMLInputElement | null>(null);
  const askCurrent = currentPassword.length === 0 || currentRefusals > 0;

  useEffect(() => {
    if (currentRefusals > 0) currentBox.current?.focus();
  }, [currentRefusals]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const problem = newPasswordProblem({ current, next, confirm });
    if (problem) {
      setError(problem);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await changeOwnPassword(current, next);
      onDone();
    } catch (err) {
      if (currentPasswordRefused(err)) {
        setCurrent("");
        setCurrentRefusals((count) => count + 1);
      }
      setError(changeError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-4">
      <p role="status" className="m-0 border-s-2 border-rule-strong ps-3 font-reading text-body-sm text-ink-2">
        {PASSWORD_CHANGE_PROMPT}
      </p>
      {error ? <FormAlert>{error}</FormAlert> : null}

      {askCurrent ? (
        <PasswordField
          id="gate-current-password"
          label="Current password"
          inputRef={currentBox}
          autoComplete="current-password"
          revealed={show}
          value={current}
          onChange={setCurrent}
          maxLength={MAX_PASSWORD_LENGTH}
        />
      ) : null}
      <PasswordField
        id="gate-new-password"
        label="New password"
        autoComplete="new-password"
        revealed={show}
        onReveal={() => setShow((value) => !value)}
        value={next}
        onChange={setNext}
        minLength={MIN_PASSWORD_LENGTH}
        maxLength={MAX_PASSWORD_LENGTH}
      />
      <PasswordField
        id="gate-confirm-password"
        label="Repeat password"
        autoComplete="new-password"
        revealed={show}
        value={confirm}
        onChange={setConfirm}
        minLength={MIN_PASSWORD_LENGTH}
        maxLength={MAX_PASSWORD_LENGTH}
        hint={passwordRuleLine(PASSWORD_CHANGE_SESSIONS)}
      />

      <ActionGroup>
        <Button type="button" variant="quiet" onClick={onSignOut}>
          Sign out instead
        </Button>
        <Button type="submit" variant="primary" busy={saving} busyLabel="Saving">
          Set password and continue
        </Button>
      </ActionGroup>
    </form>
  );
}
