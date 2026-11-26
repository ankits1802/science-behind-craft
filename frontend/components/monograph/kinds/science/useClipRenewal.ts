"use client";

import { useEffect, type RefObject } from "react";

import { clipRenewal, type RenewalClock } from "@/lib/clipRenewal";
import { fetchClipLink, type HeldClips } from "@/lib/codedClips";
import { filmAskFrom } from "@/lib/codedFigureFrame";
import type { CodedFigureSpec } from "@/lib/componentSpecsScienceCoded";

const WINDOW_CLOCK: RenewalClock = {
  now: () => Date.now(),
  later: (run, ms) => window.setTimeout(run, ms),
  cancel: (timer) => window.clearTimeout(timer as number)
};

export function useClipRenewal(holder: RefObject<HTMLDivElement | null>, figure: CodedFigureSpec, held: HeldClips): void {
  useEffect(() => {
    if (!Object.keys(held).length) return;
    const frame = () => holder.current?.querySelector("iframe")?.contentWindow ?? null;
    const renewal = clipRenewal(figure, held, { read: fetchClipLink, post: (message) => frame()?.postMessage(message, "*"), clock: WINDOW_CLOCK });
    const listen = (event: MessageEvent) => {
      const key = filmAskFrom(event, frame());
      if (key !== null) renewal.ask(key);
    };
    window.addEventListener("message", listen);
    return () => {
      window.removeEventListener("message", listen);
      renewal.stop();
    };
  }, [holder, figure, held]);
}
