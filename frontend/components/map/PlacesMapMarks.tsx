import type { MapBox } from "@/components/map/basemap";
import { HALO_WIDTH, LABEL_SIZE } from "@/components/map/MapCanvas";
import { ringRadii, scaleBar } from "@/components/map/mapLayerFrame";
import { RotatedLabel } from "@/components/map/physical/RotatedLabel";
import { project, type Projected } from "@/components/map/projection";
import { placeRadius, type MapPlace } from "@/lib/componentSpecsGeneral";
import type { MapRingSpec, MapRouteSpec, ShownMarks } from "@/lib/componentSpecsMapLayer";
import { formatNumber } from "@/lib/measure";

export const PIN_MIN = 10;
export const LABEL_GAP = 5;
export const HEAD = 9;
export const BEND = 0.16;
export const EDGE_SHARE = 0.68;
export const SCALE_INSET = 14;
export const SCALE_TICK = 5;

export type PlacedPin = Projected & { r: number };
export type ValueMark = { lgd: number; x: number; y: number; text: string };

const TEXT_STYLE = { fontSize: LABEL_SIZE, strokeWidth: HALO_WIDTH };

export function placedPins(places: readonly MapPlace[], scale: number): PlacedPin[] {
  const largest = Math.max(0, ...places.map((place) => place.value ?? 0));
  return places.map((place) => ({ ...project(place.longitude, place.latitude), r: Math.max(PIN_MIN, placeRadius(place.value, largest)) * scale }));
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

export function MapRings({ rings, places, marks, scale }: { rings: readonly MapRingSpec[]; places: readonly MapPlace[]; marks: ShownMarks; scale: number }) {
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
            <RotatedLabel x={centre.x} y={centre.y - ry - 4 * scale} angle={0} weight="medium">
              {`${formatNumber(ring.radiusKm)} km`}
            </RotatedLabel>
          </g>
        );
      })}
    </g>
  );
}

type PinProps = { places: readonly MapPlace[]; pins: readonly PlacedPin[]; marks: ShownMarks; frame: MapBox; scale: number; nameOf: (ref: string) => string };

function PinLabel({ pin, name, frame, scale }: { pin: PlacedPin; name: string; frame: MapBox; scale: number }) {
  if (!name) return null;
  const late = pin.x > frame.x + frame.width * EDGE_SHARE;
  const gap = pin.r + LABEL_GAP * scale;
  return (
    <RotatedLabel x={pin.x} y={pin.y} angle={0} dx={late ? -gap : gap} anchor={late ? "end" : "start"} weight="medium">
      {name}
    </RotatedLabel>
  );
}

export function PlacePins({ places, pins, marks, frame, scale, nameOf }: PinProps) {
  return (
    <g data-testid="map-places">
      {places.map((place, at) => {
        const pin = pins[at];
        if (!marks.places.has(at) || !pin) return null;
        const current = marks.current.has(at);
        return (
          <g key={place.reading} data-testid="map-place" data-current={current ? "" : undefined}>
            {current ? <circle cx={pin.x} cy={pin.y} r={pin.r + 4 * scale} fill="none" stroke="var(--map-selection-halo)" strokeWidth={5} vectorEffect="non-scaling-stroke" /> : null}
            {current ? <circle cx={pin.x} cy={pin.y} r={pin.r + 4 * scale} fill="none" stroke="var(--map-selection)" strokeWidth={2} vectorEffect="non-scaling-stroke" /> : null}
            <circle cx={pin.x} cy={pin.y} r={pin.r} fill={place.value === null ? "var(--map-marker)" : "var(--chart-series)"} stroke="var(--map-marker-ring)" strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
            <text x={pin.x} y={pin.y} textAnchor="middle" dominantBaseline="central" className="pointer-events-none font-ui font-semibold [font-variant-numeric:lining-nums_tabular-nums]" fill={place.value === null ? "var(--map-label)" : "var(--map-marker)"} style={{ fontSize: LABEL_SIZE }}>
              {at + 1}
            </text>
            <PinLabel pin={pin} name={nameOf(place.name)} frame={frame} scale={scale} />
          </g>
        );
      })}
    </g>
  );
}

export function ValueLabels({ values }: { values: readonly ValueMark[] }) {
  return (
    <g className="pointer-events-none" data-testid="map-district-values">
      {values.map((value) => (
        <text key={value.lgd} x={value.x} y={value.y} textAnchor="middle" dominantBaseline="central" fill="var(--map-label)" stroke="var(--map-label-halo)" strokeLinejoin="round" paintOrder="stroke" className="font-ui font-semibold [font-variant-numeric:lining-nums_tabular-nums]" style={TEXT_STYLE}>
          {value.text}
        </text>
      ))}
    </g>
  );
}

export function MapScale({ frame, scale }: { frame: MapBox; scale: number }) {
  const bar = scaleBar(frame);
  const x = frame.x + SCALE_INSET * scale;
  const y = frame.y + frame.height - SCALE_INSET * scale;
  const tick = SCALE_TICK * scale;
  return (
    <g className="pointer-events-none" data-testid="map-scale" data-km={bar.km}>
      <path d={`M${x} ${y - tick}V${y}H${x + bar.length}V${y - tick}`} fill="none" stroke="var(--map-label-halo)" strokeWidth={4} vectorEffect="non-scaling-stroke" />
      <path d={`M${x} ${y - tick}V${y}H${x + bar.length}V${y - tick}`} fill="none" stroke="var(--map-label)" strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
      <RotatedLabel x={x} y={y - tick - 6 * scale} angle={0} anchor="start">
        {`${formatNumber(bar.km)} km`}
      </RotatedLabel>
    </g>
  );
}
