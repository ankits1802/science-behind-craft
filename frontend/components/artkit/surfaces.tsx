import type { ReactNode } from "react";

import { paint, url, type KitIds, type Moving } from "./kitIds";

export type Texture = "weave" | "grain" | "speckle" | "ripple" | "strata";

export const INK = "var(--ink-1)";
export const INK_SOFT = "var(--ink-2)";
export const INK_FAINT = "var(--ink-3)";
export const PAPER = "var(--raised)";
export const WELL = "var(--sunk)";
export const SHADE = "color-mix(in srgb, var(--ink-3) 22%, var(--raised))";
export const NEUTRAL_LIQUOR = "color-mix(in srgb, var(--ink-3) 18%, var(--sunk))";

type MaterialProps = { d: string; material: string; ids: KitIds; print?: string; texture?: Texture; edge?: string };

export function MaterialPath({ d, material, ids, print, texture = "weave", edge = INK }: MaterialProps) {
  return (
    <>
      <path d={d} fill={paint(material)} />
      {print ? <path d={d} fill={url(print)} /> : null}
      <path d={d} fill={url(ids[texture])} />
      <path d={d} fill="none" stroke={edge} strokeWidth="1.2" strokeLinejoin="round" />
    </>
  );
}

export function LinePath({ d, ids, texture, fill = PAPER }: { d: string; ids: KitIds; texture?: Texture; fill?: string }) {
  return (
    <>
      <path d={d} fill={fill} />
      {texture ? <path d={d} fill={url(ids[texture])} /> : null}
      <path d={d} fill="none" stroke={INK} strokeWidth="1.2" strokeLinejoin="round" />
    </>
  );
}

export function MovingLayer({ moving, children }: { moving?: Moving; children: ReactNode }) {
  if (!moving) return <g>{children}</g>;
  return (
    <g className={moving.className} data-kit-move={moving.panel}>
      {children}
    </g>
  );
}

export function shaded(token: string, share: number): string {
  return `color-mix(in srgb, ${paint(token)} ${share}%, black)`;
}

export function rectPath(x: number, y: number, width: number, height: number): string {
  return `M${x} ${y} H${x + width} V${y + height} H${x} Z`;
}
