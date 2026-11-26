"use client";

import { useCallback, useEffect, useReducer, useState, type RefObject } from "react";

import { motionAllowedNow } from "@/components/motion/useMotionAllowed";
import { isPlaying, played, restingPlay, TIMELINE_STEP_MS } from "@/lib/timelinePlay";

export type TimelinePlay = {
  at: number;
  playing: boolean;
  motion: boolean;
  choose: (at: number) => void;
  toggle: () => void;
};

const IN_VIEW = { rootMargin: "-20% 0px -20% 0px" };

export function useTimelinePlay(count: number, rest: number, watched: RefObject<Element | null>): TimelinePlay {
  const [state, dispatch] = useReducer(played, rest, restingPlay);
  const [chosen, setChosen] = useState(0);
  const playing = isPlaying(state, count);

  useEffect(() => {
    const node = watched.current;
    if (!node || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => dispatch({ type: "seen", on: entry.isIntersecting, motion: motionAllowedNow() })), IN_VIEW);
    observer.observe(node);
    return () => observer.disconnect();
  }, [watched]);

  useEffect(() => {
    if (!playing) return;
    dispatch({ type: "start" });
    const timer = window.setInterval(() => dispatch(motionAllowedNow() ? { type: "tick", count } : { type: "still" }), TIMELINE_STEP_MS);
    return () => window.clearInterval(timer);
  }, [playing, count, chosen]);

  const choose = useCallback((at: number) => {
    dispatch({ type: "choose", at });
    setChosen((times) => times + 1);
  }, []);

  const toggle = useCallback(() => dispatch({ type: "toggle", motion: motionAllowedNow(), count }), [count]);

  return { at: state.at, playing, motion: state.motion, choose, toggle };
}
