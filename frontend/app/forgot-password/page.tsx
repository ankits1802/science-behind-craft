"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { ArrowLeft, CircleAlert } from "lucide-react";

import { AuthShell } from "@/components/auth/AuthShell";
import { Field, TextInput } from "@/components/FormControls";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { isUnreachable, serverAskedForTime } from "@/lib/failureTriage";
import { requestForgotPasswordLink, retryAfterWords } from "@/lib/signIn";

function forgotError(err: unknown): { message: string; refocus: boolean } {
  if (err instanceof ApiError && serverAskedForTime(err)) {
    const wait = retryAfterWords(err.headers?.get("retry-after"));
    return { message: wait && !err.message.includes("Try again") ? `${err.message} ${wait}` : err.message, refocus: false };
  }
  if (isUnreachable(err)) return { message: "Couldn't connect. Check your connection and try again.", refocus: false };
  return { message: err instanceof Error && err.message ? err.message : "That did not work. Check the address and try again.", refocus: true };
}

export default function ForgotPasswordPage() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState<string | null>(null);
  const emailRef = useRef<HTMLInputElement | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    const data = new FormData(event.currentTarget);
    event.preventDefault();
    if (pending) return;
    const email = String(data.get("email") ?? "").trim();
    if (!email) {
      setError("Enter your email address.");
      emailRef.current?.focus();
      return;
    }
    setPending(true);
    setError(null);
    setSent(null);
    try {
      const answer = await requestForgotPasswordLink(email);
      setSent(answer?.message || "If that address has an account, a reset link is on its way.");
    } catch (err) {
      const failure = forgotError(err);
      setError(failure.message);
      if (failure.refocus) emailRef.current?.focus();
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthShell
      title="Forgot your password?"
      subtitle="Enter the email address you sign in with. If it belongs to an account that uses a password, we will email it a link to choose a new one. The link works once and lasts 2 hours."
    >
      <form onSubmit={submit} noValidate className="grid gap-4">
        <div role="alert" aria-live="assertive" className={error ? "flex items-start gap-2 rounded-control border border-error bg-error-wash px-3 py-2.5 font-ui text-ui text-ink-1" : "sr-only"}>
          {error ? <CircleAlert aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-error" /> : null}
          {error ?? ""}
        </div>
        <p role="status" aria-live="polite" className={sent ? "m-0 rounded-control border border-success bg-success-wash px-3 py-2.5 font-ui text-ui font-normal text-ink-1" : "sr-only"}>
          {sent ?? ""}
        </p>

        <Field label="Email address">
          <TextInput
            ref={emailRef}
            id="forgot-email"
            name="email"
            type="email"
            autoComplete="username"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            inputMode="email"
            enterKeyHint="send"
            maxLength={320}
            disabled={pending}
            placeholder="you@example.com"
          />
        </Field>

        <ActionGroup fill className="mt-2">
          <Button type="submit" variant="primary" busy={pending} busyLabel="Sending" disabled={pending}>
            Email me a link
          </Button>
        </ActionGroup>
      </form>

      <p className="mt-6 font-ui text-caption text-ink-3">If two-step verification is on for your account, you will still need your authenticator app to sign in afterwards.</p>
      <p className="mt-2 font-ui text-caption text-ink-3">
        No email? Ask an administrator, who can make you a link. Nobody here can see your password, and nobody will ever ask you for it.
      </p>

      <p className="mt-6 font-ui text-ui">
        <Link href="/login" className="kv-link inline-flex items-center gap-1.5">
          <ArrowLeft aria-hidden className="h-4 w-4 shrink-0 rtl:rotate-180" />
          Back to sign in
        </Link>
      </p>
    </AuthShell>
  );
}
