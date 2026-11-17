"use client";

import { useEffect, useState, type RefObject } from "react";
import { animate, useInView, useMotionValue, useMotionValueEvent, type MotionValue } from "framer-motion";

import { ALL_PASSED, FLOW_EASE, FLOW_SECONDS, NOT_YET, passedFraction } from "@/lib/regionStory";

export type RiverFlow = {
  progress: MotionValue<number>;
  moving: boolean;
  passed: number;
  replay: (() => void) | null;
};

export type FlowReadiness = { expected: boolean; drawn: boolean };

const IN_VIEW = { once: true, amount: 0.35 } as const;

export function useRiverFlow(frameRef: RefObject<HTMLElement | null>, thresholds: readonly number[], river: FlowReadiness, reduce: boolean): RiverFlow {
  const inView = useInView(frameRef, IN_VIEW);
  const progress = useMotionValue(0);
  const [passed, setPassed] = useState(NOT_YET);
  const [round, setRound] = useState(0);
  const moving = river.expected && !reduce;

  useMotionValueEvent(progress, "change", (value) => {
    const next = passedFraction(thresholds, value);
    setPassed((current) => (current === next ? current : next));
  });

  useEffect(() => {
    if (!moving || !river.drawn || !inView) return;
    progress.jump(0);
    setPassed(NOT_YET);
    const controls = animate(progress, 1, { duration: FLOW_SECONDS, ease: [...FLOW_EASE] });
    return () => controls.stop();
  }, [moving, river.drawn, inView, round, progress]);

  const shown = moving ? passed : ALL_PASSED;
  const replay = moving && shown >= ALL_PASSED ? () => setRound((value) => value + 1) : null;
  return { progress, moving, passed: shown, replay };
}
