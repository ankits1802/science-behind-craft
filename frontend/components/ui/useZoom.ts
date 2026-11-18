"use client";

import { useCallback, useRef, useState, type PointerEvent, type WheelEvent } from "react";

export const ZOOM_MIN = 1;
export const ZOOM_MAX = 4;

export type ZoomState = { scale: number; x: number; y: number };

export const ZOOM_RESET: ZoomState = { scale: 1, x: 0, y: 0 };

export function clampZoom(scale: number): number {
  return Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, scale));
}

export function zoomBy(state: ZoomState, factor: number): ZoomState {
  const scale = clampZoom(state.scale * factor);
  return scale === ZOOM_MIN ? ZOOM_RESET : { scale, x: state.x, y: state.y };
}

function spread(points: Map<number, { x: number; y: number }>): number {
  const [a, b] = [...points.values()];
  return a && b ? Math.hypot(a.x - b.x, a.y - b.y) : 0;
}

export function useZoom() {
  const [zoom, setZoom] = useState<ZoomState>(ZOOM_RESET);
  const points = useRef(new Map<number, { x: number; y: number }>());
  const lastSpread = useRef(0);

  const onWheel = useCallback((event: WheelEvent) => {
    setZoom((current) => zoomBy(current, event.deltaY < 0 ? 1.12 : 1 / 1.12));
  }, []);

  const onPointerDown = useCallback((event: PointerEvent) => {
    event.currentTarget.setPointerCapture(event.pointerId);
    points.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    lastSpread.current = spread(points.current);
  }, []);

  const onPointerMove = useCallback((event: PointerEvent) => {
    const before = points.current.get(event.pointerId);
    if (!before) return;
    points.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (points.current.size === 2) {
      const now = spread(points.current);
      if (lastSpread.current > 0) setZoom((current) => zoomBy(current, now / lastSpread.current));
      lastSpread.current = now;
      return;
    }
    setZoom((current) => (current.scale === ZOOM_MIN ? current : { ...current, x: current.x + event.clientX - before.x, y: current.y + event.clientY - before.y }));
  }, []);

  const onPointerUp = useCallback((event: PointerEvent) => {
    points.current.delete(event.pointerId);
    lastSpread.current = spread(points.current);
  }, []);

  const step = useCallback((factor: number) => setZoom((current) => zoomBy(current, factor)), []);
  const reset = useCallback(() => setZoom(ZOOM_RESET), []);

  return { zoom, step, reset, handlers: { onWheel, onPointerDown, onPointerMove, onPointerUp, onPointerCancel: onPointerUp } };
}
