"use client";

import type { PlacedPin } from "@/components/map/layout";
import { VIEW_BOX } from "@/components/map/projection";

const CARD_WIDTH = 256;
const CLEARANCE = 14;
const FLIP_AT = 0.42;

function percent(value: number, span: number): string {
  return `${((value / span) * 100).toFixed(3)}%`;
}

function countLine(total: number): string {
  return total === 1 ? "1 craft" : `${total} crafts`;
}

export function MapHoverCard({ pin, ordinal }: { pin: PlacedPin; ordinal?: number }) {
  const { point } = pin;
  const above = pin.y > VIEW_BOX.height * FLIP_AT;
  const vertical = above
    ? { bottom: percent(VIEW_BOX.height - (pin.y - pin.radius - CLEARANCE), VIEW_BOX.height) }
    : { top: percent(pin.y + pin.radius + CLEARANCE, VIEW_BOX.height) };
  const across = `clamp(0px, calc(${percent(pin.x, VIEW_BOX.width)} - ${CARD_WIDTH / 2}px), calc(100% - ${CARD_WIDTH}px))`;
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
