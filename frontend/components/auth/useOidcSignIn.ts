"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import {
  OIDC_TAB_LOST,
  beginSignIn,
  callbackErrorMessage,
  configuredOidcProviders,
  fetchOidcNonce,
  loginBody,
  parseCallbackFragment,
  takePendingSignIn,
  type OidcProvider
} from "@/lib/oidcSignIn";
import type { TwoFactorChallenge } from "@/lib/twoFactor";
import type { User } from "@/lib/types";

export type OidcSignInEvents = {
  onStart: () => void;
  onSignedIn: (outcome: User | TwoFactorChallenge) => void;
  onFailure: (err: unknown) => void;
  onMessage: (message: string) => void;
  onSettled: () => void;
};

export function useOidcSignIn(events: OidcSignInEvents) {
  const { loginWithOidc } = useAuth();
  const [providers] = useState<OidcProvider[]>(() => configuredOidcProviders());
  const [busy, setBusy] = useState(false);
  const latest = useRef(events);

  useEffect(() => {
    latest.current = events;
  });

  const start = useCallback(async (provider: OidcProvider) => {
    latest.current.onStart();
    setBusy(true);
    try {
      const rawNonce = await fetchOidcNonce(provider.id);
      window.location.assign(await beginSignIn(provider, window.location.origin, { rawNonce }));
    } catch (err) {
      setBusy(false);
      latest.current.onFailure(err);
      latest.current.onSettled();
    }
  }, []);

  useEffect(() => {
    const callback = parseCallbackFragment(window.location.hash);
    if (!callback) return;
    window.history.replaceState(null, "", window.location.pathname + window.location.search);
    const pending = takePendingSignIn(callback.state);
    if (!pending) {
      latest.current.onMessage(OIDC_TAB_LOST);
      return;
    }
    if (callback.error || !callback.code) {
      latest.current.onMessage(callbackErrorMessage(pending.provider, callback.error));
      return;
    }
    latest.current.onStart();
    setBusy(true);
    loginWithOidc(loginBody(pending, callback.code))
      .then((outcome) => latest.current.onSignedIn(outcome))
      .catch((err: unknown) => latest.current.onFailure(err))
      .finally(() => {
        setBusy(false);
        latest.current.onSettled();
      });
  }, [loginWithOidc]);

  return { providers, busy, start };
}
