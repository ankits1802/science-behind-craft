"use client";

import { memo, useId, useMemo } from "react";

import { MapPatterns } from "@/components/map/MapBase";
import { indiaOutlinePath, project, VIEW_BOX } from "@/components/map/projection";
import { shapePath, type DistrictShape } from "@/components/map/shapeGeometry";

export const CHOROPLETH_TONES = [
  "fill-[var(--density-1)]",
  "fill-[var(--density-2)]",
  "fill-[var(--density-3)]",
  "fill-[var(--density-5)]",
  "fill-[var(--density-6)]"
] as const;

export const NO_DATA_TONE = "fill-[url(#kv-map-nodata)]";

export const PLACE_TONE = "fill-[url(#kv-map-place)] stroke-[var(--terracotta)] [stroke-width:1.25px]";

export const HIGHLIGHT_TONES = {
  district: PLACE_TONE,
  state: PLACE_TONE
} as const;

export const DISTRICT_EDGE = "stroke-[var(--map-border-district)]";

export type DistrictFill = (shape: DistrictShape) => string | null;

function districtClass(fill: string, selectable: boolean): string {
  const edged = fill.includes("stroke-") ? fill : `${fill} ${DISTRICT_EDGE}`;
  return selectable ? `${edged} cursor-pointer` : edged;
}

export const DistrictFills = memo(function DistrictFills({
  shapes,
  fillOf,
  onHover,
  onSelect
}: {
  shapes: DistrictShape[];
  fillOf: DistrictFill;
  onHover?: (lgd: number | null) => void;
  onSelect?: (lgd: number) => void;
}) {
  const clipId = `district-clip-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;
  const paths = useMemo(() => shapes.map((shape) => ({ shape, d: shapePath(shape) })), [shapes]);
  return (
    <g data-testid="district-fills">
      <MapPatterns />
      <defs>
        <clipPath id={clipId}>
          <path d={indiaOutlinePath()} clipRule="evenodd" />
        </clipPath>
      </defs>
      <g clipPath={`url(#${clipId})`}>
        {paths.map(({ shape, d }) => {
          const fill = fillOf(shape);
          if (!fill) return null;
          return (
            <path
              key={shape.lgd}
              d={d}
              fillRule="evenodd"
              data-lgd={shape.lgd}
              className={districtClass(fill, Boolean(onSelect))}
              strokeWidth={0.5}
              vectorEffect="non-scaling-stroke"
              onPointerEnter={onHover ? () => onHover(shape.lgd) : undefined}
              onPointerLeave={onHover ? () => onHover(null) : undefined}
              onClick={onSelect ? () => onSelect(shape.lgd) : undefined}
            />
          );
        })}
      </g>
    </g>
  );
});

export function DistrictOutlines({ shapes, className }: { shapes: readonly DistrictShape[]; className: string }) {
  return (
    <g className="pointer-events-none" data-testid="district-outlines">
      {shapes.map((shape) => (
        <path key={shape.lgd} d={shapePath(shape)} fillRule="evenodd" data-lgd={shape.lgd} className={`fill-none ${className}`} strokeWidth={2} strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
      ))}
    </g>
  );
}

export const SELECTION_OUTLINE = "stroke-[var(--map-selection)]";

export function SelectedDistrict({ shape }: { shape: DistrictShape }) {
  const d = shapePath(shape);
  return (
    <g className="pointer-events-none" data-testid="district-outlines" data-lgd={shape.lgd}>
      <path d={d} fillRule="evenodd" fill="none" stroke="var(--map-selection-halo)" strokeWidth={4} strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
      <path d={d} fillRule="evenodd" fill="none" stroke="var(--map-selection)" strokeWidth={2} strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
    </g>
  );
}

const TAG_FONT = 17;
const TAG_HEIGHT = 30;
const TAG_LIFT = 12;
const TAG_EDGE = 4;

export function DistrictTag({ shape, text }: { shape: DistrictShape; text: string }) {
  const { x, y } = project(shape.centroid[0], shape.centroid[1]);
  const width = text.length * TAG_FONT * 0.58 + 24;
  const start = Math.min(Math.max(x - width / 2, TAG_EDGE), VIEW_BOX.width - width - TAG_EDGE);
  const above = y - TAG_LIFT - TAG_HEIGHT >= TAG_EDGE;
  const top = above ? y - TAG_LIFT - TAG_HEIGHT : y + TAG_LIFT;
  return (
    <g className="pointer-events-none" data-testid="district-tag">
      <circle cx={x} cy={y} r={4} fill="var(--map-selection)" stroke="var(--map-selection-halo)" strokeWidth={1.5} />
      <rect x={start} y={top} width={width} height={TAG_HEIGHT} rx={4} fill="var(--raised)" stroke="var(--rule-strong)" strokeWidth={1} vectorEffect="non-scaling-stroke" />
      <text x={start + width / 2} y={top + TAG_HEIGHT / 2} textAnchor="middle" dominantBaseline="central" fontSize={TAG_FONT} className="fill-ink-1 font-ui font-semibold">
        {text}
      </text>
    </g>
  );
}
