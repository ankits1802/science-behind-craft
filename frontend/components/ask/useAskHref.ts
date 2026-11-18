"use client";

import { useAuth } from "@/components/AuthProvider";
import { askPagePath, signedOutAskHref, type AskEntry } from "@/lib/askEntry";

export function useAskHref(entry: AskEntry): string {
  const { user } = useAuth();
  return user ? askPagePath(entry) : signedOutAskHref(entry);
}
