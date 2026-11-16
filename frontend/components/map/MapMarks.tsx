"use client";

import { motion, type Variants } from "framer-motion";

import type { PlacedPin } from "@/components/map/layout";
import { unitsPerKilometre, VIEW_BOX } from "@/components/map/projection";
import { cn } from "@/lib/utils";

const PRESS_SPRING = { type: "spring" as const, stiffness: 380, damping: 30, mass: 0.7 };

function pinPop(reduce: boolean): Variants {
  return {
    hidden: { opacity: 0, scale: reduce ? 1 : 0.3, transition: reduce ? { duration: 0 } : PRESS_SPRING },
    visible: (delay: number) => ({
      opacity: 1,
      scale: 1,
      transition: reduce ? { duration: 0 } : { ...PRESS_SPRING, delay }
    })
  };
}

function pinFontSize(label: string, radius: number): number {
  if (label.length >= 3) return radius * 0.72;
  return radius * (label.length === 2 ? 0.9 : 1.05);
}

export function Pin({
  pin,
  isActive,
  delay,
  reduce,
  onSelect,
  onHover
}: {
  pin: PlacedPin;
  isActive: boolean;
  delay: number;
  reduce: boolean;
  onSelect?: (key: string) => void;
  onHover?: (key: string | null) => void;
}) {
  const { point, x, y, radius } = pin;
  const label = point.pinLabel ?? String(point.total);
  return (
    <g transform={`translate(${x} ${y})`}>
      <motion.g
        variants={pinPop(reduce)}
        custom={delay}
        className="cursor-pointer"
        onClick={() => onSelect?.(point.key)}
        onPointerEnter={() => onHover?.(point.key)}
        onPointerLeave={() => onHover?.(null)}
      >
        <circle r={radius + 8} fill="transparent" />
        {isActive ? <circle r={radius + 4} className="fill-none stroke-purple-700" strokeWidth={2} /> : null}
        <circle r={radius} className={cn("fill-purple-700 stroke-white", isActive ? "opacity-100" : "opacity-90")} strokeWidth={2} />
        <text textAnchor="middle" dominantBaseline="central" fontSize={pinFontSize(label, radius)} className="pointer-events-none fill-white font-display font-bold">
          {label}
        </text>
      </motion.g>
    </g>
  );
}

export function ScaleBar() {
  const kilometres = 500;
  const length = kilometres * unitsPerKilometre();
  const x = 26;
  const y = VIEW_BOX.height - 34;
  return (
    <g className="pointer-events-none">
      <line x1={x} y1={y} x2={x + length} y2={y} className="stroke-ink-500" strokeWidth={2} />
      <line x1={x} y1={y - 5} x2={x} y2={y + 5} className="stroke-ink-500" strokeWidth={2} />
      <line x1={x + length} y1={y - 5} x2={x + length} y2={y + 5} className="stroke-ink-500" strokeWidth={2} />
      <text x={x} y={y + 22} className="fill-ink-500 font-sans text-[15px]">
        {kilometres} km
      </text>
    </g>
  );
}
