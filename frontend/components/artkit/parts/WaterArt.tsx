import type { WaterPart } from "@/lib/componentSpecsKit";

import { url, type PartIds } from "../kitIds";
import { INK, INK_FAINT, INK_SOFT, NEUTRAL_LIQUOR, rectPath } from "../surfaces";

const DROP = "M0 -9 C3 -4 5 -1 5 2 C5 5 3 7 0 7 C-3 7 -5 5 -5 2 C-5 -1 -3 -4 0 -9 Z";
const DROPS = [
  [30, 26],
  [58, 18],
  [86, 30],
  [44, 52],
  [74, 56]
];

function wave(y: number): string {
  return `M6 ${y} C18 ${y - 7} 30 ${y + 7} 42 ${y} S66 ${y - 7} 78 ${y} S102 ${y + 7} 110 ${y}`;
}

function Running({ ids }: { ids: PartIds }) {
  const bed = rectPath(2, 20, 116, 82);
  return (
    <>
      <path d={bed} fill={NEUTRAL_LIQUOR} />
      <path d={bed} fill={url(ids.ripple)} />
      <path d="M2 20 H118 M2 102 H118" stroke={INK} strokeWidth="1.4" />
      <g fill="none" stroke={INK_SOFT} strokeWidth="1.6" strokeLinecap="round">
        {[42, 62, 82].map((y) => (
          <path key={y} d={wave(y)} />
        ))}
      </g>
      <path d="M100 30 L112 30 M106 25 L112 30 L106 35" fill="none" stroke={INK} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </>
  );
}

function Still({ ids }: { ids: PartIds }) {
  return (
    <>
      <ellipse cx="60" cy="66" rx="54" ry="30" fill={NEUTRAL_LIQUOR} stroke={INK} strokeWidth="1.4" />
      <ellipse cx="60" cy="66" rx="54" ry="30" fill={url(ids.ripple)} />
      {[
        [34, 18],
        [22, 12],
        [10, 6]
      ].map(([rx, ry]) => (
        <ellipse key={rx} cx="60" cy="66" rx={rx} ry={ry} fill="none" stroke={INK_SOFT} strokeWidth="1" />
      ))}
    </>
  );
}

function Sprinkled() {
  return (
    <>
      <path d="M10 96 H110" stroke={INK} strokeWidth="1.6" />
      <path d="M22 104 H98" stroke={INK_FAINT} strokeWidth="1" strokeDasharray="4 3" />
      {DROPS.map(([x, y]) => (
        <path key={`${x}-${y}`} d={DROP} transform={`translate(${x} ${y})`} fill={NEUTRAL_LIQUOR} stroke={INK_SOFT} strokeWidth="1.2" />
      ))}
      <path d="M40 92 q4 -4 8 0 M70 92 q4 -4 8 0" fill="none" stroke={INK_SOFT} strokeWidth="1.2" strokeLinecap="round" />
    </>
  );
}

export function WaterArt({ part, ids }: { part: WaterPart; ids: PartIds }) {
  return (
    <g data-kit-part="water" data-kit-form={part.form}>
      {part.form === "running" ? <Running ids={ids} /> : null}
      {part.form === "still" ? <Still ids={ids} /> : null}
      {part.form === "sprinkled" ? <Sprinkled /> : null}
    </g>
  );
}
