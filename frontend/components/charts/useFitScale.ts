"use client";

import { useEffect, useState, type CSSProperties, type RefObject } from "react";

export const ASSUMED_WIDTH = 640;

export function fitScale(viewBoxWidth: number, renderedWidth: number): number {
  return renderedWidth > 0 ? viewBoxWidth / renderedWidth : viewBoxWidth / ASSUMED_WIDTH;
}

export function fitStyle(scale: number): CSSProperties {
  return { "--k": scale.toFixed(4) } as CSSProperties;
}

export function useFitScale(target: RefObject<Element | null>, viewBoxWidth: number): number {
  const [scale, setScale] = useState(() => fitScale(viewBoxWidth, 0));
  useEffect(() => {
    const node = target.current;
    if (!node) return;
    const measure = () => setScale(fitScale(viewBoxWidth, node.getBoundingClientRect().width));
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, [target, viewBoxWidth]);
  return scale;
}
