"use client";

import { useMemo, type ReactNode } from "react";

import { viewBoxOf, type MapBox } from "@/components/map/basemap";
import { layoutPins, WHOLE_MAP, type MapPoint, type PlacedPin } from "@/components/map/layout";
import { MapCoast, MapLand, MapPatterns, SaltFlats, StateLines } from "@/components/map/MapBase";
import { MapHoverCard } from "@/components/map/MapHoverCard";
import { Pin } from "@/components/map/MapMarks";
import { PinControls } from "@/components/map/PinControls";
import { cn } from "@/lib/utils";

export type { MapPoint } from "@/components/map/layout";
export type ScreenLayer = (pins: readonly PlacedPin[], active: readonly string[]) => ReactNode;

export interface IndiaMapProps {
  points: MapPoint[];
  selectedKey?: string | null;
  hoveredKey?: string | null;
  onSelect?: (key: string) => void;
  onHover?: (key: string | null) => void;
  underlay?: ReactNode;
  overlay?: ReactNode;
  screenLayer?: ScreenLayer;
  frame?: MapBox;
  className?: string;
}

export function IndiaMapBase({ underlay, frame = WHOLE_MAP }: { underlay?: ReactNode; frame?: MapBox }) {
  return (
    <>
      <MapPatterns />
      <MapLand frame={frame} />
      {underlay}
      <StateLines />
      <SaltFlats />
      <MapCoast />
    </>
  );
}

export function IndiaMap({ points, selectedKey = null, hoveredKey = null, onSelect, onHover, underlay = null, overlay = null, screenLayer, frame = WHOLE_MAP, className }: IndiaMapProps) {
  const pins = useMemo(() => layoutPins(points, frame), [points, frame]);
  const ordinals = useMemo(() => new Map(points.map((point, index) => [point.key, index + 1])), [points]);
  const active = pins.find((pin) => pin.point.key === (hoveredKey ?? selectedKey)) ?? null;
  const drawnInSvg = screenLayer ? [] : pins;
  const ring = frame.width / WHOLE_MAP.width;

  return (
    <div className={cn("relative", className)}>
      <svg viewBox={frame === WHOLE_MAP ? `0 0 ${frame.width} ${frame.height}` : viewBoxOf(frame)} className="block h-auto w-full max-w-full rounded-plate" role="presentation" aria-hidden="true" focusable="false">
        <IndiaMapBase underlay={underlay} frame={frame} />
        <g>
          {pins
            .filter((pin) => pin.displaced)
            .map((pin) => (
              <g key={`leader-${pin.point.key}`}>
                <line x1={pin.anchorX} y1={pin.anchorY} x2={pin.x} y2={pin.y} stroke="var(--map-marker-ring)" strokeWidth={1} vectorEffect="non-scaling-stroke" />
                <circle cx={pin.anchorX} cy={pin.anchorY} r={2.5 * ring} fill="var(--map-marker-ring)" />
              </g>
            ))}
        </g>
        {drawnInSvg.map((pin) => (
          <Pin key={pin.point.key} pin={pin} isActive={pin.point.key === selectedKey || pin.point.key === hoveredKey} onSelect={onSelect} onHover={onHover} />
        ))}
        {overlay}
      </svg>
      {screenLayer ? screenLayer(pins, [selectedKey, hoveredKey].filter((key) => key !== null)) : null}
      {onSelect && pins.length ? <PinControls pins={pins} frame={frame} selectedKey={selectedKey} onSelect={onSelect} onHover={onHover} /> : null}
      {active ? <MapHoverCard key={active.point.key} pin={active} ordinal={ordinals.get(active.point.key)} frame={frame} /> : null}
    </div>
  );
}
