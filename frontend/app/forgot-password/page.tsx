"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { ArrowLeft, CircleAlert } from "lucide-react";

import { BrandLockup } from "@/components/BrandMark";
import { Field, TextInput } from "@/components/FormControls";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { isUnreachable, serverAskedForTime } from "@/lib/failureTriage";
import { requestForgotPasswordLink, retryAfterWords } from "@/lib/signIn";

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
      if (err instanceof ApiError && serverAskedForTime(err)) {
        const wait = retryAfterWords(err.headers?.get("retry-after"));
        setError(wait && !err.message.includes("Try again") ? `${err.message} ${wait}` : err.message);
      } else if (isUnreachable(err)) {
        setError("Couldn't connect. Check your connection and try again.");
      } else {
        setError(err instanceof Error && err.message ? err.message : "That did not work. Check the address and try again.");
        emailRef.current?.focus();
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-ground px-6 py-6 md:px-10">
      <div className="relative z-10 w-full max-w-md rounded-card border border-rule bg-raised p-6 md:p-8">
        <div className="mb-5 flex flex-col items-center gap-2 text-center">
          <BrandLockup compact />
          <h1 className="mt-2 font-headline text-h3 text-ink-1">Forgot your password?</h1>
          <p className="font-ui text-ui font-normal text-ink-2">
            Enter the email address you sign in with. If it belongs to an account that uses a password, we will email
            it a link to choose a new one. The link works once and lasts 2 hours.
          </p>
        </div>

        <form onSubmit={submit} noValidate className="grid gap-3">
          <div
            role="alert"
            aria-live="assertive"
            className={error ? "flex items-start gap-2 rounded-card bg-error-wash px-3 py-2 font-ui text-ui text-error" : "sr-only"}
          >
            {error ? <CircleAlert aria-hidden className="mt-0.5 h-4 w-4 shrink-0" /> : null}
            {error ?? ""}
          </div>
          <p
            role="status"
            aria-live="polite"
            className={sent ? "rounded-card bg-success-wash px-3 py-2 font-ui text-ui font-normal text-ink-1" : "sr-only"}
          >
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

          <Button type="submit" variant="primary" className="w-full" busy={pending} busyLabel="Sending" disabled={pending}>
            Email me a link
          </Button>
        </form>

        <p className="mt-5 font-ui text-caption text-ink-3">
          If two-step verification is on for your account, you will still need your authenticator app to sign in
          afterwards.
        </p>
        <p className="mt-2 font-ui text-caption text-ink-3">
          No email? Ask an administrator — they can make you a link. Nobody here can see your password, and nobody will
          ever ask you for it.
        </p>

        <p className="mt-5 font-ui text-ui">
          <Link href="/login" className="kv-link inline-flex items-center gap-1.5">
            <ArrowLeft aria-hidden className="h-4 w-4 shrink-0 rtl:rotate-180" />
            Back to sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
