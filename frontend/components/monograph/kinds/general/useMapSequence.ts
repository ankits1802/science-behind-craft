"use client";

import { useCallback, useRef } from "react";

import { usePlayInView, type PlayInView } from "@/components/motion/usePlayInView";
import { reactionBeat } from "@/lib/reactionPlayer";

export type SequenceControls = Pick<PlayInView, "at" | "playing" | "choose" | "toggle">;
export type MapSequencePlay = SequenceControls & { watch: (node: HTMLElement | null) => void };

export function sequenceRest(count: number): number {
  return Math.max(0, count - 1);
}

export function useMapSequence(count: number): MapSequencePlay {
  const watched = useRef<HTMLElement | null>(null);
  const watch = useCallback((node: HTMLElement | null) => {
    watched.current = node;
  }, []);
  const { at, playing, choose, toggle } = usePlayInView(count, sequenceRest(count), watched, reactionBeat);
  return { at, playing, watch, choose, toggle };
}
