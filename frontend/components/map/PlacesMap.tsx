"use client";

import { useCallback, useMemo, useRef, type ReactNode } from "react";

import { useFitScale } from "@/components/charts/useFitScale";
import { useRemote } from "@/components/hooks/useRemote";
import { viewBoxOf, type MapBox } from "@/components/map/basemap";
import { loadBorders } from "@/components/map/borderGeometry";
import { choroplethTone } from "@/components/map/ChoroplethLegend";
import { DistrictFills } from "@/components/map/DistrictLayer";
import { IndiaLocator, LOCATOR_INSET, locatorLabel } from "@/components/map/IndiaLocator";
import { IndiaMapBase } from "@/components/map/IndiaMap";
import { showsDistrictLines, type MapLayerDrawn } from "@/components/map/mapLayerFrame";
import { StillLines, StillNeighbours, StillStates, StillValued, StillWatersLines } from "@/components/map/MapStillLayers";
import { PlaceHatchOrStill } from "@/components/map/PlaceHatch";
import { PlacesKey, PlacesSource } from "@/components/map/PlacesMapKey";
import { MapRings, MapRoutes, placedPins, type ValueMark } from "@/components/map/PlacesMapMarks";
import { PlacesOverlay } from "@/components/map/PlacesOverlay";
import { bordersToPath, project } from "@/components/map/projection";
import { loadShapes, type DistrictShape } from "@/components/map/shapeGeometry";
import type { MapStill } from "@/components/map/timelineMapStill";
import { useTimelineMapLayers } from "@/components/map/TimelineMapLayers";
import type { MapLayerSpec } from "@/lib/componentSpecsGeneral";
import { valueClasses, valueClassOf, type ShownMarks, type ValueClass } from "@/lib/componentSpecsMapLayer";
import { formatNumber } from "@/lib/measure";

type RenderUnit = (ref: string) => ReactNode;
type Values = { classes: ValueClass[]; toneOf: (lgd: number) => string | null; fills: ReactNode; labels: ValueMark[] };
export type PlacesMapProps = { spec: MapLayerSpec; drawn: MapLayerDrawn; marks: ShownMarks; labelledBy: string; nameOf: (ref: string) => string; renderUnit: RenderUnit };

function DistrictLinesOrStill({ still, frame }: { still: MapStill | null; frame: MapBox }) {
  const load = useCallback(() => loadBorders("district").then(bordersToPath), []);
  const loaded = useRemote(still?.lines || !showsDistrictLines(frame) ? null : load).data;
  if (still?.lines) return <StillLines still={still} d={still.lines} />;
  return loaded ? <path d={loaded} fill="none" stroke="var(--map-border-district)" strokeWidth={0.6} strokeLinejoin="round" vectorEffect="non-scaling-stroke" className="pointer-events-none" data-testid="map-district-lines" /> : null;
}

function stillStates(still: MapStill | null): ReactNode | undefined {
  if (!still || still.states === undefined) return undefined;
  return still.states ? <StillStates still={still} d={still.states} /> : null;
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

export function PlacesMap({ spec, drawn, marks, labelledBy, nameOf, renderUnit }: PlacesMapProps) {
  const map = useRef<SVGSVGElement | null>(null);
  const { frame, still } = drawn;
  const scale = useFitScale(map, frame.width);
  const layerNames = useMemo(() => ({ ...drawn.names, home: [] }), [drawn.names]);
  const layers = useTimelineMapLayers(layerNames, still);
  const waters = still?.waters ?? null;
  const values = useDistrictValues(spec, still);
  const pins = useMemo(() => placedPins(spec.places, scale), [spec.places, scale]);
  const underlay = (
    <>
      {still?.neighbours ? <StillNeighbours still={still} d={still.neighbours} /> : null}
      {layers.parts.relief}
      {marks.districts ? values.fills : null}
      <DistrictLinesOrStill still={still} frame={frame} />
      {layers.parts.rivers}
      {still && waters ? <StillWatersLines box={still.box} grid={still.grid} waters={waters} /> : null}
      <PlaceHatchOrStill still={still?.home ?? null} home={drawn.names.home} frame={frame} scale={scale} />
    </>
  );
  return (
    <div className="grid min-w-0 gap-3" data-testid="places-map">
      <div className="relative min-w-0 overflow-hidden rounded-plate border border-rule">
        <svg ref={map} viewBox={viewBoxOf(frame)} role="img" aria-labelledby={labelledBy} className="block h-auto w-full [forced-color-adjust:none]" data-fit="" data-testid="general-map">
          <IndiaMapBase underlay={underlay} frame={frame} states={stillStates(still)} />
          <MapRings rings={spec.rings ?? []} places={spec.places} marks={marks} />
          <MapRoutes routes={spec.routes ?? []} pins={pins} marks={marks} scale={scale} />
        </svg>
        <PlacesOverlay spec={spec} frame={frame} marks={marks} values={values.labels} files={layers.files} waters={waters} named={layerNames.emphasis?.rivers ?? []} nameOf={nameOf} />
        <IndiaLocator marked={[]} frame={frame} label={locatorLabel([])} className={LOCATOR_INSET} />
      </div>
      <PlacesKey spec={spec} keyed={{ frame, home: drawn.names.home, waters }} classes={values.classes} layerKey={layers.key} renderUnit={renderUnit} />
      <PlacesSource still={still} credits={still?.credits ?? layers.credits} />
    </div>
  );
}
