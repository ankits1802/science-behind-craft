"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, apiErrorMessage } from "@/lib/api";

export type RemoteFailure = { cause: unknown };

export function failureMessage(failure: RemoteFailure, fallback: string): string {
  return failure.cause instanceof ApiError ? apiErrorMessage(failure.cause, fallback) : fallback;
}

export type Remote<T> = { data: T | null; failure: RemoteFailure | null; retry: () => void };

type Settled<T> = { data: T | null; failure: RemoteFailure | null };

export function useRemote<T>(load: (() => Promise<T>) | null): Remote<T> {
  const [settled, setSettled] = useState<Settled<T>>({ data: null, failure: null });
  const [round, setRound] = useState(0);

  useEffect(() => {
    setSettled({ data: null, failure: null });
    if (!load) return;
    let cancelled = false;
    load()
      .then((data) => {
        if (!cancelled) setSettled({ data, failure: null });
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (!(cause instanceof ApiError)) console.error(cause);
        setSettled({ data: null, failure: { cause } });
      });
    return () => {
      cancelled = true;
    };
  }, [load, round]);

  const retry = useCallback(() => setRound((value) => value + 1), []);
  return { ...settled, retry };
}
