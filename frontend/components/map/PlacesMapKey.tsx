"use client";

import type { ReactNode } from "react";

import { AnswerMapSource } from "@/components/answer/place/AnswerMapSource";
import { DatasetCredit } from "@/components/DatasetCredit";
import { useRemote } from "@/components/hooks/useRemote";
import { RANN_PATH, type MapBox } from "@/components/map/basemap";
import { choroplethColour, MapLegend, placeExtra, SALT_EXTRA, type LegendExtra } from "@/components/map/ChoroplethLegend";
import type { MapStill } from "@/components/map/timelineMapStill";
import type { StillWaters } from "@/components/map/waterLayer";
import type { MapLayerSpec } from "@/lib/componentSpecsGeneral";
import type { ValueClass } from "@/lib/componentSpecsMapLayer";
import { fetchMapLayers } from "@/lib/mapLayers";
import type { RegionDataset } from "@/lib/regionContract";

export const HOME_LABEL = "The craft's home district";
export const KEY_TITLE = "On the map";
export const DAM_LABEL = "Dam, by the name OpenStreetMap gives it";
export const DAM_EXTRA: LegendExtra = { key: "dam", label: DAM_LABEL, fill: "var(--map-label)" };

type RenderUnit = (ref: string) => ReactNode;
type KeyedMap = { frame: MapBox; home: readonly number[]; waters: StillWaters | null };

const RANN_X = RANN_PATH.match(/-?\d+(\.\d+)?/g)?.map(Number) ?? [];

export function holdsSalt(frame: MapBox): boolean {
  for (let at = 0; at + 1 < RANN_X.length; at += 2) {
    const x = RANN_X[at];
    const y = RANN_X[at + 1];
    if (x >= frame.x && x <= frame.x + frame.width && y >= frame.y && y <= frame.y + frame.height) return true;
  }
  return false;
}

function keyExtras({ frame, home, waters }: KeyedMap): LegendExtra[] {
  return [...(home.length ? [placeExtra(HOME_LABEL)] : []), ...(holdsSalt(frame) ? [SALT_EXTRA] : []), ...(waters?.dams.length ? [DAM_EXTRA] : [])];
}

export function PlacesKey({ spec, keyed, classes, layerKey, renderUnit }: { spec: Pick<MapLayerSpec, "districts">; keyed: KeyedMap; classes: readonly ValueClass[]; layerKey: ReactNode; renderUnit: RenderUnit }) {
  const extras = keyExtras(keyed);
  const steps = classes.map((band, at) => ({ label: band.label, colour: choroplethColour(at, classes.length) }));
  const title = spec.districts ? renderUnit(spec.districts.valueLabel) : KEY_TITLE;
  return (
    <div className="grid min-w-0 gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]" data-testid="places-map-key">
      {steps.length || extras.length ? <MapLegend title={title} steps={steps} extras={extras} /> : null}
      {layerKey}
    </div>
  );
}

export function PlacesSource({ still, credits }: { still: MapStill | null; credits: readonly RegionDataset[] }) {
  const listed = useRemote(still?.boundary ? null : fetchMapLayers).data;
  const boundary = still?.boundary ?? listed?.boundary ?? null;
  return (
    <div className="grid gap-2 font-ui text-caption text-ink-3" data-testid="places-map-source">
      <p>
        <AnswerMapSource boundary={boundary} />
      </p>
      {credits.map((dataset) => (
        <DatasetCredit key={dataset.code} dataset={dataset} />
      ))}
    </div>
  );
}
