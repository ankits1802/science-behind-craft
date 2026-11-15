"use client";

import { motion } from "framer-motion";

import { EASE_OUT } from "@/components/guide/guideMotion";
import type { PlacedPin } from "@/components/map/layout";
import { VIEW_BOX } from "@/components/map/projection";

const CARD_WIDTH = 256;
const CLEARANCE = 14;
const FLIP_AT = 0.42;

function percent(value: number, span: number): string {
  return `${((value / span) * 100).toFixed(3)}%`;
}

export function MapHoverCard({ pin, ordinal, reduce }: { pin: PlacedPin; ordinal?: number; reduce: boolean }) {
  const { point } = pin;
  const above = pin.y > VIEW_BOX.height * FLIP_AT;
  const vertical = above
    ? { bottom: percent(VIEW_BOX.height - (pin.y - pin.radius - CLEARANCE), VIEW_BOX.height) }
    : { top: percent(pin.y + pin.radius + CLEARANCE, VIEW_BOX.height) };
  const left = `clamp(0px, calc(${percent(pin.x, VIEW_BOX.width)} - ${CARD_WIDTH / 2}px), calc(100% - ${CARD_WIDTH}px))`;

  return (
    <motion.div
      aria-hidden="true"
      initial={{ opacity: 0, scale: reduce ? 1 : 0.96 }}
      animate={{ opacity: 1, scale: 1, transition: { duration: reduce ? 0 : 0.18, ease: EASE_OUT } }}
      exit={{ opacity: 0, scale: reduce ? 1 : 0.96, transition: { duration: reduce ? 0 : 0.16, ease: EASE_OUT } }}
      style={{ left, ...vertical }}
      className="pointer-events-none absolute z-10 w-64 max-w-full rounded-lg bg-card p-3 shadow-panel ring-1 ring-line-200"
    >
      <p className="text-xs text-ink-500">
        {ordinal ? <span className="font-display font-bold tabular-nums text-purple-700">{ordinal} · </span> : null}
        <span className="font-medium text-ink-900">{point.name}</span>
      </p>
      {point.countText === undefined ? (
        <p className="mt-1 text-xs tabular-nums text-ink-500">{point.total === 1 ? "1 craft" : `${point.total} crafts`}</p>
      ) : point.countText ? (
        <p className="mt-1 text-xs tabular-nums text-ink-500">{point.countText}</p>
      ) : null}
      {point.caption ? <p className="mt-1.5 text-xs leading-5 text-ink-700">{point.caption}</p> : null}
    </motion.div>
  );
}
