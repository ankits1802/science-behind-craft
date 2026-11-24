"use client";

import type { MapBox } from "@/components/map/basemap";
import { frameScale, WHOLE_MAP, type PlacedPin } from "@/components/map/layout";

const CARD_WIDTH = 256;
const CLEARANCE = 14;
const FLIP_AT = 0.42;

function percent(value: number, span: number): string {
  return `${((value / span) * 100).toFixed(3)}%`;
}

function countLine(total: number): string {
  return total === 1 ? "1 craft" : `${total} crafts`;
}

export function MapHoverCard({ pin, ordinal, frame = WHOLE_MAP }: { pin: PlacedPin; ordinal?: number; frame?: MapBox }) {
  const { point } = pin;
  const y = pin.y - frame.y;
  const clearance = CLEARANCE * frameScale(frame);
  const above = y > frame.height * FLIP_AT;
  const vertical = above ? { bottom: percent(frame.height - (y - pin.radius - clearance), frame.height) } : { top: percent(y + pin.radius + clearance, frame.height) };
  const across = `clamp(0px, calc(${percent(pin.x - frame.x, frame.width)} - ${CARD_WIDTH / 2}px), calc(100% - ${CARD_WIDTH}px))`;
  const count = point.countText === undefined ? countLine(point.total) : point.countText;

  return (
    <div
      aria-hidden="true"
      style={{ left: across, ...vertical }}
      className="pointer-events-none absolute z-popover w-64 max-w-full rounded-card border border-rule bg-raised p-3 shadow-pop"
      data-testid="map-hover-card"
    >
      <p className="font-ui text-caption text-ink-3">
        {ordinal ? <span className="font-semibold text-ink-2 [font-variant-numeric:tabular-nums]">{ordinal} · </span> : null}
        <span className="font-medium text-ink-1">{point.name}</span>
      </p>
      {count ? <p className="mt-1 font-ui text-caption text-ink-3 [font-variant-numeric:tabular-nums]">{count}</p> : null}
      {point.caption ? <p className="mt-1.5 font-ui text-caption text-ink-2">{point.caption}</p> : null}
    </div>
  );
}
