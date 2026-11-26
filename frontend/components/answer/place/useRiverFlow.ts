"use client";

import { useEffect, useRef, useState } from "react";
import { animate, useMotionValue, useMotionValueEvent, type MotionValue } from "framer-motion";

import { ALL_PASSED, FLOW_EASE, flowSeconds, flowStart, flowsOn, passedFraction } from "@/lib/regionStory";

export type RiverFlow = {
  progress: MotionValue<number>;
  moving: boolean;
  passed: number;
};

export type FlowPlay = { stops: readonly number[]; at: number; playing: boolean };

export function useRiverFlow(thresholds: readonly number[], play: FlowPlay, drawn: boolean): RiverFlow {
  const { stops, at, playing } = play;
  const progress = useMotionValue(ALL_PASSED);
  const [passed, setPassed] = useState(ALL_PASSED);
  const [flowing, setFlowing] = useState(false);
  const shownAt = useRef<number | null>(null);
  const target = drawn ? (stops[at] ?? ALL_PASSED) : ALL_PASSED;
  const count = stops.length;

  useMotionValueEvent(progress, "change", (value) => {
    const next = passedFraction(thresholds, value);
    setPassed((current) => (current === next ? current : next));
  });

  useEffect(() => {
    const previous = shownAt.current;
    shownAt.current = at;
    if (!drawn || !flowsOn(previous, at, count, playing)) {
      progress.jump(target);
      return;
    }
    const from = flowStart(progress.get(), target);
    progress.jump(from);
    setFlowing(true);
    const controls = animate(progress, target, { duration: flowSeconds(from, target), ease: [...FLOW_EASE], onComplete: () => setFlowing(false) });
    return () => {
      controls.stop();
      setFlowing(false);
    };
  }, [at, count, drawn, playing, progress, target]);

  return { progress, moving: flowing || target < ALL_PASSED, passed: drawn ? passed : ALL_PASSED };
}
