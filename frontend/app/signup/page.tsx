"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { MailCheck } from "lucide-react";

import { AuthShell, OrDivider } from "@/components/auth/AuthShell";
import { SignInRefusal } from "@/components/auth/SignInRefusal";
import { TurnstileWidget } from "@/components/auth/TurnstileWidget";
import { useGoogleNonce } from "@/components/auth/useGoogleNonce";
import { useAuth } from "@/components/AuthProvider";
import { FieldBlock } from "@/components/FormControls";
import { GoogleSignInButton } from "@/components/GoogleSignInButton";
import { Button } from "@/components/ui/button";
import { Dropdown } from "@/components/ui/Dropdown";
import { ApiError } from "@/lib/api";
import { ACCESS_STATUS_HEADER, accessRefusalKind, type AccessRefusalKind } from "@/lib/accessRoster";
import { roleLabel } from "@/lib/permissions";
import { takeSignInReturn } from "@/lib/sessionReturn";
import { REQUESTABLE_ROLES, fetchPrivacyNotice, fetchSignUpConfig, requestAccess, type SignUpConfig } from "@/lib/signUp";
import { isTwoFactorChallenge } from "@/lib/twoFactor";
import type { UserRole } from "@/lib/types";

export default function SignUpPage() {
  const router = useRouter();
  const { loginWithGoogle, user } = useAuth();
  const google = useGoogleNonce();
  const [role, setRole] = useState<UserRole>("STUDENT");
  const [agreed, setAgreed] = useState(false);
  const [adult, setAdult] = useState(false);
  const [config, setConfig] = useState<SignUpConfig | null>(null);
  const [humanToken, setHumanToken] = useState<string | null>(null);
  const [noticeVersion, setNoticeVersion] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refusal, setRefusal] = useState<AccessRefusalKind | null>(null);
  const [requested, setRequested] = useState<string | null>(null);

  useEffect(() => {
    if (user) router.replace(takeSignInReturn());
  }, [router, user]);

  useEffect(() => {
    let cancelled = false;
    fetchPrivacyNotice()
      .then((notice) => {
        if (!cancelled) setNoticeVersion(notice.version);
      })
      .catch(() => undefined);
    fetchSignUpConfig()
      .then((next) => {
        if (!cancelled) setConfig(next);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const fail = useCallback((err: unknown) => {
    const status = err instanceof ApiError ? err.status : 0;
    setRefusal(accessRefusalKind(status, err instanceof ApiError ? err.headers?.get(ACCESS_STATUS_HEADER) : null));
    setError(err instanceof ApiError ? err.message : "Couldn't send your request. Check your connection and try again.");
  }, []);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    const form = new FormData(event.currentTarget);
    event.preventDefault();
    if (!agreed || !adult) return;
    setSaving(true);
    setError(null);
    setRefusal(null);
    const email = String(form.get("email") ?? "").trim();
    try {
      const answer = await requestAccess({
        name: String(form.get("name") ?? "").trim(),
        email,
        affiliation: String(form.get("affiliation") ?? "").trim(),
        requestedRole: role,
        profileUrl: String(form.get("profileUrl") ?? "").trim() || null,
        ageAttested: adult,
        privacyNoticeVersion: noticeVersion,
        turnstileToken: humanToken
      });
      setRequested(answer.email || email);
    } catch (err) {
      fail(err);
    } finally {
      setSaving(false);
    }
  }

  async function onGoogleCredential(credential: string) {
    if (!agreed || !adult) {
      setRefusal(null);
      setError("Confirm your age and agree to the privacy notice first.");
      return;
    }
    setError(null);
    setRefusal(null);
    try {
      const outcome = await loginWithGoogle(credential, google.nonce);
      if (!isTwoFactorChallenge(outcome)) router.replace(takeSignInReturn());
      else router.replace("/login");
    } catch (err) {
      fail(err);
    } finally {
      google.renew();
    }
  }

  if (requested) {
    return (
      <AuthShell title="Check your email" subtitle={requested}>
        <div role="status" data-testid="signup-pending" className="grid justify-items-center gap-3 text-center">
          <span className="grid h-12 w-12 place-items-center rounded-full bg-success-100 text-success-600">
            <MailCheck className="h-6 w-6" aria-hidden />
          </span>
          <p className="text-sm leading-6 text-ink-700">
            Open the link we sent to confirm your address and choose a password. An administrator then reviews your request.
          </p>
          <Link href="/login" className="field-button mt-2">
            Go to sign in
          </Link>
        </div>
      </AuthShell>
    );
  }

  const roleOptions = REQUESTABLE_ROLES.map((value) => ({ value, label: roleLabel(value) }));
  const emailOpen = config?.signUpOpen ?? false;
  const needsHuman = Boolean(config?.turnstileRequired && config.turnstileSiteKey);
  const ready = agreed && adult && (!needsHuman || Boolean(humanToken));

  return (
    <AuthShell title="Request access" subtitle="An administrator approves each account">
      {error ? <SignInRefusal kind={refusal} hint={null} message={error} /> : null}

      <form onSubmit={submit} className="grid gap-3">
        {emailOpen ? (
          <>
            <label className="grid gap-1">
              <span className="field-label">Full name</span>
              <input name="name" required autoComplete="name" maxLength={120} className="field-input" />
            </label>
            <label className="grid gap-1">
              <span className="field-label">Email</span>
              <input name="email" type="email" required autoComplete="email" className="field-input" placeholder="you@institution.ac.in" />
            </label>
            <label className="grid gap-1">
              <span className="field-label">Institution</span>
              <input name="affiliation" required autoComplete="organization" maxLength={200} className="field-input" />
            </label>
            <FieldBlock label="I am a">
              <Dropdown value={role} onChange={(next) => setRole(next as UserRole)} options={roleOptions} searchable={false} advanceOnSelect={false} />
            </FieldBlock>
            {role !== "STUDENT" ? (
              <label className="grid gap-1">
                <span className="field-label">Profile page</span>
                <input name="profileUrl" type="url" inputMode="url" className="field-input" placeholder="https://" />
              </label>
            ) : null}
          </>
        ) : null}

        <div className="flex items-start gap-2.5">
          <input
            id="signup-adult"
            type="checkbox"
            required
            checked={adult}
            onChange={(event) => setAdult(event.target.checked)}
            className="mt-1 h-4 w-4 shrink-0 rounded border-line-200 [accent-color:oklch(0.47_0.198_305)]"
          />
          <label htmlFor="signup-adult" className="text-sm leading-6 text-ink-900">
            I am 18 or older
          </label>
        </div>
        <div className="flex items-start gap-2.5">
          <input
            id="signup-agree"
            type="checkbox"
            required
            checked={agreed}
            onChange={(event) => setAgreed(event.target.checked)}
            className="mt-1 h-4 w-4 shrink-0 rounded border-line-200 [accent-color:oklch(0.47_0.198_305)]"
          />
          <span className="text-sm leading-6 text-ink-900">
            <label htmlFor="signup-agree">I agree to the</label>{" "}
            <Link href="/privacy" target="_blank" rel="noopener noreferrer" className="font-medium text-purple-700 underline underline-offset-2 dark:text-purple-300">
              privacy notice
            </Link>
          </span>
        </div>

        {emailOpen && needsHuman && config?.turnstileSiteKey ? <TurnstileWidget siteKey={config.turnstileSiteKey} onToken={setHumanToken} /> : null}

        {emailOpen ? (
          <Button type="submit" size="auth" disabled={saving || !ready} className="mt-1 w-full font-display text-base font-bold">
            {saving ? "Sending…" : "Request access"}
          </Button>
        ) : null}
      </form>

      {google.clientId ? (
        <>
          {emailOpen ? <OrDivider /> : null}
          <GoogleSignInButton
            clientId={google.clientId}
            nonce={google.nonce}
            text="signup_with"
            disabled={!google.nonce || !agreed || !adult}
            onCredential={(credential) => void onGoogleCredential(credential)}
          />
        </>
      ) : null}

      <p className="mt-5 text-center text-sm text-ink-500">
        Already approved?{" "}
        <Link href="/login" className="font-medium text-purple-700 hover:underline dark:text-purple-300">
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
