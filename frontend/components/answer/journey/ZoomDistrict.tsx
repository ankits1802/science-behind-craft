"use client";

import { useCallback, useMemo } from "react";

import { districtFrame, zoomedBox, type ZoomFrame } from "@/components/answer/journey/journeyGeometry";
import { AnswerFigure } from "@/components/answer/place/AnswerFigure";
import { AnswerMapSource } from "@/components/answer/place/AnswerMapSource";
import { MapPlaceholder } from "@/components/answer/place/MapPlaceholder";
import { useRemote } from "@/components/hooks/useRemote";
import { DistrictFills, DistrictOutlines, HIGHLIGHT_TONES } from "@/components/map/DistrictLayer";
import { IndiaLocator, LOCATOR_INSET, locatorLabel } from "@/components/map/IndiaLocator";
import { IndiaMap } from "@/components/map/IndiaMap";
import { LabelText, MapAt, MapLabelLayer } from "@/components/map/MapLabelLayer";
import { MapRetry } from "@/components/map/MapRetry";
import { mapLabel } from "@/components/map/placesMapLabels";
import { project } from "@/components/map/projection";
import { loadShapes, type DistrictShape } from "@/components/map/shapeGeometry";
import type { DistrictRef } from "@/lib/explainerPlace";
import type { BoundaryNote } from "@/lib/regionContract";

const NO_POINTS: never[] = [];
const QUIET_TONE = "fill-transparent";
const AT_REST: ZoomFrame = { scale: 1, x: "0%", y: "0%" };
const ORIGIN = { x: 0, y: 0 };
const NAME_DOT = 4;
const NAME_GAP = 8;
const NAME_TURNS = 0.6;

type ZoomMapProps = { shapes: DistrictShape[]; district: DistrictRef; boundary: BoundaryNote | null; moving: boolean };

function ZoomedName({ shape, name, target }: { shape: DistrictShape; name: string; target: ZoomFrame }) {
  const shown = zoomedBox(target);
  const at = project(shape.centroid[0], shape.centroid[1]);
  const toEnd = (at.x - shown.x) / shown.width > NAME_TURNS;
  const label = mapLabel("district", ORIGIN, name, { anchor: toEnd ? "end" : "start", dx: toEnd ? -NAME_GAP : NAME_GAP, weight: "semibold" });
  return (
    <MapLabelLayer>
      <MapAt frame={shown} at={at} testId="district-tag">
        <circle r={NAME_DOT} fill="var(--map-selection)" stroke="var(--map-selection-halo)" strokeWidth={1.5} />
        <LabelText label={label} />
      </MapAt>
    </MapLabelLayer>
  );
}

export function ZoomDistrictMap({ shapes, district, boundary, moving }: ZoomMapProps) {
  const shape = useMemo(() => shapes.find((entry) => entry.lgd === district.districtLgd) ?? null, [shapes, district.districtLgd]);
  const fillOf = useCallback((entry: DistrictShape) => (entry.lgd === district.districtLgd ? HIGHLIGHT_TONES.district : QUIET_TONE), [district.districtLgd]);
  const frame = useMemo(() => districtFrame(shape), [shape]);
  if (!shape) return null;
  const target = moving ? frame : AT_REST;
  return (
    <AnswerFigure texts={{ source: <AnswerMapSource boundary={boundary} /> }} data-testid="zoom-district" data-lgd={district.districtLgd} data-scale={target.scale}>
      <div className="relative overflow-hidden rounded-plate [forced-color-adjust:none]">
        <div style={{ transformOrigin: "0% 0%", transform: `translateX(${target.x}) translateY(${target.y}) scale(${target.scale})` }}>
          <IndiaMap points={NO_POINTS} underlay={<DistrictFills shapes={shapes} fillOf={fillOf} />} overlay={<DistrictOutlines shapes={[shape]} className="stroke-terracotta" />} />
        </div>
        <ZoomedName shape={shape} name={district.name} target={target} />
        {target.scale > 1 ? (
          <div className={LOCATOR_INSET} data-testid="zoom-locator">
            <IndiaLocator marked={[shape]} frame={null} label={locatorLabel([district])} />
          </div>
        ) : null}
      </div>
    </AnswerFigure>
  );
}

export function ZoomDistrict({ district, boundary, moving }: { district: DistrictRef; boundary: BoundaryNote | null; moving: boolean }) {
  const shapes = useRemote(loadShapes);
  if (shapes.failure) return <MapRetry message="The map could not be drawn. Try again in a moment." onRetry={shapes.retry} />;
  if (!shapes.data) return <MapPlaceholder />;
  return <ZoomDistrictMap shapes={shapes.data} district={district} boundary={boundary} moving={moving} />;
}
