"use client";

import { useId, useMemo } from "react";

import { mapLayerDrawn } from "@/components/map/mapLayerFrame";
import { PlacesMap } from "@/components/map/PlacesMap";
import { GeneralFigure, type RenderUnit } from "@/components/monograph/kinds/general/GeneralFigure";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { mapLayerSpecShape, parsedSpec, type MapLayerSpec, type MapPlace } from "@/lib/componentSpecsGeneral";
import { homeDistrictsOf, shownMarks, type ShownMarks } from "@/lib/componentSpecsMapLayer";
import { cn } from "@/lib/utils";

import { MapSequence } from "./MapSequence";
import { useMapSequence } from "./useMapSequence";

const NO_TEXT = () => "";

export function largestValue(places: readonly MapPlace[]): number {
  return Math.max(0, ...places.map((place) => place.value ?? 0));
}

function PlaceList({ places, valueLabel, marks, renderUnit }: { places: MapPlace[]; valueLabel: string | null; marks: ShownMarks; renderUnit: RenderUnit }) {
  return (
    <div className="grid content-start gap-2">
      {valueLabel ? <p className="font-ui text-caption text-ink-3">{renderUnit(valueLabel)}</p> : null}
      <ol className="grid" data-testid="general-places">
        {places.map((place, at) => (
          <li key={place.reading} className={cn("grid grid-cols-[1.75rem_minmax(0,1fr)] gap-2 border-t border-rule py-2", marks.current.has(at) ? "border-s-2 border-s-ink-1 ps-2" : null)} aria-current={marks.current.has(at) ? "step" : undefined}>
            <span className="font-ui text-label text-ink-2 [font-variant-numeric:lining-nums_tabular-nums]">{at + 1}</span>
            <div className="grid min-w-0 gap-0.5">
              <p className="font-ui text-ui font-medium text-ink-1">{renderUnit(place.name)}</p>
              <p className="font-reading text-body-sm text-ink-1">{renderUnit(place.reading)}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

function PlacedLayer({ layer, home, labelledBy, renderUnit, nameOf }: { layer: MapLayerSpec; home: number[]; labelledBy: string; renderUnit: RenderUnit; nameOf: (ref: string) => string }) {
  const steps = layer.sequence ?? [];
  const { at, playing, watch, choose, toggle } = useMapSequence(steps.length);
  const drawn = useMemo(() => mapLayerDrawn(layer, home), [layer, home]);
  const marks = useMemo(() => shownMarks(layer, layer.places.length, at), [layer, at]);
  return (
    <div ref={watch} className="grid gap-5 md:grid-cols-[minmax(0,1.5fr)_minmax(15rem,1fr)] md:items-start" data-testid="places-map-figure" data-step={steps.length ? at : undefined}>
      <div className="grid min-w-0 gap-3">
        <PlacesMap spec={layer} drawn={drawn} marks={marks} labelledBy={labelledBy} nameOf={nameOf} renderUnit={renderUnit} />
        {steps.length > 1 ? <MapSequence steps={steps} play={{ at, playing, choose, toggle }} renderUnit={renderUnit} nameOf={nameOf} /> : null}
      </div>
      <PlaceList places={layer.places} valueLabel={layer.valueLabel} marks={marks} renderUnit={renderUnit} />
    </div>
  );
}

export function MapLayerView({ component, spec, renderUnit, unitText }: ComponentViewProps) {
  const layer = useMemo(() => parsedSpec(mapLayerSpecShape, spec), [spec]);
  const home = useMemo(() => homeDistrictsOf(component.subjects), [component.subjects]);
  const titleId = useId();
  if (!layer) return null;
  return (
    <GeneralFigure kind="map_layer" head={layer.head} dataset={layer.dataset} titleId={titleId} renderUnit={renderUnit}>
      <PlacedLayer layer={layer} home={home} labelledBy={titleId} renderUnit={renderUnit} nameOf={unitText ?? NO_TEXT} />
    </GeneralFigure>
  );
}
