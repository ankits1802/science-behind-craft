"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AuthShell, OrDivider } from "@/components/auth/AuthShell";
import { AuthLinkLine } from "@/components/auth/PasswordField";
import { SignInRefusal } from "@/components/auth/SignInRefusal";
import { SignUpFields, SignUpPromises } from "@/components/auth/SignUpFields";
import { TurnstileWidget } from "@/components/auth/TurnstileWidget";
import { useGoogleNonce } from "@/components/auth/useGoogleNonce";
import { useAuth } from "@/components/AuthProvider";
import { GoogleSignInButton } from "@/components/GoogleSignInButton";
import { ActionGroup } from "@/components/ui/ActionGroup";
import { Button, buttonLook } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { ACCESS_STATUS_HEADER, accessRefusalKind, type AccessRefusalKind } from "@/lib/accessRoster";
import { takeSignInReturn } from "@/lib/sessionReturn";
import { fetchPrivacyNotice, fetchSignUpConfig, requestAccess, type SignUpConfig } from "@/lib/signUp";
import { isTwoFactorChallenge } from "@/lib/twoFactor";
import type { UserRole } from "@/lib/types";

function useSignUpSetup() {
  const [config, setConfig] = useState<SignUpConfig | null>(null);
  const [noticeVersion, setNoticeVersion] = useState<string | null>(null);
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
  return { config, noticeVersion };
}

function Requested({ email }: { email: string }) {
  return (
    <AuthShell title="Check your email" subtitle={email}>
      <div role="status" data-testid="signup-pending" className="grid gap-6">
        <p className="m-0 font-reading text-body text-ink-1">Open the link we sent to confirm your address and choose a password. An administrator then reviews your request.</p>
        <ActionGroup fill>
          <Link href="/login" {...buttonLook({ variant: "primary" })}>
            Go to sign in
          </Link>
        </ActionGroup>
      </div>
    </AuthShell>
  );
}

export default function SignUpPage() {
  const router = useRouter();
  const { loginWithGoogle, user } = useAuth();
  const google = useGoogleNonce();
  const { config, noticeVersion } = useSignUpSetup();
  const [role, setRole] = useState<UserRole>("STUDENT");
  const [agreed, setAgreed] = useState(false);
  const [adult, setAdult] = useState(false);
  const [humanToken, setHumanToken] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refusal, setRefusal] = useState<AccessRefusalKind | null>(null);
  const [requested, setRequested] = useState<string | null>(null);

  useEffect(() => {
    if (user) router.replace(takeSignInReturn());
  }, [router, user]);

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
      router.replace(isTwoFactorChallenge(outcome) ? "/login" : takeSignInReturn());
    } catch (err) {
      fail(err);
    } finally {
      google.renew();
    }
  }

  if (requested) return <Requested email={requested} />;

  const emailOpen = config?.signUpOpen ?? false;
  const needsHuman = Boolean(config?.turnstileRequired && config.turnstileSiteKey);
  const ready = agreed && adult && (!needsHuman || Boolean(humanToken));

  return (
    <AuthShell title="Request access" subtitle="An administrator approves each account.">
      {error ? <SignInRefusal kind={refusal} hint={null} message={error} /> : null}

      <form onSubmit={submit} className="grid gap-4">
        {emailOpen ? <SignUpFields role={role} onRole={setRole} /> : null}
        <SignUpPromises role={role} adult={adult} onAdult={setAdult} agreed={agreed} onAgreed={setAgreed} />
        {emailOpen && needsHuman && config?.turnstileSiteKey ? <TurnstileWidget siteKey={config.turnstileSiteKey} onToken={setHumanToken} /> : null}
        {emailOpen ? (
          <ActionGroup fill className="mt-2">
            <Button type="submit" variant="primary" busy={saving} busyLabel="Sending" disabled={!ready}>
              Request access
            </Button>
          </ActionGroup>
        ) : null}
      </form>

      {google.clientId ? (
        <>
          {emailOpen ? <OrDivider /> : null}
          <GoogleSignInButton clientId={google.clientId} nonce={google.nonce} text="signup_with" disabled={!google.nonce || !agreed || !adult} onCredential={(credential) => void onGoogleCredential(credential)} />
        </>
      ) : null}

      <AuthLinkLine>
        Already approved?{" "}
        <Link href="/login" className="kv-link">
          Sign in
        </Link>
      </AuthLinkLine>
    </AuthShell>
  );
}
