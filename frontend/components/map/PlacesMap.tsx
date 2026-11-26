"use client";

import { useCallback, useMemo, useRef, type ReactNode } from "react";

import { AnswerMapSource } from "@/components/answer/place/AnswerMapSource";
import { useFitScale } from "@/components/charts/useFitScale";
import { DatasetCredit } from "@/components/DatasetCredit";
import { useRemote } from "@/components/hooks/useRemote";
import { RANN_PATH, viewBoxOf, type MapBox } from "@/components/map/basemap";
import { loadBorders } from "@/components/map/borderGeometry";
import { choroplethColour, choroplethTone, MapLegend, placeExtra, SALT_EXTRA } from "@/components/map/ChoroplethLegend";
import { DistrictFills } from "@/components/map/DistrictLayer";
import { IndiaLocator, LOCATOR_INSET, locatorLabel } from "@/components/map/IndiaLocator";
import { IndiaMapBase } from "@/components/map/IndiaMap";
import { showsDistrictLines, type MapLayerDrawn } from "@/components/map/mapLayerFrame";
import { StillLines, StillNeighbours, StillValued } from "@/components/map/MapStillLayers";
import { PlaceHatchOrStill } from "@/components/map/PlaceHatch";
import { MapRings, MapRoutes, placedPins, type ValueMark } from "@/components/map/PlacesMapMarks";
import { PlacesOverlay } from "@/components/map/PlacesOverlay";
import { bordersToPath, project } from "@/components/map/projection";
import { loadShapes, type DistrictShape } from "@/components/map/shapeGeometry";
import type { MapStill } from "@/components/map/timelineMapStill";
import { useTimelineMapLayers } from "@/components/map/TimelineMapLayers";
import type { MapLayerSpec } from "@/lib/componentSpecsGeneral";
import { valueClasses, valueClassOf, type ShownMarks, type ValueClass } from "@/lib/componentSpecsMapLayer";
import { fetchMapLayers } from "@/lib/mapLayers";
import { formatNumber } from "@/lib/measure";

export const HOME_LABEL = "The craft's home district";
export const KEY_TITLE = "On the map";

type RenderUnit = (ref: string) => ReactNode;
type Values = { classes: ValueClass[]; toneOf: (lgd: number) => string | null; fills: ReactNode; labels: ValueMark[] };
export type PlacesMapProps = { spec: MapLayerSpec; drawn: MapLayerDrawn; marks: ShownMarks; labelledBy: string; nameOf: (ref: string) => string; renderUnit: RenderUnit };

const RANN_X = RANN_PATH.match(/-?\d+(\.\d+)?/g)?.map(Number) ?? [];

export function holdsSalt(frame: MapBox): boolean {
  for (let at = 0; at + 1 < RANN_X.length; at += 2) {
    const x = RANN_X[at];
    const y = RANN_X[at + 1];
    if (x >= frame.x && x <= frame.x + frame.width && y >= frame.y && y <= frame.y + frame.height) return true;
  }
  return false;
}

function DistrictLinesOrStill({ still, frame }: { still: MapStill | null; frame: MapBox }) {
  const load = useCallback(() => loadBorders("district").then(bordersToPath), []);
  const loaded = useRemote(still?.lines || !showsDistrictLines(frame) ? null : load).data;
  if (still?.lines) return <StillLines still={still} d={still.lines} />;
  return loaded ? <path d={loaded} fill="none" stroke="var(--map-border-district)" strokeWidth={0.6} strokeLinejoin="round" vectorEffect="non-scaling-stroke" className="pointer-events-none" data-testid="map-district-lines" /> : null;
}

function valueMarks(spec: MapLayerSpec, centre: (lgd: number) => { x: number; y: number } | null): ValueMark[] {
  return (spec.districts?.values ?? []).flatMap((value) => {
    const at = centre(value.district);
    return at ? [{ lgd: value.district, x: at.x, y: at.y, text: formatNumber(value.value) }] : [];
  });
}

