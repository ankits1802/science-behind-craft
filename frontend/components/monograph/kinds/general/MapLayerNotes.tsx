import type { ReactNode } from "react";

import type { MapLayerSpec } from "@/lib/componentSpecsGeneral";
import { formatNumber } from "@/lib/measure";

type RenderUnit = (ref: string) => ReactNode;
type Note = { key: string; label: string; text: string };

export const MOVE_LABEL = "Move";

export function markNotes(layer: MapLayerSpec): Note[] {
  const routes = (layer.routes ?? []).map((route, at) => ({ key: `route-${at}`, label: MOVE_LABEL, text: route.text }));
  const rings = (layer.rings ?? []).map((ring, at) => ({ key: `ring-${at}`, label: `Within ${formatNumber(ring.radiusKm)} km`, text: ring.text }));
  return [...routes, ...rings];
}

export function MarkNotes({ layer, renderUnit }: { layer: MapLayerSpec; renderUnit: RenderUnit }) {
  const notes = markNotes(layer);
  if (!notes.length) return null;
  return (
    <ul className="grid" data-testid="map-notes">
      {notes.map((note) => (
        <li key={note.key} className="grid gap-0.5 border-t border-rule py-2">
          <p className="font-ui text-label text-ink-3">{note.label}</p>
          <div className="font-reading text-body-sm text-ink-1">{renderUnit(note.text)}</div>
        </li>
      ))}
    </ul>
  );
}

export function DistrictList({ layer, renderUnit }: { layer: MapLayerSpec; renderUnit: RenderUnit }) {
  if (!layer.districts) return null;
  const ranked = [...layer.districts.values].sort((one, other) => other.value - one.value);
  return (
    <div className="grid content-start gap-2" data-testid="map-district-list">
      <p className="border-t border-ink-1 pt-3 font-ui text-label text-ink-1">{renderUnit(layer.districts.valueLabel)}</p>
      <ol className="grid">
        {ranked.map((value) => (
          <li key={value.district} className="grid grid-cols-[3.5rem_minmax(0,1fr)] gap-2 border-t border-rule py-2">
            <span className="font-ui text-label font-semibold text-ink-1 [font-variant-numeric:lining-nums_tabular-nums]">{formatNumber(value.value)}</span>
            <div className="font-reading text-body-sm text-ink-1">{renderUnit(value.reading)}</div>
          </li>
        ))}
      </ol>
    </div>
  );
}
