"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Lock, Mail } from "lucide-react";

import { AuthShell, OrDivider } from "@/components/auth/AuthShell";
import { SignInRefusal } from "@/components/auth/SignInRefusal";
import { useGoogleNonce } from "@/components/auth/useGoogleNonce";
import { useAuth } from "@/components/AuthProvider";
import { FirstPasswordGate } from "@/components/FirstPasswordGate";
import { GoogleSignInButton } from "@/components/GoogleSignInButton";
import { TwoStepChallengeForm } from "@/components/TwoStepChallengeForm";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/Toast";
import { ApiError } from "@/lib/api";
import { ACCESS_STATUS_HEADER, accessRefusalKind, type AccessRefusalKind } from "@/lib/accessRoster";
import { rememberSignInReturn, takeSignInReturn } from "@/lib/sessionReturn";
import { SIGN_IN_HINT_HEADER, mustChangePassword, signInHintOf, type SignInHint } from "@/lib/signIn";
import { isTwoFactorChallenge, type TwoFactorChallenge } from "@/lib/twoFactor";
import type { User } from "@/lib/types";

export default function LoginPage() {
  const router = useRouter();
  const { login, loginWithGoogle, logout, markPasswordChanged, user } = useAuth();
  const { toast } = useToast();
  const google = useGoogleNonce();
  const [challenge, setChallenge] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [doorPassword, setDoorPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refusal, setRefusal] = useState<AccessRefusalKind | null>(null);
  const [hint, setHint] = useState<SignInHint>(null);
  const [loading, setLoading] = useState(false);
  const signingIn = useRef(false);
  const passwordGate = mustChangePassword(user) ? user : null;

  useEffect(() => {
    rememberSignInReturn(window.location.search);
  }, []);

  useEffect(() => {
    if (user && !signingIn.current && !passwordGate && !challenge) router.replace(takeSignInReturn());
  }, [challenge, passwordGate, router, user]);

  const describeFailure = useCallback((err: unknown) => {
    const status = err instanceof ApiError ? err.status : 0;
    setRefusal(accessRefusalKind(status, err instanceof ApiError ? err.headers?.get(ACCESS_STATUS_HEADER) : null));
    setHint(signInHintOf(err instanceof ApiError ? err.headers?.get(SIGN_IN_HINT_HEADER) : null));
    setError(err instanceof ApiError ? err.message : "Couldn't sign in. Check your connection and try again.");
  }, []);

  const proceed = useCallback(
    (outcome: User | TwoFactorChallenge) => {
      if (isTwoFactorChallenge(outcome)) {
        setChallenge(outcome.challenge_token);
        return;
      }
      if (mustChangePassword(outcome)) return;
      router.replace(takeSignInReturn());
    },
    [router]
  );

  const onGoogleCredential = useCallback(
    async (credential: string) => {
      setDoorPassword("");
      setError(null);
      setRefusal(null);
      setHint(null);
      signingIn.current = true;
      try {
        proceed(await loginWithGoogle(credential, google.nonce));
      } catch (err) {
        describeFailure(err);
      } finally {
        signingIn.current = false;
        google.renew();
      }
    },
    [describeFailure, google, loginWithGoogle, proceed]
  );

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setRefusal(null);
    setHint(null);
    signingIn.current = true;
    setDoorPassword(password);
    try {
      proceed(await login(email, password));
    } catch (err) {
      setDoorPassword("");
      describeFailure(err);
    } finally {
      signingIn.current = false;
      setLoading(false);
    }
  }

  const subtitle = passwordGate || challenge ? "One more step" : "Sign in to your account";

  return (
    <AuthShell title="Welcome back" subtitle={subtitle}>
      {passwordGate ? (
        <FirstPasswordGate
          currentPassword={doorPassword}
          onDone={() => {
            setDoorPassword("");
            markPasswordChanged();
            router.replace(takeSignInReturn());
          }}
          onSignOut={() => {
            setDoorPassword("");
            setPassword("");
            logout().catch(() => undefined);
          }}
        />
      ) : challenge ? (
        <TwoStepChallengeForm
          challengeToken={challenge}
          onSignedIn={(account) => {
            setChallenge(null);
            if (!mustChangePassword(account)) router.replace(takeSignInReturn());
          }}
          onCancel={() => {
            setChallenge(null);
            setDoorPassword("");
          }}
        />
      ) : (
        <>
          {error ? <SignInRefusal kind={refusal} hint={hint} message={error} /> : null}

          <form onSubmit={submit} className="grid gap-3">
            <div className="grid gap-2">
              <label htmlFor="email" className="text-sm font-medium text-ink-900">
                Email
              </label>
              <div className="relative">
                <Mail aria-hidden className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-500" />
                <input
                  id="email"
                  type="email"
                  autoComplete="username"
                  required
                  placeholder="you@institution.ac.in"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="field-input h-[52px] pl-10"
                />
              </div>
            </div>

            <div className="grid gap-2">
              <label htmlFor="password" className="text-sm font-medium text-ink-900">
                Password
              </label>
              <div className="relative">
                <Lock aria-hidden className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-500" />
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  minLength={8}
                  placeholder="Your password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="field-input h-[52px] pl-10 pr-11"
                />
                <button
                  type="button"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  aria-pressed={showPassword}
                  onClick={() => setShowPassword((value) => !value)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-ink-300 hover:text-ink-500"
                >
                  {showPassword ? <EyeOff size={22} aria-hidden /> : <Eye size={22} aria-hidden />}
                </button>
              </div>
              <Link href="/forgot-password" className="justify-self-end text-sm font-medium text-purple-700 hover:underline dark:text-purple-300">
                Forgot your password?
              </Link>
            </div>

            <Button type="submit" size="auth" disabled={loading} className="mt-1 w-full font-display text-base font-bold">
              {loading ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          {google.clientId ? (
            <>
              <OrDivider />
              <GoogleSignInButton
                clientId={google.clientId}
                nonce={google.nonce}
                disabled={!google.nonce}
                onCredential={(credential) => void onGoogleCredential(credential)}
                onLoadError={() =>
                  toast({ title: "Couldn't load Google sign-in", description: "Check your connection and reload.", tone: "error", duration: 0 })
                }
              />
              {google.failed ? (
                <button type="button" onClick={google.renew} className="mt-2 w-full text-center text-xs font-medium text-purple-700 hover:underline dark:text-purple-300">
                  Retry Google sign-in
                </button>
              ) : null}
            </>
          ) : null}

          <p className="mt-5 text-center text-sm text-ink-500">
            New here?{" "}
            <Link href="/signup" className="font-medium text-purple-700 hover:underline dark:text-purple-300">
              Request access
            </Link>
          </p>
        </>
      )}
    </AuthShell>
  );
}
