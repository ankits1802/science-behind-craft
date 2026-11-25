import { DISTRICT_EDGE, PLACE_TONE } from "@/components/map/DistrictLayer";
import type { MapStill, StillDistrict, StillRiver } from "@/components/map/timelineMapStill";
import { riverWidth } from "@/lib/mapPhysical";

export const STRONG_RIVER = 1.8;
export const STRONG_LAKE = 1.4;
export const LAKE_EDGE = 0.6;

export type Strength = { rivers: boolean; water: boolean };

export const PLAIN: Strength = { rivers: false, water: false };

function gridPlacement(still: MapStill): string {
  return `translate(${still.box.x} ${still.box.y}) scale(${(still.box.width / still.grid).toFixed(5)})`;
}

export function shownRiverWidth(rank: number, strong: boolean): number {
  return riverWidth(rank) * (strong ? STRONG_RIVER : 1);
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

export function StillRivers({ still, rivers, lakes, strength = PLAIN }: { still: MapStill; rivers: readonly StillRiver[]; lakes: string | null; strength?: Strength }) {
  return (
    <g className="pointer-events-none" transform={gridPlacement(still)} data-testid="still-rivers">
      {rivers.map((group) => (
        <path key={group.rank} d={group.d} fill="none" stroke="var(--map-river)" strokeWidth={shownRiverWidth(group.rank, strength.rivers)} strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" data-rank={group.rank} />
      ))}
      {lakes ? <path d={lakes} fillRule="evenodd" fill="var(--map-water)" stroke="var(--map-river)" strokeWidth={strength.water ? STRONG_LAKE : LAKE_EDGE} vectorEffect="non-scaling-stroke" /> : null}
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

export function StillNeighbours({ still, d }: { still: MapStill; d: string }) {
  return (
    <g className="pointer-events-none" transform={gridPlacement(still)} data-testid="still-neighbours">
      <path d={d} fillRule="evenodd" fill="var(--map-land-foreign)" />
    </g>
  );
}

export function StillLines({ still, d }: { still: MapStill; d: string }) {
  return (
    <g className="pointer-events-none" transform={gridPlacement(still)} data-testid="still-district-lines">
      <path d={d} fill="none" stroke="var(--map-border-district)" strokeWidth={0.6} strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
    </g>
  );
}

export function StillValued({ still, valued, toneOf }: { still: MapStill; valued: readonly StillDistrict[]; toneOf: (lgd: number) => string | null }) {
  return (
    <g className="pointer-events-none" transform={gridPlacement(still)} data-testid="still-valued">
      {valued.map((district) => {
        const tone = toneOf(district.lgd);
        return tone ? <path key={district.lgd} d={district.d} fillRule="evenodd" className={`${tone} ${DISTRICT_EDGE}`} strokeWidth={0.5} vectorEffect="non-scaling-stroke" data-lgd={district.lgd} /> : null;
      })}
    </g>
  );
}
