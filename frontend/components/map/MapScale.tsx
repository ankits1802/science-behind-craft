import type { MapBox } from "@/components/map/basemap";
import { scaleBar } from "@/components/map/mapDistance";
import { RotatedLabel } from "@/components/map/physical/RotatedLabel";
import { formatNumber } from "@/lib/measure";

export const SCALE_INSET = 14;
export const SCALE_TICK = 5;

export function MapScale({ frame, scale }: { frame: MapBox; scale: number }) {
  const bar = scaleBar(frame);
  const x = frame.x + SCALE_INSET * scale;
  const y = frame.y + frame.height - SCALE_INSET * scale;
  const tick = SCALE_TICK * scale;
  const d = `M${x.toFixed(1)} ${(y - tick).toFixed(1)}V${y.toFixed(1)}H${(x + bar.length).toFixed(1)}V${(y - tick).toFixed(1)}`;
  return (
    <g className="pointer-events-none" data-testid="map-scale" data-km={bar.km}>
      <path d={d} fill="none" stroke="var(--map-label-halo)" strokeWidth={4} vectorEffect="non-scaling-stroke" />
      <path d={d} fill="none" stroke="var(--map-label)" strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
      <RotatedLabel x={x} y={y - tick - 6 * scale} angle={0} anchor="start">
        {`${formatNumber(bar.km)} km`}
      </RotatedLabel>
    </g>
  );
}
