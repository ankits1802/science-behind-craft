"use client";

import { useId, useMemo } from "react";

import { useRemote } from "@/components/hooks/useRemote";
import type { MapBox } from "@/components/map/basemap";
import { loadShapes, shapePath } from "@/components/map/shapeGeometry";

export const HATCH_GAP = 9;
export const HATCH_WIDTH = 1.4;
export const HATCH_EDGE = 1.6;

export function hatchLines(frame: MapBox, gap: number): string {
  const top = frame.y;
  const bottom = frame.y + frame.height;
  const count = Math.ceil((frame.width + frame.height) / gap);
  const f = (value: number) => value.toFixed(1);
  return Array.from({ length: count + 1 }, (_, at) => frame.x - frame.height + at * gap)
    .map((start) => `M${f(start)} ${f(bottom)}L${f(start + frame.height)} ${f(top)}`)
    .join("");
}

export function PlaceHatch({ d, frame, scale }: { d: string; frame: MapBox; scale: number }) {
  const clipId = `kv-place-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;
  const lines = useMemo(() => hatchLines(frame, HATCH_GAP * scale), [frame, scale]);
  return (
    <g className="pointer-events-none" data-testid="places-home">
      <clipPath id={clipId}>
        <path d={d} clipRule="evenodd" />
      </clipPath>
      <path d={lines} clipPath={`url(#${clipId})`} fill="none" stroke="var(--terracotta)" strokeWidth={HATCH_WIDTH} vectorEffect="non-scaling-stroke" />
      <path d={d} fillRule="evenodd" fill="none" stroke="var(--terracotta)" strokeWidth={HATCH_EDGE} strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
    </g>
  );
}

export function PlaceHatchOrStill({ still, home, frame, scale }: { still: string | null; home: readonly number[]; frame: MapBox; scale: number }) {
  const shapes = useRemote(!still && home.length ? loadShapes : null).data;
  const d = useMemo(() => still ?? (shapes ?? []).filter((shape) => home.includes(shape.lgd)).map(shapePath).join(""), [still, shapes, home]);
  return d ? <PlaceHatch d={d} frame={frame} scale={scale} /> : null;
}
