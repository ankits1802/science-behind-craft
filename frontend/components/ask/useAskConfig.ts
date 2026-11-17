"use client";

import { useEffect, useState } from "react";

import { FALLBACK_ASK_CONFIG, fetchAskConfig, normaliseAskConfig, type AskConfig } from "@/lib/askConfig";

export function useAskConfig(): { config: AskConfig; ready: boolean } {
  const [config, setConfig] = useState<AskConfig>(FALLBACK_ASK_CONFIG);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    let cancelled = false;
    fetchAskConfig()
      .then((raw) => {
        if (!cancelled) setConfig(normaliseAskConfig(raw));
      })
      .catch((error: unknown) => {
        if (!cancelled) console.error(error);
      })
      .finally(() => {
        if (!cancelled) setReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);
  return { config, ready };
}
