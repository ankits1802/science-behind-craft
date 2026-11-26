"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { usePlayback } from "@/components/answer/matter/usePlayback";
import { useMotionAllowed } from "@/components/motion/useMotionAllowed";

const IN_VIEW = { rootMargin: "-20% 0px -20% 0px" };

export type SequenceControls = { at: number; playing: boolean; choose: (at: number) => void; toggle: () => void };
export type MapSequencePlay = SequenceControls & { watch: (node: HTMLElement | null) => void };

export function useMapSequence(count: number): MapSequencePlay {
  const motion = useMotionAllowed();
  const last = Math.max(0, count - 1);
  const [rest] = useState(() => ({ at: last, playing: false }));
  const { at, playing, send } = usePlayback(count, motion, rest);
  const [node, watch] = useState<HTMLElement | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (!node || !motion || count < 2 || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver((entries) => {
      if (started.current || !entries.some((entry) => entry.isIntersecting)) return;
      started.current = true;
      send({ type: "play" });
    }, IN_VIEW);
    observer.observe(node);
    return () => observer.disconnect();
  }, [node, motion, count, send]);

  const choose = useCallback(
    (index: number) => {
      started.current = true;
      send({ type: "choose", index });
    },
    [send]
  );

  const toggle = useCallback(() => {
    started.current = true;
    if (playing) send({ type: "pause" });
    else if (motion) send({ type: "play" });
    else send(at >= last ? { type: "choose", index: 0 } : { type: "next" });
  }, [playing, motion, at, last, send]);

  return { at, playing, watch, choose, toggle };
}
