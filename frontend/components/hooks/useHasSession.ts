"use client";

import { useSyncExternalStore } from "react";

import { getSessionMarker } from "@/lib/session";

function subscribeNever(): () => void {
  return () => undefined;
}

function holdsSession(): boolean {
  return getSessionMarker() !== null;
}

function serverHoldsSession(): boolean {
  return false;
}

export function useHasSession(): boolean {
  return useSyncExternalStore(subscribeNever, holdsSession, serverHoldsSession);
}