function useDistrictValues(spec: MapLayerSpec, still: MapStill | null): Values {
  const values = spec.districts?.values;
  const classes = useMemo(() => valueClasses((values ?? []).map((value) => value.value)), [values]);
  const byDistrict = useMemo(() => new Map((values ?? []).map((value) => [value.district, value.value])), [values]);
  const held = still?.valued ?? null;
  const shapes = useRemote(values && !held ? loadShapes : null).data;
  const toneOf = useCallback((lgd: number) => {
    const value = byDistrict.get(lgd);
    return value === undefined ? null : choroplethTone(valueClassOf(value, classes), classes.length);
  }, [byDistrict, classes]);
  const fillOf = useCallback((shape: DistrictShape) => toneOf(shape.lgd), [toneOf]);
  if (held && still) {
    const centres = new Map(held.map((district) => [district.lgd, district]));
    return { classes, toneOf, fills: <StillValued still={still} valued={held} toneOf={toneOf} />, labels: valueMarks(spec, (lgd) => centres.get(lgd) ?? null) };
  }
  const found = new Map((shapes ?? []).map((shape) => [shape.lgd, shape]));
  const centre = (lgd: number) => {
    const shape = found.get(lgd);
    return shape ? project(shape.centroid[0], shape.centroid[1]) : null;
  };
  return { classes, toneOf, fills: shapes ? <DistrictFills shapes={shapes} fillOf={fillOf} /> : null, labels: shapes ? valueMarks(spec, centre) : [] };
}

function PlacesKey({ spec, drawn, values, layerKey, renderUnit }: { spec: MapLayerSpec; drawn: MapLayerDrawn; values: Values; layerKey: ReactNode; renderUnit: RenderUnit }) {
  const extras = [...(drawn.names.home.length ? [placeExtra(HOME_LABEL)] : []), ...(holdsSalt(drawn.frame) ? [SALT_EXTRA] : [])];
  const steps = values.classes.map((band, at) => ({ label: band.label, colour: choroplethColour(at, values.classes.length) }));
  const title = spec.districts ? renderUnit(spec.districts.valueLabel) : KEY_TITLE;
  return (
    <div className="grid min-w-0 gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]" data-testid="places-map-key">
      {steps.length || extras.length ? <MapLegend title={title} steps={steps} extras={extras} /> : null}
      {layerKey}
    </div>
  );
}

function PlacesSource({ still, credits }: { still: MapStill | null; credits: MapStill["credits"] }) {
  const listed = useRemote(still?.boundary ? null : fetchMapLayers).data;
  const boundary = still?.boundary ?? listed?.boundary ?? null;
  return (
    <div className="grid gap-2 font-ui text-caption text-ink-3" data-testid="places-map-source">
      <p>
        <AnswerMapSource boundary={boundary} />
      </p>
      {(credits ?? []).map((dataset) => (
        <DatasetCredit key={dataset.code} dataset={dataset} />
      ))}
    </div>
  );
}

export function PlacesMap({ spec, drawn, marks, labelledBy, nameOf, renderUnit }: PlacesMapProps) {
  const map = useRef<SVGSVGElement | null>(null);
  const { frame, still } = drawn;
  const scale = useFitScale(map, frame.width);
  const layerNames = useMemo(() => ({ ...drawn.names, home: [] }), [drawn.names]);
  const layers = useTimelineMapLayers(layerNames, still);
  const values = useDistrictValues(spec, still);
  const pins = useMemo(() => placedPins(spec.places, scale), [spec.places, scale]);
  const underlay = (
    <>
      {still?.neighbours ? <StillNeighbours still={still} d={still.neighbours} /> : null}
      {layers.parts.relief}
      {marks.districts ? values.fills : null}
      <DistrictLinesOrStill still={still} frame={frame} />
      {layers.parts.rivers}
      <PlaceHatchOrStill still={still?.home ?? null} home={drawn.names.home} frame={frame} scale={scale} />
    </>
  );
  return (
    <div className="grid min-w-0 gap-3" data-testid="places-map">
      <div className="relative min-w-0 overflow-hidden rounded-plate border border-rule">
        <svg ref={map} viewBox={viewBoxOf(frame)} role="img" aria-labelledby={labelledBy} className="block h-auto w-full [forced-color-adjust:none]" data-fit="" data-testid="general-map">
          <IndiaMapBase underlay={underlay} frame={frame} />
          <MapRings rings={spec.rings ?? []} places={spec.places} marks={marks} />
          <MapRoutes routes={spec.routes ?? []} pins={pins} marks={marks} scale={scale} />
        </svg>
        <PlacesOverlay spec={spec} frame={frame} marks={marks} values={values.labels} files={layers.files} named={layerNames.emphasis?.rivers ?? []} nameOf={nameOf} />
        <IndiaLocator marked={[]} frame={frame} label={locatorLabel([])} className={LOCATOR_INSET} />
      </div>
      <PlacesKey spec={spec} drawn={drawn} values={values} layerKey={layers.key} renderUnit={renderUnit} />
      <PlacesSource still={still} credits={still?.credits ?? layers.credits} />
    </div>
  );
}
