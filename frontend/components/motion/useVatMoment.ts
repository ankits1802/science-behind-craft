"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { motionAllowedNow } from "@/components/motion/useMotionAllowed";
import { VAT_STILL_STEP, vatSchedule, vatTimings, type VatPhase } from "@/lib/motion";

export type VatMoment = { phase: VatPhase; play: () => void; playing: boolean };

function readToken(token: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(token);
}

function playedThisVisit(key: string): boolean {
  try {
    return window.sessionStorage.getItem(key) === "1";
  } catch {
    return false;
  }
}

function markPlayed(key: string): void {
  try {
    window.sessionStorage.setItem(key, "1");
  } catch {
    return;
  }
}

export function useVatMoment({ autoplayKey, onPhase }: { autoplayKey?: string; onPhase?: (phase: VatPhase) => void } = {}): VatMoment {
  const [phase, setPhase] = useState<VatPhase>("rest");
  const shownPhase = useRef<VatPhase>("rest");
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const announce = useRef(onPhase);

  useEffect(() => {
    announce.current = onPhase;
  });

  const stop = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  }, []);

  const show = useCallback((next: VatPhase) => {
    shownPhase.current = next;
    setPhase(next);
    announce.current?.(next);
  }, []);

  const run = useCallback(
    (withDelay: boolean) => {
      stop();
      if (!motionAllowedNow()) {
        if (!withDelay) show(VAT_STILL_STEP[shownPhase.current]);
        return;
      }
      for (const step of vatSchedule(vatTimings(readToken), withDelay)) timers.current.push(setTimeout(() => show(step.phase), step.at));
    },
    [show, stop]
  );

  useEffect(() => {
    if (!autoplayKey || playedThisVisit(autoplayKey)) return;
    markPlayed(autoplayKey);
    const start = setTimeout(() => run(true), 0);
    return () => {
      clearTimeout(start);
      stop();
    };
  }, [autoplayKey, run, stop]);

  useEffect(() => stop, [stop]);

  const play = useCallback(() => run(false), [run]);
  return { phase, play, playing: phase !== "rest" };
}
