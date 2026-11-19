"use client";

import { memo, useEffect, useState } from "react";

import { boardTransform, KACHCHH_OUTLINE, NEIGHBOUR_LAND, RANN_SALT_FLATS, type MapBox } from "@/components/map/boardGeometry";
import { loadBorders } from "@/components/map/borderGeometry";
import { bordersToPath, indiaOutlinePath } from "@/components/map/projection";

export const SALT_PATTERN = "kv-map-salt";
export const PLACE_PATTERN = "kv-map-place";
export const BOARD_PLACE_PATTERN = "kv-map-place-board";
export const NO_READING_PATTERN = "kv-map-nodata";

export function MapPatterns() {
  return (
    <defs>
      <pattern id={SALT_PATTERN} width={4} height={4} patternUnits="userSpaceOnUse">
        <rect width={4} height={4} fill="var(--map-salt)" />
        <circle cx={1} cy={1.2} r={0.55} fill="var(--map-salt-hatch)" />
        <circle cx={3.1} cy={3} r={0.55} fill="var(--map-salt-hatch)" />
      </pattern>
      <pattern id={BOARD_PLACE_PATTERN} width={5} height={5} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <line x1={0} y1={0} x2={0} y2={5} stroke="var(--terracotta)" strokeWidth={1.4} />
      </pattern>
      <pattern id={PLACE_PATTERN} width={8} height={8} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <line x1={0} y1={0} x2={0} y2={8} stroke="var(--terracotta)" strokeWidth={2.2} />
      </pattern>
      <pattern id={NO_READING_PATTERN} width={9.6} height={9.6} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width={9.6} height={9.6} fill="var(--map-land)" />
        <path d="M0 0 V9.6 M0 0 H9.6" stroke="var(--map-nodata)" strokeWidth={1.3} />
      </pattern>
    </defs>
  );
}

export const MapLand = memo(function MapLand({ frame }: { frame: MapBox }) {
  return (
    <g data-testid="map-land">
      <rect x={frame.x} y={frame.y} width={frame.width} height={frame.height} fill="var(--map-water)" />
      <g transform={boardTransform()}>
        <path d={NEIGHBOUR_LAND} fill="var(--map-land-foreign)" stroke="var(--map-land-foreign)" strokeWidth={2} strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
      </g>
      <path d={indiaOutlinePath()} fillRule="evenodd" fill="var(--map-land)" />
    </g>
  );
});

export const MapCoast = memo(function MapCoast() {
  return <path d={indiaOutlinePath()} fillRule="evenodd" fill="none" stroke="var(--map-coast)" strokeWidth={0.75} strokeLinejoin="round" vectorEffect="non-scaling-stroke" className="pointer-events-none" />;
});

export const SaltFlats = memo(function SaltFlats() {
  return (
    <g transform={boardTransform()} className="pointer-events-none" data-testid="map-salt">
      <path d={RANN_SALT_FLATS} fill={`url(#${SALT_PATTERN})`} stroke="var(--map-salt-hatch)" strokeWidth={0.75} strokeDasharray="1 2" vectorEffect="non-scaling-stroke" />
    </g>
  );
});

export const KachchhPlace = memo(function KachchhPlace() {
  return (
    <g transform={boardTransform()} className="pointer-events-none" data-testid="map-place">
      <path d={KACHCHH_OUTLINE} fill={`url(#${BOARD_PLACE_PATTERN})`} stroke="var(--terracotta)" strokeWidth={1.25} vectorEffect="non-scaling-stroke" />
    </g>
  );
});

export function StateLines() {
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
  return <path d={path} fill="none" stroke="var(--map-border-state)" strokeWidth={0.75} strokeLinejoin="round" vectorEffect="non-scaling-stroke" className="pointer-events-none" />;
}
