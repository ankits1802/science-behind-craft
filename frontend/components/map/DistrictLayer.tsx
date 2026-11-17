"use client";

import { memo, useId, useMemo } from "react";

import { indiaOutlinePath, project, VIEW_BOX } from "@/components/map/projection";
import { shapePath, type DistrictShape } from "@/components/map/shapeGeometry";

export const CHOROPLETH_TONES = [
  "fill-purple-300 dark:fill-purple-800",
  "fill-purple-400 dark:fill-purple-700",
  "fill-purple-500 dark:fill-purple-600",
  "fill-purple-700 dark:fill-purple-400",
  "fill-purple-900 dark:fill-purple-200"
] as const;

export const NO_DATA_TONE = "fill-field-100";

export const HIGHLIGHT_TONES = {
  district: "fill-purple-300 dark:fill-purple-700",
  state: "fill-purple-200/80 dark:fill-purple-800/70"
} as const;

export const DISTRICT_EDGE = "stroke-card";

export type DistrictFill = (shape: DistrictShape) => string | null;

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
              className={`${fill} ${DISTRICT_EDGE}${onSelect ? " cursor-pointer" : ""}`}
              strokeWidth={0.6}
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

const TAG_FONT = 17;
const TAG_HEIGHT = 30;
const TAG_LIFT = 12;
const TAG_EDGE = 4;

export function DistrictTag({ shape, text }: { shape: DistrictShape; text: string }) {
  const { x, y } = project(shape.centroid[0], shape.centroid[1]);
  const width = text.length * TAG_FONT * 0.58 + 24;
  const left = Math.min(Math.max(x - width / 2, TAG_EDGE), VIEW_BOX.width - width - TAG_EDGE);
  const above = y - TAG_LIFT - TAG_HEIGHT >= TAG_EDGE;
  const top = above ? y - TAG_LIFT - TAG_HEIGHT : y + TAG_LIFT;
  return (
    <g className="pointer-events-none" data-testid="district-tag">
      <circle cx={x} cy={y} r={4} className="fill-ink-900 stroke-card" strokeWidth={1.5} />
      <rect x={left} y={top} width={width} height={TAG_HEIGHT} rx={8} className="fill-ink-900" />
      <text x={left + width / 2} y={top + TAG_HEIGHT / 2} textAnchor="middle" dominantBaseline="central" fontSize={TAG_FONT} className="fill-card font-sans font-semibold">
        {text}
      </text>
    </g>
  );
}
