"use client";

import { isValidElement, useId, useMemo, type ReactNode } from "react";

import { TimelineMapFrame, type TimelineControl, type TimelineMapDrawing } from "@/components/answer/journey/TimelineMap";
import type { TimelineTexts } from "@/components/answer/journey/TimelineEntries";
import { DatasetCredit } from "@/components/DatasetCredit";
import { useTimelineMapLayers } from "@/components/map/TimelineMapLayers";
import { timelineMapDrawn } from "@/components/map/timelineMapStill";
import { GeneralFigure, type RenderUnit } from "@/components/monograph/kinds/general/GeneralFigure";
import { parsedSpec } from "@/lib/componentSpecsGeneral";
import { layerCredits, timelineMapSource, timelineMapSpecShape, TIMELINE_MAP_KIND, type TimelineMapSpec, type UnitSaid } from "@/lib/componentSpecsTimelineMap";
import type { ComponentViewProps } from "@/lib/componentViewContract";
import { boundaryNote } from "@/lib/placeView";
import { BOUNDARY_DATASET_CODE } from "@/lib/regionContract";
import { pointPositions } from "@/lib/timelinePlay";
import { stopLabel, timelineEntries, timelineStops } from "@/lib/timelineView";

import { TimelineTrack } from "./TimelineTrack";
import { useTimelinePlay, type TimelinePlay } from "./useTimelinePlay";

const SHOWN: TimelineMapDrawing<UnitSaid>["placeable"] = (place) => place.latitude !== null && place.longitude !== null;
const POINTS_LABEL = "Dated moments on the map";

type Shown = Parameters<TimelineControl<UnitSaid>>[0];

function playedTrack(play: TimelinePlay, { entries, stops }: Shown): ReactNode {
  const positions = pointPositions(stops);
  const points = stops.map((stop, at) => ({ key: String(stop), position: positions[at], name: stopLabel(entries, stop), shown: stopLabel(entries, stop) }));
  return <TimelineTrack points={points} play={play} label={POINTS_LABEL} first={points[0].name} last={points[points.length - 1].name} />;
}

function plainText(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(plainText).join("");
  if (isValidElement<{ children?: ReactNode }>(node)) return plainText(node.props.children);
  return "";
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
  const count = useMemo(() => timelineStops(timelineEntries(source)).length, [source]);
  const play = useTimelinePlay(count, count - 1);
  const drawn = useMemo(() => timelineMapDrawn(map), [map]);
  const layers = useTimelineMapLayers(drawn.names, drawn.still);
  const texts = useMemo<TimelineTexts<UnitSaid>>(() => ({ say: (said, className) => <p className={className}>{renderUnit(said.id)}</p>, keyOf: (said) => said.id, idOf: (said) => said.id }), [renderUnit]);
  const coordinates = map.places.some((place) => place.found?.wikidataId !== undefined);
  const parts = { frame: drawn.frame, underlay: layers.underlay, overlay: layers.overlay, key: layers.key, credits: <Credits map={map} />, titled: false, coordinates };
  const drawing: TimelineMapDrawing<UnitSaid> = { texts, boundary: boundaryNote(map.boundaryCaption ?? "", map.datasets ?? []), placeable: SHOWN, pinUndated: true, parts, control: (shown) => playedTrack(play, shown) };
  return (
    <div ref={play.watch} className="min-w-0" data-testid="timeline-map-play" data-at={play.at}>
      <TimelineMapFrame source={source} at={play.at} onChoose={play.choose} drawing={drawing} />
    </div>
  );
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
