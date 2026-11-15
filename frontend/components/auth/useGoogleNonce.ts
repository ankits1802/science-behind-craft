"use client";

import { useCallback, useEffect, useState } from "react";

import { fetchGoogleNonce, googleClientId } from "@/lib/googleIdentity";

export type GoogleNonceState = {
  clientId: string | null;
  nonce: string | null;
  failed: boolean;
  renew: () => void;
};

export function useGoogleNonce(): GoogleNonceState {
  const [clientId] = useState(() => googleClientId());
  const [nonce, setNonce] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [round, setRound] = useState(0);

  useEffect(() => {
    if (!clientId) return;
    let cancelled = false;
    setNonce(null);
    fetchGoogleNonce()
      .then((next) => {
        if (cancelled) return;
        setNonce(next);
        setFailed(false);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [clientId, round]);

  const renew = useCallback(() => setRound((value) => value + 1), []);

  return { clientId, nonce, failed, renew };
}
