"use client";

import { useCallback, useMemo } from "react";
import { motion } from "framer-motion";

import { districtFrame } from "@/components/answer/journey/journeyGeometry";
import { MapPlaceholder } from "@/components/answer/place/MapPlaceholder";
import { cameraMove } from "@/components/guide/guideMotion";
import { useRemote } from "@/components/hooks/useRemote";
import { DistrictFills, DistrictOutlines, DistrictTag, HIGHLIGHT_TONES } from "@/components/map/DistrictLayer";
import { IndiaMap } from "@/components/map/IndiaMap";
import { MapAttribution } from "@/components/map/MapAttribution";
import { loadShapes, type DistrictShape } from "@/components/map/shapeGeometry";
import { RetryLine } from "@/components/RemotePanels";
import type { DistrictRef } from "@/lib/explainerPlace";
import type { BoundaryNote } from "@/lib/regionContract";

const NO_POINTS: never[] = [];
const QUIET_TONE = "fill-purple-50 dark:fill-purple-950/40";
const AT_REST = { scale: 1, x: "0%", y: "0%" };

export function ZoomDistrictMap({
  shapes,
  district,
  boundary,
  moving
}: {
  shapes: DistrictShape[];
  district: DistrictRef;
  boundary: BoundaryNote | null;
  moving: boolean;
}) {
  const shape = useMemo(() => shapes.find((entry) => entry.lgd === district.districtLgd) ?? null, [shapes, district.districtLgd]);
  const fillOf = useCallback((entry: DistrictShape) => (entry.lgd === district.districtLgd ? HIGHLIGHT_TONES.district : QUIET_TONE), [district.districtLgd]);
  const frame = useMemo(() => districtFrame(shape), [shape]);
  if (!shape) return null;
  const target = moving ? frame : AT_REST;
  const marks = (
    <>
      <DistrictOutlines shapes={[shape]} className="stroke-ink-900" />
      <DistrictTag shape={shape} text={district.name} />
    </>
  );
  return (
    <figure className="min-w-0" data-testid="zoom-district" data-lgd={district.districtLgd} data-scale={target.scale}>
      <div className="overflow-hidden rounded-md">
        <motion.div style={{ transformOrigin: "0% 0%" }} initial={AT_REST} animate={target} transition={cameraMove(!moving)}>
          <IndiaMap points={NO_POINTS} underlay={<DistrictFills shapes={shapes} fillOf={fillOf} />} overlay={marks} />
        </motion.div>
      </div>
      <MapAttribution boundary={boundary} />
    </figure>
  );
}

export function ZoomDistrict({ district, boundary, moving }: { district: DistrictRef; boundary: BoundaryNote | null; moving: boolean }) {
  const shapes = useRemote(loadShapes);
  if (shapes.failure) return <RetryLine message="Couldn't load the map." onRetry={shapes.retry} />;
  if (!shapes.data) return <MapPlaceholder />;
  return <ZoomDistrictMap shapes={shapes.data} district={district} boundary={boundary} moving={moving} />;
}
