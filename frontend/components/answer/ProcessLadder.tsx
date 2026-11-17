"use client";

import { useRef, useState } from "react";
import { motion, useMotionValueEvent, useScroll, useSpring, useTransform } from "framer-motion";

import { LadderStageCard } from "@/components/answer/LadderStageCard";
import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import type { ProcessLadderBlock } from "@/lib/explainerContract";
import { ladderReach } from "@/lib/explainerView";

const SPINE_OFFSET: ["start 65%", "end 65%"] = ["start 65%", "end 65%"];

export function ProcessLadder({ block }: { block: ProcessLadderBlock }) {
  const reduce = useAppReducedMotion();
  const listRef = useRef<HTMLOListElement | null>(null);
  const count = block.stages.length;
  const { scrollYProgress } = useScroll({ target: listRef, offset: SPINE_OFFSET });
  const smoothed = useSpring(scrollYProgress, { stiffness: 140, damping: 30, mass: 0.4 });
  const progress = reduce ? scrollYProgress : smoothed;
  const fill = useTransform(progress, [0, 1], [0, 1], { clamp: true });
  const [reached, setReached] = useState(() => ladderReach(0, count, false));
  useMotionValueEvent(progress, "change", (value) => {
    const next = ladderReach(value, count, reduce);
    setReached((current) => (current === next ? current : next));
  });
  const shown = reduce ? count : reached;

  return (
    <div className="relative [--rail:2.5rem] sm:[--rail:3rem]" data-testid="process-ladder" data-reached={shown}>
      <div aria-hidden className="pointer-events-none absolute inset-y-8 left-0 flex w-[var(--rail)] justify-center">
        <div className="relative h-full w-1">
          <span className="absolute inset-0 rounded-full bg-progress-track" />
          <motion.span style={{ scaleY: reduce ? 1 : fill }} className="absolute inset-0 origin-top rounded-full bg-progress-fill" />
        </div>
      </div>
      <ol ref={listRef} className="relative grid gap-3" aria-label="Process steps">
        {block.stages.map((stage, index) => (
          <LadderStageCard key={stage.stageId} stage={stage} craft={block.craft} reached={index < shown} />
        ))}
      </ol>
    </div>
  );
}
