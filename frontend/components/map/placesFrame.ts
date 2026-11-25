import type { MapBox } from "@/components/map/basemap";
import { WHOLE_MAP } from "@/components/map/layout";
import { project, type Projected } from "@/components/map/projection";

export type FramedPoint = { longitude: number; latitude: number };
export type FrameZoom = { minShare: number; paddingShare: number };

export const FRAME_MIN_SHARE = 0.32;
export const FRAME_PADDING_SHARE = 0.22;
export const FRAME_ASPECT = 0.8;
export const PLACES_ZOOM: FrameZoom = { minShare: FRAME_MIN_SHARE, paddingShare: FRAME_PADDING_SHARE };

function clampedStart(centre: number, size: number, start: number, span: number): number {
  return Math.min(Math.max(centre - size / 2, start), start + span - size);
}

export function placesFrame(points: readonly FramedPoint[], zoom: FrameZoom = PLACES_ZOOM): MapBox {
  return projectedFrame(points.map((point) => project(point.longitude, point.latitude)), zoom);
}

export function projectedFrame(projected: readonly Projected[], zoom: FrameZoom = PLACES_ZOOM): MapBox {
  if (projected.length === 0) return WHOLE_MAP;
  const xs = projected.map((point) => point.x);
  const ys = projected.map((point) => point.y);
  const spanX = Math.max(...xs) - Math.min(...xs);
  const spanY = Math.max(...ys) - Math.min(...ys);
  const padded = Math.max(spanX, spanY / FRAME_ASPECT) * (1 + 2 * zoom.paddingShare);
  const width = Math.min(WHOLE_MAP.width, Math.max(padded, WHOLE_MAP.width * zoom.minShare));
  const height = Math.min(WHOLE_MAP.height, width * FRAME_ASPECT);
  if (width >= WHOLE_MAP.width) return WHOLE_MAP;
  const centreX = (Math.max(...xs) + Math.min(...xs)) / 2;
  const centreY = (Math.max(...ys) + Math.min(...ys)) / 2;
  return {
    x: Number(clampedStart(centreX, width, WHOLE_MAP.x, WHOLE_MAP.width).toFixed(1)),
    y: Number(clampedStart(centreY, height, WHOLE_MAP.y, WHOLE_MAP.height).toFixed(1)),
    width: Number(width.toFixed(1)),
    height: Number(height.toFixed(1))
  };
}
