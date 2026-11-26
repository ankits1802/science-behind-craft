import type { ReactNode } from "react";

import type { MapBox } from "@/components/map/basemap";
import { scaleBar } from "@/components/map/mapDistance";
import { SCALE_INSET, SCALE_TICK } from "@/components/map/MapScale";
import { TIER_HIDDEN } from "@/components/map/physical/RotatedLabel";
import { frameShare, mapLabel, type MapLabel, type PeakLabel } from "@/components/map/placesMapLabels";
import type { Projected } from "@/components/map/projection";
import { formatNumber } from "@/lib/measure";
import { cn } from "@/lib/utils";

export const LABEL_FONT = "var(--text-caption)";
export const LABEL_HALO = 3;
export const SCALE_TEXT_GAP = 6;

const ORIGIN: Projected = { x: 0, y: 0 };

const WEIGHT = { normal: "font-normal", medium: "font-medium", semibold: "font-semibold" } as const;

export function MapAt({ frame, at, className, testId, children }: { frame: MapBox; at: Projected; className?: string; testId?: string; children: ReactNode }) {
  const share = frameShare(frame, at);
  return (
    <svg x={share.x} y={share.y} overflow="visible" className={className} data-testid={testId}>
      {children}
    </svg>
  );
}

export function LabelText({ label }: { label: MapLabel }) {
  const face = label.italic ? "font-reading italic" : "font-ui";
  const figures = label.numeric ? "[font-variant-numeric:lining-nums_tabular-nums]" : null;
  return (
    <g transform={label.angle ? `rotate(${label.angle})` : undefined}>
      <text x={label.dx} dy={label.lift ? "-0.55em" : undefined} textAnchor={label.anchor} dominantBaseline="central" fill={label.tone} stroke="var(--map-label-halo)" strokeLinejoin="round" paintOrder="stroke" className={cn(face, WEIGHT[label.weight], figures)} style={{ fontSize: LABEL_FONT, strokeWidth: LABEL_HALO }} data-map-label="">
        {label.text}
      </text>
    </g>
  );
}

export function PlacedLabels({ frame, labels, testId }: { frame: MapBox; labels: readonly MapLabel[]; testId: string }) {
  return (
    <g data-testid={testId}>
      {labels.map((label) => (
        <MapAt key={label.key} frame={frame} at={label.at} className={label.tier === null ? undefined : TIER_HIDDEN[label.tier]}>
          <LabelText label={label} />
        </MapAt>
      ))}
    </g>
  );
}

export function PeakMarks({ frame, peaks, size }: { frame: MapBox; peaks: readonly PeakLabel[]; size: number }) {
  return (
    <g data-testid="relief-labels">
      {peaks.map((peak) => (
        <MapAt key={peak.key} frame={frame} at={peak.at} className={TIER_HIDDEN[peak.tier]} testId="relief-peak">
          <path d={`M0 ${-size}L${size} ${size * 0.7}L${-size} ${size * 0.7}Z`} fill="var(--ink-1)" stroke="var(--map-label-halo)" strokeWidth={1} />
          <LabelText label={peak.label} />
        </MapAt>
      ))}
    </g>
  );
}

export function LabelScale({ frame }: { frame: MapBox }) {
  const bar = scaleBar(frame);
  const share = `${((bar.length / frame.width) * 100).toFixed(3)}%`;
  const strokes = [
    { stroke: "var(--map-label-halo)", width: 4 },
    { stroke: "var(--map-label)", width: 1.5 }
  ];
  return (
    <svg x="0" y="100%" overflow="visible" data-testid="map-scale" data-km={bar.km}>
      <g transform={`translate(${SCALE_INSET} ${-SCALE_INSET})`}>
        <svg width={share} height="1" overflow="visible">
          {strokes.map((line) => (
            <g key={line.width} fill="none" stroke={line.stroke} strokeWidth={line.width}>
              <line x1="0" y1="0" x2="100%" y2="0" />
              <line x1="0" y1={-SCALE_TICK} x2="0" y2="0" />
              <line x1="100%" y1={-SCALE_TICK} x2="100%" y2="0" />
            </g>
          ))}
        </svg>
        <g transform={`translate(0 ${-(SCALE_TICK + SCALE_TEXT_GAP)})`}>
          <LabelText label={mapLabel("scale", ORIGIN, `${formatNumber(bar.km)} km`, { anchor: "start", numeric: true })} />
        </g>
      </g>
    </svg>
  );
}

export function MapLabelLayer({ children }: { children: ReactNode }) {
  return (
    <svg className="pointer-events-none absolute inset-0 block h-full w-full overflow-hidden [forced-color-adjust:none]" aria-hidden="true" data-testid="map-label-layer">
      {children}
    </svg>
  );
}
