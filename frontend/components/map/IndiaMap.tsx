"use client";

import { memo, useEffect, useMemo, useState, type ReactNode } from "react";
import { AnimatePresence, motion, type Variants } from "framer-motion";

import { useAppReducedMotion } from "@/components/guide/useAppReducedMotion";
import { EASE_OUT } from "@/components/guide/guideMotion";
import { loadBorders } from "@/components/map/borderGeometry";
import { bloomDelays, layoutPins, type MapPoint } from "@/components/map/layout";
import { MapHoverCard } from "@/components/map/MapHoverCard";
import { Pin, ScaleBar } from "@/components/map/MapMarks";
import { bordersToPath, indiaOutlinePath, VIEW_BOX } from "@/components/map/projection";
import { cn } from "@/lib/utils";

export type { MapPoint } from "@/components/map/layout";

const BLOOM = 0.48;

function leaderFade(reduce: boolean): Variants {
  return {
    hidden: { opacity: 0, transition: reduce ? { duration: 0 } : { duration: 0.18, ease: EASE_OUT } },
    visible: { opacity: 1, transition: reduce ? { duration: 0 } : { duration: 0.22, ease: EASE_OUT, delay: BLOOM } }
  };
}

const OutlineStroke = memo(function OutlineStroke() {
  return (
    <path
      d={indiaOutlinePath()}
      fillRule="evenodd"
      className="pointer-events-none fill-none stroke-purple-300"
      strokeWidth={1.6}
      strokeLinejoin="round"
      vectorEffect="non-scaling-stroke"
    />
  );
});

const Coastline = memo(function Coastline() {
  return (
    <path
      d={indiaOutlinePath()}
      fillRule="evenodd"
      className="fill-purple-100/60 stroke-purple-300 dark:fill-purple-950/40"
      strokeWidth={1.6}
      strokeLinejoin="round"
      vectorEffect="non-scaling-stroke"
    />
  );
});

function StateBorders() {
  const [path, setPath] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    loadBorders("state")
      .then((lines) => {
        if (!cancelled) setPath(bordersToPath(lines));
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);
  if (!path) return null;
  return (
    <path
      d={path}
      fill="none"
      className="stroke-purple-300/70 dark:stroke-purple-800"
      strokeWidth={0.8}
      strokeLinejoin="round"
      vectorEffect="non-scaling-stroke"
    />
  );
}

export interface IndiaMapProps {
  points: MapPoint[];
  selectedKey?: string | null;
  hoveredKey?: string | null;
  onSelect?: (key: string) => void;
  onHover?: (key: string | null) => void;
  showStates?: boolean;
  underlay?: ReactNode;
  overlay?: ReactNode;
  className?: string;
}

export function IndiaMap({
  points,
  selectedKey = null,
  hoveredKey = null,
  onSelect,
  onHover,
  showStates = true,
  underlay = null,
  overlay = null,
  className
}: IndiaMapProps) {
  const reduce = useAppReducedMotion();
  const pins = useMemo(() => layoutPins(points), [points]);
  const delays = useMemo(() => bloomDelays(pins, BLOOM), [pins]);
  const ordinals = useMemo(() => new Map(points.map((point, index) => [point.key, index + 1])), [points]);
  const active = pins.find((pin) => pin.point.key === (hoveredKey ?? selectedKey)) ?? null;

  return (
    <div className={cn("relative", className)}>
      <motion.svg
        viewBox={`0 0 ${VIEW_BOX.width} ${VIEW_BOX.height}`}
        className="h-auto w-full max-w-full"
        role="presentation"
        aria-hidden="true"
        focusable="false"
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.3 }}
      >
        <Coastline />
        {underlay}
        {showStates ? <StateBorders /> : null}
        {underlay ? <OutlineStroke /> : null}

        <motion.g variants={leaderFade(reduce)}>
          {pins
            .filter((pin) => pin.displaced)
            .map((pin) => (
              <g key={`leader-${pin.point.key}`}>
                <line x1={pin.anchorX} y1={pin.anchorY} x2={pin.x} y2={pin.y} className="stroke-purple-400" strokeWidth={1.2} />
                <circle cx={pin.anchorX} cy={pin.anchorY} r={2} className="fill-purple-500" />
              </g>
            ))}
        </motion.g>

        {pins.map((pin) => (
          <Pin
            key={pin.point.key}
            pin={pin}
            isActive={pin.point.key === selectedKey || pin.point.key === hoveredKey}
            delay={delays.get(pin.point.key) ?? 0}
            reduce={reduce}
            onSelect={onSelect}
            onHover={onHover}
          />
        ))}

        {overlay}
        <ScaleBar />
      </motion.svg>

      <AnimatePresence>
        {active ? <MapHoverCard key={active.point.key} pin={active} ordinal={ordinals.get(active.point.key)} reduce={reduce} /> : null}
      </AnimatePresence>
    </div>
  );
}
