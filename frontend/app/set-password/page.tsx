"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AuthShell } from "@/components/auth/AuthShell";
import { FormAlert } from "@/components/auth/FormAlert";
import { PasswordField } from "@/components/auth/PasswordField";
import { useAuth } from "@/components/AuthProvider";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button, buttonLook } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/Skeleton";
import { ApiError } from "@/lib/api";
import {
  MAX_PASSWORD_LENGTH,
  MIN_PASSWORD_LENGTH,
  checkPasswordLink,
  passwordRuleLine,
  setPasswordWithLink,
  takeLinkTokenFromAddress
} from "@/lib/signIn";

const TITLE = "Set your password";

const LINK_REFUSALS: Record<string, string> = {
  missing: "This link is incomplete. Open the whole link the administrator sent you.",
  malformed: "This is not a link this site issued. Ask the administrator for another.",
  expired: "This link has expired. Ask the administrator for a new one.",
  revoked: "This link was withdrawn. Ask the administrator for a new one.",
  spent: "This link has already been used. Sign in with the password you set.",
  "unknown-account": "This link no longer points at an account."
};

type LinkCheck = { token: string | null; valid: boolean | null; reason: string | null };

function usePasswordLink(): LinkCheck {
  const [token, setToken] = useState<string | null>(null);
  const [valid, setValid] = useState<boolean | null>(null);
  const [reason, setReason] = useState<string | null>(null);

  useEffect(() => {
    const taken = takeLinkTokenFromAddress(window.location.href);
    const address = taken.address;
    if (address !== null) queueMicrotask(() => window.history.replaceState(null, "", address));
    setToken((previous) => previous || taken.token);
  }, []);

  useEffect(() => {
    if (token === null) return;
    let cancelled = false;
    if (!token) {
      setValid(false);
      setReason("missing");
      return;
    }
    checkPasswordLink(token)
      .then((result) => {
        if (cancelled) return;
        setValid(result.valid);
        setReason(result.reason);
      })
      .catch(() => {
        if (cancelled) return;
        setValid(true);
        setReason(null);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  return { token, valid, reason };
}

function NewPasswordForm({ token, onDone }: { token: string; onDone: () => void }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [shown, setShown] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (password !== confirm) {
        setError("The two passwords do not match.");
        return;
      }
      setSaving(true);
      setError(null);
      try {
        await setPasswordWithLink(token, password);
        onDone();
      } catch (err) {
        setError(err instanceof ApiError || err instanceof Error ? err.message : "Could not set the password.");
      } finally {
        setSaving(false);
      }
    },
    [confirm, onDone, password, token]
  );

  return (
    <form onSubmit={submit} className="grid gap-4">
      {error ? <FormAlert>{error}</FormAlert> : null}
      <PasswordField id="new-password" label="New password" autoComplete="new-password" revealed={shown} onReveal={() => setShown((value) => !value)} value={password} onChange={setPassword} minLength={MIN_PASSWORD_LENGTH} maxLength={MAX_PASSWORD_LENGTH} />
      <PasswordField id="confirm-password" label="Repeat password" autoComplete="new-password" revealed={shown} value={confirm} onChange={setConfirm} minLength={MIN_PASSWORD_LENGTH} maxLength={MAX_PASSWORD_LENGTH} hint={passwordRuleLine("This link works once.")} />
      <ActionGroup fill className="mt-2">
        <Button type="submit" variant="primary" busy={saving} busyLabel="Saving">
          Set password
        </Button>
      </ActionGroup>
    </form>
  );
}

function SetPasswordForm() {
  const router = useRouter();
  const { clearSession } = useAuth();
  const link = usePasswordLink();
  const [done, setDone] = useState(false);

  if (done) {
    return (
      <AuthShell title={TITLE} subtitle="Your password is set. Any other device that was signed in to this account has been signed out.">
        <ActionGroup fill>
          <Button variant="primary" onClick={() => router.replace("/login")}>
            Go to sign in
          </Button>
        </ActionGroup>
      </AuthShell>
    );
  }
  if (link.valid === null) {
    return (
      <AuthShell title={TITLE} subtitle="Choose the password you will sign in with.">
        <Skeleton shape="lede" label="Checking this link" />
      </AuthShell>
    );
  }
  if (!link.valid || !link.token) {
    return (
      <AuthShell title={TITLE} subtitle="This link cannot set a password.">
        <FormAlert>{LINK_REFUSALS[link.reason ?? ""] ?? "This password link is not valid."}</FormAlert>
        <ActionGroup fill className="mt-6">
          <Link href="/login" {...buttonLook({ variant: "quiet" })}>
            Back to sign in
          </Link>
        </ActionGroup>
      </AuthShell>
    );
  }
  return (
    <AuthShell title={TITLE} subtitle="Choose the password you will sign in with.">
      <NewPasswordForm
        token={link.token}
        onDone={() => {
          clearSession();
          setDone(true);
        }}
      />
    </AuthShell>
  );
}

export default function SetPasswordPage() {
  return <SetPasswordForm />;
}
