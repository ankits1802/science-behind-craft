"use client";

import { useEffect, useState } from "react";

const TICK_MS = 1000;

export function useSecondsLeft(startedAt: number | null, totalSeconds: number | null): number | null {
  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    if (startedAt === null) return;
    setNow(Date.now());
    const timer = setInterval(() => setNow(Date.now()), TICK_MS);
    return () => clearInterval(timer);
  }, [startedAt]);

  if (startedAt === null || totalSeconds === null) return null;
  const elapsed = now === null || now < startedAt ? 0 : (now - startedAt) / 1000;
  return Math.max(0, totalSeconds - elapsed);
}
