import type { MapBox } from "@/components/map/basemap";
import { ringRadii } from "@/components/map/mapDistance";
import { LABEL_FONT, LabelText, MapAt } from "@/components/map/MapLabelLayer";
import { inFrame, mapLabel } from "@/components/map/placesMapLabels";
import { project, type Projected } from "@/components/map/projection";
import { largestValue, placeRadius, type MapPlace } from "@/lib/componentSpecsGeneral";
import type { MapRingSpec, MapRouteSpec, ShownMarks } from "@/lib/componentSpecsMapLayer";

export const PIN_MIN = 10;
export const LABEL_GAP = 5;
export const CURRENT_GAP = 4;
export const HEAD = 9;
export const BEND = 0.16;
export const EDGE_SHARE = 0.68;

export type PlacedPin = Projected & { r: number };
export type ValueMark = { lgd: number; x: number; y: number; text: string };

const ORIGIN: Projected = { x: 0, y: 0 };

export function pinRadius(place: MapPlace, largest: number): number {
  return Math.max(PIN_MIN, placeRadius(place.value, largest));
}

export function placedPins(places: readonly MapPlace[], scale: number): PlacedPin[] {
  const largest = largestValue(places);
  return places.map((place) => ({ ...project(place.longitude, place.latitude), r: pinRadius(place, largest) * scale }));
}

const unit = (from: Projected, to: Projected): Projected => {
  const length = Math.hypot(to.x - from.x, to.y - from.y) || 1;
  return { x: (to.x - from.x) / length, y: (to.y - from.y) / length };
};

export function routeGeometry(from: PlacedPin, to: PlacedPin, scale: number): { d: string; head: string } {
  const length = Math.hypot(to.x - from.x, to.y - from.y);
  const along = unit(from, to);
  const control = { x: (from.x + to.x) / 2 - along.y * length * BEND, y: (from.y + to.y) / 2 + along.x * length * BEND };
  const leave = unit(from, control);
  const arrive = unit(control, to);
  const start = { x: from.x + leave.x * (from.r + LABEL_GAP * scale), y: from.y + leave.y * (from.r + LABEL_GAP * scale) };
  const tip = { x: to.x - arrive.x * (to.r + 2 * scale), y: to.y - arrive.y * (to.r + 2 * scale) };
  const size = HEAD * scale;
  const base = { x: tip.x - arrive.x * size, y: tip.y - arrive.y * size };
  const wing = { x: -arrive.y * size * 0.55, y: arrive.x * size * 0.55 };
  const f = (point: Projected) => `${point.x.toFixed(1)} ${point.y.toFixed(1)}`;
  return {
    d: `M${f(start)}Q${f(control)} ${f(base)}`,
    head: `M${f(tip)}L${f({ x: base.x + wing.x, y: base.y + wing.y })}L${f({ x: base.x - wing.x, y: base.y - wing.y })}Z`
  };
}

export function MapRoutes({ routes, pins, marks, scale }: { routes: readonly MapRouteSpec[]; pins: readonly PlacedPin[]; marks: ShownMarks; scale: number }) {
  return (
    <g className="pointer-events-none" data-testid="map-routes">
      {routes.map((route, at) => {
        if (!marks.routes.has(at) || !pins[route.start] || !pins[route.end]) return null;
        const { d, head } = routeGeometry(pins[route.start], pins[route.end], scale);
        return (
          <g key={`${route.start}-${route.end}-${route.text}`} data-testid="map-route">
            <path d={d} fill="none" stroke="var(--map-selection-halo)" strokeWidth={7} strokeLinecap="round" vectorEffect="non-scaling-stroke" />
            <path d={d} fill="none" stroke="var(--map-selection)" strokeWidth={2.4} strokeLinecap="round" vectorEffect="non-scaling-stroke" />
            <path d={head} fill="var(--map-selection)" stroke="var(--map-selection-halo)" strokeWidth={1} vectorEffect="non-scaling-stroke" />
          </g>
        );
      })}
    </g>
  );
}

export function MapRings({ rings, places, marks }: { rings: readonly MapRingSpec[]; places: readonly MapPlace[]; marks: ShownMarks }) {
  return (
    <g className="pointer-events-none" data-testid="map-rings">
      {rings.map((ring, at) => {
        const place = places[ring.place];
        if (!marks.rings.has(at) || !place) return null;
        const centre = project(place.longitude, place.latitude);
        const { rx, ry } = ringRadii(place, ring.radiusKm);
        return (
          <g key={`${ring.place}-${ring.radiusKm}`} data-testid="map-ring" data-km={ring.radiusKm}>
            <ellipse cx={centre.x} cy={centre.y} rx={rx} ry={ry} fill="none" stroke="var(--map-selection-halo)" strokeWidth={4} vectorEffect="non-scaling-stroke" />
            <ellipse cx={centre.x} cy={centre.y} rx={rx} ry={ry} fill="none" stroke="var(--map-selection)" strokeWidth={1.4} strokeDasharray="5 4" vectorEffect="non-scaling-stroke" />
          </g>
        );
      })}
    </g>
  );
}

function PinName({ name, radius, late }: { name: string; radius: number; late: boolean }) {
  if (!name) return null;
  const gap = radius + LABEL_GAP;
  return <LabelText label={mapLabel("name", ORIGIN, name, { anchor: late ? "end" : "start", dx: late ? -gap : gap, weight: "medium" })} />;
}

type PinProps = { places: readonly MapPlace[]; marks: ShownMarks; frame: MapBox; nameOf: (ref: string) => string };

export function PlacePins({ places, marks, frame, nameOf }: PinProps) {
  const largest = largestValue(places);
  return (
    <g data-testid="map-places">
      {places.map((place, at) => {
        const centre = project(place.longitude, place.latitude);
        if (!marks.places.has(at) || !inFrame(frame, centre)) return null;
        const current = marks.current.has(at);
        const radius = pinRadius(place, largest);
        const late = centre.x > frame.x + frame.width * EDGE_SHARE;
        return (
          <MapAt key={place.reading} frame={frame} at={centre}>
            <g data-testid="map-place" data-current={current ? "" : undefined}>
              {current ? <circle r={radius + CURRENT_GAP} fill="none" stroke="var(--map-selection-halo)" strokeWidth={5} /> : null}
              {current ? <circle r={radius + CURRENT_GAP} fill="none" stroke="var(--map-selection)" strokeWidth={2} /> : null}
              <circle r={radius} fill={place.value === null ? "var(--map-marker)" : "var(--chart-series)"} stroke="var(--map-marker-ring)" strokeWidth={1.5} />
              <text textAnchor="middle" dominantBaseline="central" className="font-ui font-semibold [font-variant-numeric:lining-nums_tabular-nums]" fill={place.value === null ? "var(--map-label)" : "var(--map-marker)"} style={{ fontSize: LABEL_FONT }} data-map-label="">
                {at + 1}
              </text>
              <PinName name={nameOf(place.name)} radius={radius} late={late} />
            </g>
          </MapAt>
        );
      })}
    </g>
  );
}
