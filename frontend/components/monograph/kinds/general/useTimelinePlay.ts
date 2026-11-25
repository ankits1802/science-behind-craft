"use client";

import { useCallback, useEffect, useReducer, useRef, useState, type RefObject } from "react";

import { useMotionAllowed } from "@/components/motion/useMotionAllowed";
import { isPlaying, played, restingPlay, TIMELINE_STEP_MS } from "@/lib/timelinePlay";

export type TimelinePlay = {
  at: number;
  playing: boolean;
  motion: boolean;
  watched: RefObject<HTMLDivElement | null>;
  choose: (at: number) => void;
  toggle: () => void;
};

const IN_VIEW = { rootMargin: "-20% 0px -20% 0px" };

export function useTimelinePlay(count: number, rest: number): TimelinePlay {
  const motion = useMotionAllowed();
  const [state, dispatch] = useReducer(played, rest, restingPlay);
  const [chosen, setChosen] = useState(0);
  const watched = useRef<HTMLDivElement | null>(null);
  const playing = isPlaying(state, motion, count);

  useEffect(() => {
    const node = watched.current;
    if (!node || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => dispatch({ type: "seen", on: entry.isIntersecting })), IN_VIEW);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!playing) return;
    dispatch({ type: "start" });
    const timer = window.setInterval(() => dispatch({ type: "tick", count }), TIMELINE_STEP_MS);
    return () => window.clearInterval(timer);
  }, [playing, count, chosen]);

  const choose = useCallback((at: number) => {
    dispatch({ type: "choose", at });
    setChosen((times) => times + 1);
  }, []);

  const toggle = useCallback(() => dispatch({ type: "toggle", motion, count }), [motion, count]);

  return { at: state.at, playing, motion, watched, choose, toggle };
}
