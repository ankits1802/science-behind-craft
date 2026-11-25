import type { MapBox } from "@/components/map/basemap";
import type { MapStill, StillDistrict, StillRiver } from "@/components/map/timelineMapStill";
import type { MineralKeyRow } from "@/lib/mapPhysical";
import { boundaryShape, datasetShape } from "@/lib/regionContract";
import type { LayerLegend } from "@/lib/regionView";
import { count, integer, list, matching, nullable, number, object, optional, positive, text, type Shape } from "@/lib/shape";

const STILL_PATH = matching(/^[MLlz\d .-]*$/, "a still's path");
const NAMED_FRAME = matching(/^(district|state):\d+$/, "a named frame");

export const mapStillShape: Shape<MapStill> = object<MapStill>({
  box: object<MapBox>({ x: number, y: number, width: number, height: number }),
  grid: positive,
  relief: nullable(list(STILL_PATH)),
  rivers: nullable(list(object<StillRiver>({ rank: integer, d: STILL_PATH }))),
  lakes: nullable(STILL_PATH),
  home: nullable(STILL_PATH),
  minerals: nullable(list(object<MineralKeyRow>({ id: text, label: text, count }))),
  district: nullable(object<LayerLegend>({ title: text, labels: list(text), caption: text, summary: text, dataset: datasetShape })),
  lines: optional(nullable(STILL_PATH)),
  neighbours: optional(nullable(STILL_PATH)),
  valued: optional(nullable(list(object<StillDistrict>({ lgd: integer, d: STILL_PATH, x: number, y: number })))),
  named: optional(nullable(NAMED_FRAME)),
  credits: optional(nullable(list(datasetShape))),
  boundary: optional(nullable(boundaryShape))
});
