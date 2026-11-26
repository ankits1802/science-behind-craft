import { DISTRICT_EDGE, PLACE_TONE } from "@/components/map/DistrictLayer";
import type { MapBox } from "@/components/map/basemap";
import type { MapStill, StillDistrict, StillRiver } from "@/components/map/timelineMapStill";
import type { StillWaters } from "@/components/map/waterLayer";
import { riverWidth } from "@/lib/mapPhysical";

export const STRONG_RIVER = 1.8;
export const STRONG_LAKE = 1.4;
export const LAKE_EDGE = 0.6;
export const WATER_WIDTH = 0.8;
export const STRONG_WATER = 2.2;
export const WATER_HALO = 5;

export type Strength = { rivers: boolean; water: boolean };

export const PLAIN: Strength = { rivers: false, water: false };

export function gridTransform(box: MapBox, grid: number): string {
  return `translate(${box.x} ${box.y}) scale(${(box.width / grid).toFixed(5)})`;
}

function gridPlacement(still: MapStill): string {
  return gridTransform(still.box, still.grid);
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

export function StillStates({ still, d }: { still: MapStill; d: string }) {
  return (
    <g className="pointer-events-none" transform={gridPlacement(still)} data-testid="still-states">
      <path d={d} fill="none" stroke="var(--map-border-state)" strokeWidth={0.75} strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
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

export function StillWatersLines({ box, grid, waters }: { box: MapBox; grid: number; waters: StillWaters }) {
  return (
    <g className="pointer-events-none" transform={gridTransform(box, grid)} fill="none" strokeLinecap="round" strokeLinejoin="round" data-testid="still-waters">
      {waters.d ? <path d={waters.d} stroke="var(--map-river)" strokeWidth={WATER_WIDTH} vectorEffect="non-scaling-stroke" /> : null}
      {waters.strong.map((river) => (
        <g key={river.name} data-testid="still-water-strong" data-name={river.name}>
          <path d={river.d} stroke="var(--map-label-halo)" strokeWidth={WATER_HALO} vectorEffect="non-scaling-stroke" />
          <path d={river.d} stroke="var(--map-river)" strokeWidth={STRONG_WATER} vectorEffect="non-scaling-stroke" />
        </g>
      ))}
    </g>
  );
}
