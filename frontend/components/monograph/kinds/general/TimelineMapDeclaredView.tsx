"use client";

import { isValidElement, useId, useMemo, useState, type ReactNode } from "react";

import { TimelineMapFrame, type TimelineMapDrawing } from "@/components/answer/journey/TimelineMap";
import type { TimelineTexts } from "@/components/answer/journey/TimelineEntries";
import { DatasetCredit } from "@/components/DatasetCredit";
import { INDIA_BOUNDS } from "@/components/map/indiaBounds";
import { placesFrame } from "@/components/map/placesFrame";
import { useTimelineMapLayers } from "@/components/map/TimelineMapLayers";
import { GeneralFigure, type RenderUnit } from "@/components/monograph/kinds/general/GeneralFigure";
import { parsedSpec } from "@/lib/componentSpecsGeneral";
import { districtLayer, foundPoints, homeDistricts, layerCredits, physicalLayers, timelineMapSource, timelineMapSpecShape, TIMELINE_MAP_KIND, type TimelineMapSpec, type UnitSaid } from "@/lib/componentSpecsTimelineMap";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { boundaryNote } from "@/lib/placeView";
import { BOUNDARY_DATASET_CODE } from "@/lib/regionContract";
import { timelineEntries, timelineStops } from "@/lib/timelineView";

import "./general.css";

const SHOWN: TimelineMapDrawing<UnitSaid>["placeable"] = (place) => place.latitude !== null && place.longitude !== null;

function plainText(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(plainText).join("");
  if (isValidElement<{ children?: ReactNode }>(node)) return plainText(node.props.children);
  return "";
}

function inIndia(point: { longitude: number; latitude: number }): boolean {
  return point.longitude >= INDIA_BOUNDS.minLongitude && point.longitude <= INDIA_BOUNDS.maxLongitude && point.latitude >= INDIA_BOUNDS.minLatitude && point.latitude <= INDIA_BOUNDS.maxLatitude;
}

function Credits({ map }: { map: TimelineMapSpec }) {
  const credits = layerCredits(map, BOUNDARY_DATASET_CODE);
  if (!credits.length) return null;
  return (
    <span className="mt-2 grid gap-2" data-testid="timeline-map-credits">
      {credits.map((dataset) => (
        <DatasetCredit key={dataset.code} dataset={dataset} />
      ))}
    </span>
  );
}

function PlacedMap({ map, renderUnit, textOf }: { map: TimelineMapSpec; renderUnit: RenderUnit; textOf: (ref: string) => string }) {
  const source = useMemo(() => timelineMapSource(map, textOf), [map, textOf]);
  const [at, onChoose] = useState(() => timelineStops(timelineEntries(source)).length - 1);
  const layers = useTimelineMapLayers({ physical: physicalLayers(map), district: districtLayer(map), home: homeDistricts(map) });
  const frame = useMemo(() => placesFrame(foundPoints(map).filter(inIndia)), [map]);
  const texts = useMemo<TimelineTexts<UnitSaid>>(() => ({ say: (said, className) => <p className={className}>{renderUnit(said.id)}</p>, keyOf: (said) => said.id, idOf: (said) => said.id }), [renderUnit]);
  const coordinates = map.places.some((place) => place.found?.wikidataId !== undefined);
  const parts = { frame, underlay: layers.underlay, overlay: layers.overlay, key: layers.key, credits: <Credits map={map} />, titled: false, coordinates };
  const drawing: TimelineMapDrawing<UnitSaid> = { texts, boundary: boundaryNote(map.boundaryCaption ?? "", map.datasets ?? []), placeable: SHOWN, pinUndated: true, parts };
  return <TimelineMapFrame source={source} at={at} onChoose={onChoose} drawing={drawing} />;
}

export function TimelineMapDeclaredView({ spec, renderUnit, unitText }: ComponentViewProps) {
  const map = useMemo(() => parsedSpec(timelineMapSpecShape, spec), [spec]);
  const titleId = useId();
  const textOf = useMemo(() => unitText ?? ((ref: string) => plainText(renderUnit(ref))), [unitText, renderUnit]);
  if (!map) return null;
  return (
    <GeneralFigure kind={TIMELINE_MAP_KIND} head={map.head} titleId={titleId} renderUnit={renderUnit}>
      <PlacedMap map={map} renderUnit={renderUnit} textOf={textOf} />
    </GeneralFigure>
  );
}
