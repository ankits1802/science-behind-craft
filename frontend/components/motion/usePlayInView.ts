"use client";

import { useCallback, useEffect, useReducer, useRef, useState, type RefObject } from "react";

import { motionAllowedNow } from "@/components/motion/useMotionAllowed";
import { IN_VIEW_MARGIN, isPlaying, played, restingPlay } from "@/lib/playInView";

export type PlayInView = {
  at: number;
  playing: boolean;
  motion: boolean;
  choose: (at: number) => void;
  toggle: () => void;
};

export type BeatLength = (at: number) => number;

const IN_VIEW = { rootMargin: IN_VIEW_MARGIN };

export function usePlayInView(count: number, rest: number, watched: RefObject<Element | null>, beat: BeatLength): PlayInView {
  const [state, dispatch] = useReducer(played, rest, restingPlay);
  const [chosen, setChosen] = useState(0);
  const length = useRef(beat);
  const playing = isPlaying(state, count);

  useEffect(() => {
    length.current = beat;
  });

  useEffect(() => {
    const node = watched.current;
    if (!node || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => dispatch({ type: "seen", on: entry.isIntersecting, motion: motionAllowedNow() })), IN_VIEW);
    observer.observe(node);
    return () => observer.disconnect();
  }, [watched]);

  useEffect(() => {
    if (playing) dispatch({ type: "start" });
  }, [playing]);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setTimeout(() => dispatch(motionAllowedNow() ? { type: "tick", count } : { type: "still" }), length.current(state.at));
    return () => window.clearTimeout(timer);
  }, [playing, count, chosen, state.at]);

  const choose = useCallback((at: number) => {
    dispatch({ type: "choose", at });
    setChosen((times) => times + 1);
  }, []);

  const toggle = useCallback(() => dispatch({ type: "toggle", motion: motionAllowedNow(), count }), [count]);

  return { at: state.at, playing, motion: state.motion, choose, toggle };
}
