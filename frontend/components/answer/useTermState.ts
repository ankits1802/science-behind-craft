"use client";

import { useCallback, useState } from "react";

import type { TermSpan } from "@/lib/explainerBlockBase";

export function useTermState() {
  const [span, setSpan] = useState<TermSpan | null>(null);
  const [hidden, setHidden] = useState<ReadonlySet<string>>(() => new Set());
  const close = useCallback(() => setSpan(null), []);
  const missing = useCallback((key: string) => {
    setHidden((current) => new Set([...current, key]));
    setSpan(null);
  }, []);
  return { span, hidden, open: setSpan, close, missing };
}
