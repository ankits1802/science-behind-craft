import { PLACE_TONE } from "@/components/map/DistrictLayer";
import type { MapStill, StillRiver } from "@/components/map/timelineMapStill";
import { riverWidth } from "@/lib/mapPhysical";

function gridPlacement(still: MapStill): string {
  return `translate(${still.box.x} ${still.box.y}) scale(${(still.box.width / still.grid).toFixed(5)})`;
}

export function StillRelief({ still, bands }: { still: MapStill; bands: readonly string[] }) {
  return (
    <g className="pointer-events-none" transform={gridPlacement(still)} data-testid="still-relief">
      {bands.map((d, at) =>
        d ? (
          <path
            key={`band-${at + 1}`}
            d={d}
            fillRule="evenodd"
            fill={`var(--elevation-${at + 1})`}
            stroke={at > 0 ? "var(--map-border-district)" : undefined}
            strokeWidth={at > 0 ? 0.5 : undefined}
            vectorEffect="non-scaling-stroke"
            data-step={at + 1}
          />
        ) : null
      )}
    </g>
  );
}

export function StillRivers({ still, rivers, lakes }: { still: MapStill; rivers: readonly StillRiver[]; lakes: string | null }) {
  return (
    <g className="pointer-events-none" transform={gridPlacement(still)} data-testid="still-rivers">
      {rivers.map((group) => (
        <path key={group.rank} d={group.d} fill="none" stroke="var(--map-river)" strokeWidth={riverWidth(group.rank)} strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" data-rank={group.rank} />
      ))}
      {lakes ? <path d={lakes} fillRule="evenodd" fill="var(--map-water)" stroke="var(--map-river)" strokeWidth={0.6} vectorEffect="non-scaling-stroke" /> : null}
    </g>
  );
}

export function StillHome({ d }: { d: string }) {
  return (
    <g className="pointer-events-none" data-testid="still-home">
      <path d={d} fillRule="evenodd" className={PLACE_TONE} vectorEffect="non-scaling-stroke" />
    </g>
  );
}
