import { RANN_PATH, viewBoxOf } from "@/components/map/basemap";
import type { CodedDam, CodedStillBase } from "@/components/map/codedStillCut";
import { gridTransform, StillWatersLines } from "@/components/map/MapStillLayers";
import { DAM_SHARE } from "@/lib/codedFigureFrame";

export const RELIEF_STEPS_MAX = 7;

function Dams({ dams, width }: { dams: readonly CodedDam[]; width: number }) {
  const size = width * DAM_SHARE;
  return (
    <g data-testid="coded-base-dams">
      {dams.map((dam) => (
        <rect key={`${dam.name}-${dam.x}-${dam.y}`} x={dam.x - size} y={dam.y - size / 3} width={size * 2} height={(size * 2) / 3} fill="var(--map-label)" stroke="var(--map-label-halo)" strokeWidth={1} vectorEffect="non-scaling-stroke" data-name={dam.name} />
      ))}
    </g>
  );
}

export function CodedStillBaseView({ base, dams }: { base: CodedStillBase; dams: readonly CodedDam[] }) {
  const placed = gridTransform(base.box, base.grid);
  const relief = (base.relief ?? []).slice(0, RELIEF_STEPS_MAX);
  return (
    <svg viewBox={viewBoxOf(base.box)} className="pointer-events-none absolute inset-0 block h-full w-full [forced-color-adjust:none]" aria-hidden="true" data-coded-base="">
      <g transform={placed}>
        {base.land ? <path d={base.land} fillRule="evenodd" fill="var(--map-land)" /> : null}
        {relief.map((d, at) => (d ? <path key={`band-${at + 1}`} d={d} fillRule="evenodd" fill={`var(--elevation-${at + 1})`} /> : null))}
        {base.rivers ? <path d={base.rivers} fill="none" stroke="var(--map-river)" strokeWidth={1} vectorEffect="non-scaling-stroke" /> : null}
        {base.districts ? <path d={base.districts} fill="none" stroke="var(--map-border-district)" strokeWidth={0.5} vectorEffect="non-scaling-stroke" /> : null}
        {base.homes ? <path d={base.homes} fill="none" stroke="var(--terracotta)" strokeWidth={1.5} vectorEffect="non-scaling-stroke" /> : null}
      </g>
      {base.waters ? <StillWatersLines box={base.box} grid={base.grid} waters={base.waters} /> : null}
      <path d={RANN_PATH} fill="var(--map-salt)" />
      {base.land ? <path transform={placed} d={base.land} fill="none" stroke="var(--map-border-intl)" strokeWidth={1.2} vectorEffect="non-scaling-stroke" data-testid="coded-base-outline" /> : null}
      <Dams dams={dams} width={base.box.width} />
    </svg>
  );
}
