"use client";

import { useEffect, useRef, useState } from "react";

import { GoogleSignInButton } from "@/components/GoogleSignInButton";
import { useGoogleNonce } from "@/components/auth/useGoogleNonce";
import { ApiError } from "@/lib/api";
import { googleClientId } from "@/lib/googleIdentity";
import { beginSignIn, callbackErrorMessage, configuredOidcProviders, type OidcProvider } from "@/lib/oidcSignIn";
import { type ConfirmProvider, confirmPrompt, fetchFirstPasswordNonce } from "@/lib/passwordChange";
import type { ProviderProof } from "@/lib/signIn";

const GOOGLE_UNREACHABLE = "Couldn't reach Google. Check your connection and try again.";
const NO_PROVIDER_HERE = "To add a password, ask an administrator to send you a link to set one.";

type ConfirmEvents = {
  onProof: (proof: ProviderProof) => void;
  onError: (message: string) => void;
};

async function fetchGoogleConfirmNonce(): Promise<string> {
  return (await fetchFirstPasswordNonce()).nonce;
}

export function ConfirmItsYou({ provider, onProof, onError }: { provider: ConfirmProvider } & ConfirmEvents) {
  const google = provider === "GOOGLE" && googleClientId() !== null;
  const oidc = provider === "GOOGLE" ? null : (configuredOidcProviders().find((item) => item.id === provider) ?? null);

  return (
    <div className="grid gap-2 rounded-md border border-line-200 bg-surface-50 p-3">
      <p className="text-sm text-ink-700">{confirmPrompt(provider)}</p>
      {google ? <GoogleConfirm onProof={onProof} onError={onError} /> : null}
      {oidc ? <ProviderConfirm provider={oidc} onError={onError} /> : null}
      {!google && !oidc ? <p className="text-xs leading-5 text-ink-500">{NO_PROVIDER_HERE}</p> : null}
    </div>
  );
}

function GoogleConfirm({ onProof, onError }: ConfirmEvents) {
  const { clientId, nonce, failed, renew } = useGoogleNonce(fetchGoogleConfirmNonce);
  const events = useRef({ onProof, onError });
  useEffect(() => {
    events.current = { onProof, onError };
  });

  if (!clientId) return null;
  return (
    <>
      <GoogleSignInButton
        clientId={clientId}
        nonce={nonce}
        disabled={!nonce}
        onCredential={(credential) => events.current.onProof({ googleIdToken: credential })}
        onLoadError={() => events.current.onError(GOOGLE_UNREACHABLE)}
      />
      {failed ? (
        <button type="button" onClick={renew} className="w-full text-center text-xs font-medium text-purple-700 hover:underline dark:text-purple-300">
          Retry Google sign-in
        </button>
      ) : null}
    </>
  );
}

function ProviderConfirm({ provider, onError }: { provider: OidcProvider; onError: (message: string) => void }) {
  const [leaving, setLeaving] = useState(false);

  async function leaveForProvider() {
    setLeaving(true);
    try {
      const { nonce } = await fetchFirstPasswordNonce();
      window.location.assign(await beginSignIn(provider, window.location.origin, { rawNonce: nonce, purpose: "confirm" }));
    } catch (err) {
      setLeaving(false);
      onError(err instanceof ApiError ? err.message : callbackErrorMessage(provider.id, null));
    }
  }

  return (
    <div>
      <button type="button" className="field-button-secondary w-full" disabled={leaving} onClick={() => void leaveForProvider()}>
        {leaving ? "Opening…" : `Continue with ${provider.label}`}
      </button>
    </div>
  );
}
