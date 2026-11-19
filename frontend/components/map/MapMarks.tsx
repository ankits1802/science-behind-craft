"use client";

import type { PlacedPin } from "@/components/map/layout";

function pinFontSize(label: string, radius: number): number {
  if (label.length >= 3) return radius * 0.72;
  return radius * (label.length === 2 ? 0.9 : 1.05);
}

export function Pin({ pin, isActive, onSelect, onHover }: { pin: PlacedPin; isActive: boolean; onSelect?: (key: string) => void; onHover?: (key: string | null) => void }) {
  const { point, x, y, radius } = pin;
  const label = point.pinLabel ?? String(point.total);
  return (
    <g
      transform={`translate(${x} ${y})`}
      className={onSelect ? "cursor-pointer" : undefined}
      onClick={() => onSelect?.(point.key)}
      onPointerEnter={() => onHover?.(point.key)}
      onPointerLeave={() => onHover?.(null)}
      data-testid="map-pin"
    >
      <circle r={radius + 8} fill="transparent" />
      {isActive ? <circle r={radius + 4} fill="none" stroke="var(--map-selection-halo)" strokeWidth={4} /> : null}
      {isActive ? <circle r={radius + 4} fill="none" stroke="var(--map-selection)" strokeWidth={2} /> : null}
      <circle r={radius} fill="var(--map-marker)" stroke="var(--map-marker-ring)" strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
      <text textAnchor="middle" dominantBaseline="central" fontSize={pinFontSize(label, radius)} className="pointer-events-none fill-ink-1 font-ui font-semibold [font-variant-numeric:lining-nums_tabular-nums]" data-testid="map-pin-label">
        {label}
      </text>
    </g>
  );
}
