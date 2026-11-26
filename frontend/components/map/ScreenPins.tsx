import type { MapBox } from "@/components/map/basemap";
import type { PlacedPin } from "@/components/map/layout";
import { LABEL_FONT, MapAt } from "@/components/map/MapLabelLayer";
import { CURRENT_GAP, PIN_MIN } from "@/components/map/PlacesMapMarks";

export function ScreenPins({ frame, pins, active }: { frame: MapBox; pins: readonly PlacedPin[]; active: readonly string[] }) {
  return (
    <g data-testid="map-pins">
      {pins.map((pin) => {
        const shown = active.includes(pin.point.key);
        return (
          <MapAt key={pin.point.key} frame={frame} at={{ x: pin.x, y: pin.y }}>
            <g data-testid="map-pin" data-active={shown ? "" : undefined}>
              {shown ? <circle r={PIN_MIN + CURRENT_GAP} fill="none" stroke="var(--map-selection-halo)" strokeWidth={4} /> : null}
              {shown ? <circle r={PIN_MIN + CURRENT_GAP} fill="none" stroke="var(--map-selection)" strokeWidth={2} /> : null}
              <circle r={PIN_MIN} fill="var(--map-marker)" stroke="var(--map-marker-ring)" strokeWidth={1.5} />
              <text textAnchor="middle" dominantBaseline="central" fill="var(--map-label)" className="font-ui font-semibold [font-variant-numeric:lining-nums_tabular-nums]" style={{ fontSize: LABEL_FONT }} data-map-label="" data-testid="map-pin-label">
                {pin.point.pinLabel ?? String(pin.point.total)}
              </text>
            </g>
          </MapAt>
        );
      })}
    </g>
  );
}
